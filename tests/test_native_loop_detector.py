# ABOUTME: Checks native LifeOS loop feedback for repeated failed Hermes tool calls.
# ABOUTME: Runs the installed LoopDetector through the bridge in a disposable root.

import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path

from lifeos_hook_bridge.bridge import HookBridge


HOOK_PATH = os.environ.get("LIFEOS_LOOP_DETECTOR_PATH")


@unittest.skipUnless(HOOK_PATH and shutil.which("bun"), "LifeOS LoopDetector and Bun are required")
class NativeLoopDetectorTests(unittest.TestCase):
    def test_third_failed_call_returns_loop_feedback(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "LIFEOS"
            root.mkdir()
            settings = root / "settings.json"
            settings.write_text(json.dumps({"hooks": {"PostToolUseFailure": [{"hooks": [
                {"type": "command", "command": f"bun {HOOK_PATH}"},
            ]}]}}))
            bridge = HookBridge(settings, root)
            bridge.environment["LIFEOS_DIR"] = str(root)
            try:
                feedback = [bridge.post_tool_call(
                    "terminal", {"command": "false"}, "Exit code 1", session_id="failed-loop",
                    status="error", error_message="Exit code 1",
                ) for _ in range(3)]
            finally:
                bridge.close()

            self.assertEqual(feedback[:2], [None, None])
            self.assertIn("[LOOP DETECTED]", feedback[2])
            state = json.loads((root / "MEMORY/STATE/loop-detector/failed-loop.json").read_text())
            self.assertEqual(len(state["window"]), 3)
            self.assertTrue(all(row["failed"] for row in state["window"]))
