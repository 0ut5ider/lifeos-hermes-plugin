# ABOUTME: Checks native LifeOS capability feedback after a failed Hermes command.
# ABOUTME: Runs the installed AlgorithmNudge through the bridge in a disposable home.

import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path

from lifeos_hook_bridge.bridge import HookBridge


HOOK_PATH = os.environ.get("LIFEOS_ALGORITHM_NUDGE_PATH")


@unittest.skipUnless(HOOK_PATH and shutil.which("bun"), "LifeOS AlgorithmNudge and Bun are required")
class NativeAlgorithmNudgeTests(unittest.TestCase):
    def test_broken_capability_failure_returns_one_nudge(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            root = home / ".claude"
            root.mkdir()
            manifest = home / "capabilities.json"
            manifest.write_text(json.dumps({"capabilities": {"codex": {"state": "broken"}}}))
            settings = root / "settings.json"
            settings.write_text(json.dumps({"hooks": {"PostToolUseFailure": [{"hooks": [
                {"type": "command", "command": f"bun {HOOK_PATH}"},
            ]}]}}))
            bridge = HookBridge(settings, root)
            bridge.environment["HOME"] = str(home)
            bridge.environment["LIFEOS_CAPABILITIES_PATH"] = str(manifest)
            try:
                feedback = [bridge.post_tool_call(
                    "terminal", {"command": "codex --version"}, "Exit code 1", session_id="broken-cap",
                    status="error", error_message="Exit code 1",
                ) for _ in range(2)]
            finally:
                bridge.close()

            self.assertIn("\"codex\" capability", feedback[0])
            self.assertIn("Doctor has as BROKEN", feedback[0])
            self.assertIsNone(feedback[1])
