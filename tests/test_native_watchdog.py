# ABOUTME: Exercises the LifeOS watchdog path adapter with isolated fixture files.
# ABOUTME: Set LIFEOS_WATCHDOG_PATH to run against a patched LifeOS checkout.

import json
import os
import shutil
import subprocess
import tempfile
import time
import unittest
from pathlib import Path


WATCHDOG_PATH = os.environ.get("LIFEOS_WATCHDOG_PATH")


@unittest.skipUnless(WATCHDOG_PATH and shutil.which("bun"), "LifeOS watchdog and Bun are required")
class NativeWatchdogTests(unittest.TestCase):
    def test_active_agent_with_silent_activity_emits_alert(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            starts = root / "starts.json"
            activity = root / "activity.jsonl"
            starts.write_text(json.dumps({"session::agent": {"subagent_type": "general-purpose"}}))
            activity.touch()
            old = time.time() - 10
            os.utime(activity, (old, old))
            env = {
                **os.environ,
                "LIFEOS_WATCHDOG_STARTS_FILE": str(starts),
                "LIFEOS_WATCHDOG_ACTIVITY_FILE": str(activity),
                "LIFEOS_WATCHDOG_SILENCE_SECONDS": "1",
                "LIFEOS_WATCHDOG_CHECK_SECONDS": "1",
            }
            process = subprocess.Popen(
                ["bun", WATCHDOG_PATH], text=True, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, env=env,
            )
            try:
                time.sleep(2.2)
            finally:
                process.terminate()
            output, errors = process.communicate(timeout=5)
            self.assertIn("WATCHDOG: No tool activity", output, errors)
            self.assertIn("general-purpose", output)
            self.assertIn("Check the background task status in Hermes.", output)
