# ABOUTME: Checks the native LifeOS format contract through Hermes prompt hooks.
# ABOUTME: Runs the installed DriftReminder in a disposable LifeOS root.

import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path

from lifeos_hook_bridge.bridge import HookBridge


HOOK_PATH = os.environ.get("LIFEOS_DRIFT_REMINDER_PATH")


@unittest.skipUnless(HOOK_PATH and shutil.which("bun"), "LifeOS DriftReminder and Bun are required")
class NativeDriftReminderTests(unittest.TestCase):
    def test_each_prompt_gets_its_line_budget(self):
        with tempfile.TemporaryDirectory(prefix="lifeos-drift-reminder-") as directory:
            root = Path(directory) / "LIFEOS"
            root.mkdir()
            settings = root / "settings.json"
            settings.write_text(json.dumps({"hooks": {"UserPromptSubmit": [{"hooks": [
                {"type": "command", "command": f"bun {HOOK_PATH}"},
            ]}]}}))
            bridge = HookBridge(settings, root)
            bridge.environment["LIFEOS_DIR"] = str(root)
            try:
                brief = bridge.pre_llm_call("Hello", session_id="format-probe")
                detailed = bridge.pre_llm_call("Give a detailed report", session_id="format-probe")
            finally:
                bridge.close()

            self.assertIn("max 15 prose lines", brief["context"])
            self.assertIn("depth requested, line cap lifted", detailed["context"])
            state = json.loads((root / "MEMORY/STATE/drift-reminder.json").read_text())
            self.assertEqual(state["turn_count"], 2)
