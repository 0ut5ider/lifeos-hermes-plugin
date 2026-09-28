# ABOUTME: Checks native LifeOS model-rung feedback through Hermes prompt hooks.
# ABOUTME: Uses synthetic model names in a disposable bridge transcript.

import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path

from lifeos_hook_bridge.bridge import HookBridge


HOOK_PATH = os.environ.get("LIFEOS_MODEL_RUNG_GUARD_PATH")


@unittest.skipUnless(HOOK_PATH and shutil.which("bun"), "LifeOS ModelRungGuard and Bun are required")
class NativeModelRungGuardTests(unittest.TestCase):
    def test_lower_transcript_rung_warns_at_next_prompt(self):
        with tempfile.TemporaryDirectory(prefix="lifeos-model-rung-") as directory:
            home = Path(directory)
            root = home / ".claude"
            root.mkdir()
            lifeos = root / "LIFEOS"
            lifeos.mkdir()
            settings = root / "settings.json"
            settings.write_text(json.dumps({
                "model": "fable",
                "hooks": {"UserPromptSubmit": [{"hooks": [
                    {"type": "command", "command": f"bun {HOOK_PATH}"},
                ]}]},
            }))
            bridge = HookBridge(settings, root)
            bridge.environment.update(HOME=str(home), LIFEOS_DIR=str(lifeos))
            try:
                bridge.stop("Previous synthetic answer", session_id="rung-probe", model="claude-sonnet")
                result = bridge.pre_llm_call("Plan the design", session_id="rung-probe")
            finally:
                bridge.close()

            self.assertIn("MODEL RUNG", result["context"])
            self.assertIn("claude-sonnet", result["context"])
            row = json.loads((lifeos / "MEMORY/OBSERVABILITY/model-rung.jsonl").read_text().splitlines()[-1])
            self.assertEqual((row["event"], row["pin"], row["live"], row["gap"]),
                             ("off-pin", "fable", "sonnet", 2))
