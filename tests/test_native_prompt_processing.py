# ABOUTME: Checks deterministic LifeOS prompt naming through the Hermes bridge.
# ABOUTME: Runs the installed prompt hook in a disposable home without model inference.

import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path

from lifeos_hook_bridge.bridge import HookBridge


HOOK_PATH = os.environ.get("LIFEOS_PROMPT_PROCESSING_PATH")


@unittest.skipUnless(HOOK_PATH and shutil.which("bun"), "LifeOS PromptProcessing and Bun are required")
class NativePromptProcessingTests(unittest.TestCase):
    def test_slash_prompt_creates_session_name_on_discord(self):
        with tempfile.TemporaryDirectory(prefix="lifeos-prompt-processing-") as directory:
            home = Path(directory)
            root = home / ".claude"
            root.mkdir()
            lifeos = root / "LIFEOS"
            lifeos.mkdir()
            settings = root / "settings.json"
            settings.write_text(json.dumps({"hooks": {"UserPromptSubmit": [{"hooks": [
                {"type": "command", "command": f"bun {HOOK_PATH}"},
            ]}]}}))
            bridge = HookBridge(settings, root)
            bridge.environment.update(
                HOME=str(home), LIFEOS_DIR=str(lifeos), LIFEOS_NOTIFICATION_CHANNEL="discord",
            )
            try:
                result = bridge.pre_llm_call("/Research", session_id="prompt-probe", platform="discord")
            finally:
                bridge.close()

            self.assertIsNone(result)
            names = json.loads((lifeos / "MEMORY/STATE/session-names.json").read_text())
            self.assertEqual(names["prompt-probe"], "Research Skill Run")
            rows = [json.loads(line) for line in bridge.transcript_path("prompt-probe").read_text().splitlines()]
            self.assertEqual(rows[-1]["message"]["content"], "/Research")
