# ABOUTME: Checks that LifeOS records Hermes's combined Bash output accurately.
# ABOUTME: Set LIFEOS_EVENT_LOGGER_HOOK_PATH to run against a LifeOS checkout.

import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


HOOK_PATH = os.environ.get("LIFEOS_EVENT_LOGGER_HOOK_PATH")


@unittest.skipUnless(HOOK_PATH and shutil.which("bun"), "LifeOS EventLogger and Bun are required")
class NativeEventLoggerTests(unittest.TestCase):
    def test_bash_combined_output_is_named_in_audit(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "LIFEOS"
            environment = {**os.environ, "LIFEOS_DIR": str(root)}
            payload = {
                "hook_event_name": "PostToolUse",
                "session_id": "hermes-event-logger-test",
                "tool_name": "Bash",
                "tool_input": {"command": "printf hello"},
                "tool_response": {"output": "hello", "exit_code": 0},
                "cwd": directory,
            }
            result = subprocess.run(
                ["bun", HOOK_PATH], input=json.dumps(payload), text=True, capture_output=True,
                timeout=10, env=environment, cwd=directory,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            path = root / "MEMORY/OBSERVABILITY/tool-activity.jsonl"
            ground_truth = json.loads(path.read_text().splitlines()[-1])["ground_truth"]
            self.assertEqual(ground_truth["combined_output_preview"], "hello")
            self.assertEqual(ground_truth["combined_output_bytes"], 5)
            self.assertNotIn("stdout_preview", ground_truth)
