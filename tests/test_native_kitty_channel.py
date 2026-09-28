# ABOUTME: Checks that LifeOS terminal state stays local to desktop sessions.
# ABOUTME: Uses native Kitty hooks with a disposable home and fake terminal values.

import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from lifeos_hook_bridge.bridge import HookBridge


KITTY_HOOK_PATH = os.environ.get("LIFEOS_KITTY_HOOK_PATH")


@unittest.skipUnless(KITTY_HOOK_PATH and shutil.which("bun"), "LifeOS KittyEnvPersist and Bun are required")
class NativeKittyChannelTests(unittest.TestCase):
    def run_session_start(self, platform):
        temporary = tempfile.TemporaryDirectory(prefix="kitty-channel-parity-")
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        home = root / "home"
        home.mkdir()
        settings = root / "settings.json"
        settings.write_text(json.dumps({"hooks": {"SessionStart": [{"hooks": [
            {"type": "command", "command": f"bun {KITTY_HOOK_PATH}"},
        ]}]}}))
        bridge = HookBridge(settings, root)
        bridge.environment.update({
            "HOME": str(home),
            "TERM": "xterm-kitty",
            "KITTY_LISTEN_ON": "unix:/tmp/nonexistent-kitty-parity",
            "KITTY_WINDOW_ID": "123",
        })
        try:
            bridge.pre_llm_call("Hello", session_id="kitty-channel-probe", platform=platform)
        finally:
            bridge.close()
        return root, home

    def test_cli_session_preserves_kitty_environment(self):
        root, _ = self.run_session_start("cli")
        self.assertTrue((root / "LIFEOS/MEMORY/STATE/kitty-env.json").exists())

    def test_discord_session_does_not_persist_kitty_environment(self):
        root, _ = self.run_session_start("discord")
        self.assertFalse((root / "LIFEOS/MEMORY/STATE/kitty-env.json").exists())
        self.assertFalse((root / "LIFEOS/MEMORY/STATE/kitty-sessions/kitty-channel-probe.json").exists())

    def run_tab_setter(self, channel):
        setter = Path(KITTY_HOOK_PATH).parent / "lib/tab-setter.ts"
        temporary = tempfile.TemporaryDirectory(prefix="kitty-setter-parity-")
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        script = root / "run.ts"
        script.write_text(
            f'import {{setTabState}} from "{setter}"; '
            'setTabState({title:"Test turn",state:"working",sessionId:"probe"});\n'
        )
        environment = {
            **os.environ,
            "HOME": str(root),
            "LIFEOS_DIR": str(root / "LIFEOS"),
            "LIFEOS_NOTIFICATION_CHANNEL": channel,
            "TERM": "xterm-kitty",
            "KITTY_LISTEN_ON": "unix:/tmp/nonexistent-kitty-parity",
            "KITTY_WINDOW_ID": "123",
        }
        process = subprocess.run(["bun", str(script)], env=environment, capture_output=True, text=True, timeout=10)
        self.assertEqual(process.returncode, 0, process.stderr)
        return root / "LIFEOS/MEMORY/STATE/tab-titles/123.json"

    def test_discord_session_does_not_write_tab_state(self):
        self.assertFalse(self.run_tab_setter("discord").exists())

    def test_desktop_session_writes_tab_state(self):
        self.assertTrue(self.run_tab_setter("desktop").exists())
