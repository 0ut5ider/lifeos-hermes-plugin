# ABOUTME: Checks that LifeOS records Hermes's combined Bash output accurately.
# ABOUTME: Set LIFEOS_EVENT_LOGGER_HOOK_PATH to run against a LifeOS checkout.

import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from lifeos_hook_bridge.bridge import HookBridge


HOOK_PATH = os.environ.get("LIFEOS_EVENT_LOGGER_HOOK_PATH")


@unittest.skipUnless(HOOK_PATH and shutil.which("bun"), "LifeOS EventLogger and Bun are required")
class NativeEventLoggerTests(unittest.TestCase):
    def test_failed_bash_call_is_recorded_through_bridge(self):
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
                bridge.post_tool_call(
                    "terminal", {"command": "false"}, "Exit code 1", session_id="failed-bash",
                    status="error", error_message="Exit code 1",
                )
            finally:
                bridge.close()

            path = root / "MEMORY/OBSERVABILITY/tool-failures.jsonl"
            row = json.loads(path.read_text().splitlines()[-1])
            self.assertEqual(row["event"], "tool_failure")
            self.assertEqual(row["session_id"], "failed-bash")
            self.assertEqual(row["tool_name"], "Bash")
            self.assertEqual(row["error"], "Exit code 1")

    def test_bash_combined_output_is_named_in_audit(self):
        for output in ("hello", "é🚀"):
            with self.subTest(output=output):
                self.assert_combined_output(output)

    def assert_combined_output(self, output):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "LIFEOS"
            environment = {**os.environ, "LIFEOS_DIR": str(root)}
            payload = {
                "hook_event_name": "PostToolUse",
                "session_id": "hermes-event-logger-test",
                "tool_name": "Bash",
                "tool_input": {"command": "printf hello"},
                "tool_response": {"output": output, "exit_code": 0},
                "cwd": directory,
            }
            result = subprocess.run(
                ["bun", HOOK_PATH], input=json.dumps(payload), text=True, capture_output=True,
                timeout=10, env=environment, cwd=directory,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            path = root / "MEMORY/OBSERVABILITY/tool-activity.jsonl"
            ground_truth = json.loads(path.read_text().splitlines()[-1])["ground_truth"]
            self.assertEqual(ground_truth["combined_output_preview"], output)
            self.assertEqual(ground_truth["combined_output_bytes"], len(output.encode("utf-8")))
            self.assertNotIn("stdout_preview", ground_truth)
