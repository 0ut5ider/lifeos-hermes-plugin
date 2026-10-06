# ABOUTME: Verifies bridge decisions against the real native Pulse HTTP guard endpoints.
# ABOUTME: Starts a disposable daemon with no scheduled jobs or optional integrations.

import json
import os
from pathlib import Path
import re
import shutil
import socket
import subprocess
import tempfile
import time
import unittest
from urllib.error import URLError
from urllib.request import Request, urlopen

from lifeos_hook_bridge.bridge import HookBridge


SOURCE = os.environ.get("LIFEOS_PULSE_SOURCE")


class PulseFixture:
    def __init__(self, home, source):
        self.home = home
        self.root = home / ".claude"
        self.source = Path(source)
        self.pulse = self.root / "LIFEOS/PULSE"
        self.pulse.mkdir(parents=True)
        for item in (self.source / "LIFEOS/PULSE").iterdir():
            if item.name not in {"PULSE.toml", "state.json", "pulse.pid", "logs"}:
                (self.pulse / item.name).symlink_to(item, target_is_directory=item.is_dir())
        (self.root / "LIFEOS/TOOLS").symlink_to(self.source / "LIFEOS/TOOLS", target_is_directory=True)
        for folder in ("LIFEOS/USER/CONFIG", "LIFEOS/MEMORY/STATE"):
            (self.root / folder).mkdir(parents=True, exist_ok=True)
        declaration = (self.source / "LIFEOS/PULSE/lib/modules.ts").read_text().split("export const MODULE_DEFAULTS")[1].split("}")[0]
        modules = re.findall(r"\b(\w+): (?:true|false)", declaration)
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            self.port = listener.getsockname()[1]
        (self.pulse / "PULSE.toml").write_text(
            f"port = {self.port}\n[hooks]\nenabled = true\n[modules]\n" +
            "".join(f"{name} = false\n" for name in modules))
        self.log = home / "pulse.log"
        self.process = None

    def start(self):
        environment = {**os.environ, "HOME": str(self.home), "LIFEOS_DIR": str(self.root / "LIFEOS")}
        for key in ("LIFEOS_MEMORY_CONTEXT", "LIFEOS_MEMORY_INTERNAL", "CLAUDE_CONFIG_DIR", "LIFEOS_CONFIG_DIR"):
            environment.pop(key, None)
        with self.log.open("a") as output:
            self.process = subprocess.Popen(["bun", str(self.source / "LIFEOS/PULSE/pulse.ts")],
                                            env=environment, stdout=output, stderr=subprocess.STDOUT)
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            if self.process.poll() is not None:
                raise AssertionError(self.log.read_text())
            try:
                self.request("skill-guard", {"tool_input": {"skill": "fixture-ready"}})
                return
            except URLError:
                time.sleep(0.05)
        raise AssertionError("Pulse readiness timeout: " + self.log.read_text())

    def request(self, guard, payload):
        request = Request(f"http://127.0.0.1:{self.port}/hooks/{guard}",
                          data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"})
        with urlopen(request, timeout=2) as response:
            return response.read().decode()

    def stop(self):
        if self.process is not None and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=5)


@unittest.skipUnless(SOURCE and shutil.which("bun"), "Native Pulse source and Bun are required")
class NativePulseGuardTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="lifeos-pulse-guards-")
        self.addCleanup(temporary.cleanup)
        self.fixture = PulseFixture(Path(temporary.name), SOURCE)
        self.addCleanup(self.fixture.stop)
        self.fixture.start()
        settings = self.fixture.root / "settings.json"
        settings.write_text(json.dumps({"hooks": {"PreToolUse": [
            {"matcher": matcher, "hooks": [{"type": "http", "url":
                f"http://127.0.0.1:{self.fixture.port}/hooks/{guard}"}]}
            for matcher, guard in (("Skill", "skill-guard"), ("Agent", "agent-guard"))]}}))
        self.bridge = HookBridge(settings, self.fixture.root, lifeos_home=self.fixture.home)
        self.addCleanup(self.bridge.close)

    def test_blocked_and_allowed_skills_use_native_decisions(self):
        verdict = self.bridge.pre_tool_call("skill_view", {"name": "keybindings-help"}, session_id="skill-session")
        self.assertEqual(verdict["action"], "block")
        self.assertIn('"keybindings-help"', verdict["message"])
        self.assertIsNone(self.bridge.pre_tool_call("skill_view", {"name": "fixture-allowed"}, session_id="skill-session"))
        self.assertNotIn(("skill-session", "skill_view"), self.bridge.pending_tool_context)

    def test_foreground_warning_reaches_the_result_context(self):
        args = {"goal": "Inspect the report", "background": False}
        self.assertIsNone(self.bridge.pre_tool_call("delegate_task", args, session_id="parent", tool_call_id="agent-1"))
        context = self.bridge.augment_tool_result("delegate_task", args, "Report inspected", "Report inspected",
                                                 session_id="parent", tool_call_id="agent-1")
        self.assertIn("WARNING: Foreground agent", context)
        self.assertIn("run_in_background: true", context)

    def test_fast_tier_and_fast_scope_keep_the_native_silent_branch(self):
        for index, args in enumerate((
            {"goal": "Inspect report", "model": "haiku", "background": False},
            {"goal": "Inspect report", "context": "## Scope\nTiming: FAST", "background": False},
        )):
            with self.subTest(args=args):
                self.assertIsNone(self.bridge.pre_tool_call("delegate_task", args, session_id="parent", tool_call_id=str(index)))
                self.assertNotIn(("parent", str(index)), self.bridge.pending_tool_context)

    def test_outage_is_visible_and_restart_restores_the_deny(self):
        self.fixture.stop()
        with self.assertLogs("lifeos_hook_bridge.bridge", level="WARNING") as messages:
            self.assertIsNone(self.bridge.pre_tool_call("skill_view", {"name": "keybindings-help"}, session_id="outage"))
        self.assertEqual(len(messages.output), 1)
        self.assertIn("LifeOS HTTP hook unavailable", messages.output[0])
        self.fixture.start()
        verdict = self.bridge.pre_tool_call("skill_view", {"name": "keybindings-help"}, session_id="outage")
        self.assertEqual(verdict["action"], "block")

    def test_invalid_native_skill_input_is_fail_open(self):
        body = self.fixture.request("skill-guard", {"tool_input": {"skill": {"invalid": "type"}}})
        self.assertEqual(body, "")
