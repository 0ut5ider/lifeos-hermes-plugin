# ABOUTME: Checks native LifeOS model-rung feedback through Hermes prompt hooks.
# ABOUTME: Uses synthetic model names in a disposable bridge transcript.

import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path

from lifeos_hook_bridge.bridge import HookBridge
from lifeos_hook_bridge.model_tiers import configured_tiers


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

    def test_local_model_medium_effort_uses_sonnet_rung(self):
        with tempfile.TemporaryDirectory(prefix="lifeos-local-rung-") as directory:
            home = Path(directory)
            root = home / ".claude"
            lifeos = root / "LIFEOS"
            lifeos.mkdir(parents=True)
            settings = root / "settings.json"
            settings.write_text(json.dumps({
                "model": "fable",
                "hooks": {"UserPromptSubmit": [{"hooks": [
                    {"type": "command", "command": f"bun {HOOK_PATH}"},
                ]}]},
            }))
            bridge = HookBridge(settings, root, model_tiers_provider=lambda: configured_tiers(lambda key, default: default))
            bridge.environment.update(HOME=str(home), LIFEOS_DIR=str(lifeos))
            try:
                bridge.stop(
                    "Previous local answer", session_id="local-rung-probe",
                    model="flashnext-w4a16-fp8ple", reasoning_effort="medium",
                )
                result = bridge.pre_llm_call("Plan the design", session_id="local-rung-probe")
            finally:
                bridge.close()

            self.assertIn("MODEL RUNG", result["context"])
            self.assertIn("flashnext-w4a16-fp8ple", result["context"])
            transcript = json.loads(bridge.transcript_path("local-rung-probe").read_text().splitlines()[0])
            self.assertEqual(transcript["message"]["model"], "flashnext-w4a16-fp8ple")
            self.assertEqual(transcript["message"]["reasoning_effort"], "medium")
            row = json.loads((lifeos / "MEMORY/OBSERVABILITY/model-rung.jsonl").read_text().splitlines()[-1])
            self.assertEqual((row["event"], row["pin"], row["live"], row["gap"]),
                             ("off-pin", "fable", "sonnet", 2))

    def test_custom_tier_models_use_the_model_and_effort_pair(self):
        with tempfile.TemporaryDirectory(prefix="lifeos-custom-rung-") as directory:
            home = Path(directory)
            root = home / ".claude"
            lifeos = root / "LIFEOS"
            lifeos.mkdir(parents=True)
            settings = root / "settings.json"
            settings.write_text(json.dumps({
                "model": "fable",
                "hooks": {"UserPromptSubmit": [{"hooks": [
                    {"type": "command", "command": f"bun {HOOK_PATH}"},
                ]}]},
            }))
            values = {
                "sonnet_model": "balanced-local", "sonnet_effort": "high",
                "fable_model": "largest-local", "fable_effort": "ultra",
            }
            bridge = HookBridge(settings, root, model_tiers_provider=lambda: configured_tiers(values.get))
            bridge.environment.update(HOME=str(home), LIFEOS_DIR=str(lifeos))
            try:
                bridge.stop("Balanced answer", session_id="custom-rung", model="balanced-local", reasoning_effort="high")
                result = bridge.pre_llm_call("Plan the design", session_id="custom-rung")
                bridge.stop("Largest answer", session_id="custom-rung", model="largest-local", reasoning_effort="ultra")
                top_result = bridge.pre_llm_call("Continue", session_id="custom-rung")
            finally:
                bridge.close()

            self.assertIn("MODEL RUNG", result["context"])
            self.assertIsNone(top_result)
            rows = [json.loads(line) for line in (lifeos / "MEMORY/OBSERVABILITY/model-rung.jsonl").read_text().splitlines()]
            self.assertEqual((rows[-2]["live"], rows[-2]["reasoning_effort"], rows[-2]["gap"]),
                             ("sonnet", "high", 2))
            self.assertEqual((rows[-1]["event"], rows[-1]["live"], rows[-1]["reasoning_effort"]),
                             ("on-pin", "fable", "ultra"))

    def test_plugin_pin_classifies_local_model_settings(self):
        with tempfile.TemporaryDirectory(prefix="lifeos-local-pin-") as directory:
            home = Path(directory)
            root = home / ".claude"
            lifeos = root / "LIFEOS"
            lifeos.mkdir(parents=True)
            settings = root / "settings.json"
            settings.write_text(json.dumps({
                "model": "flashnext-w4a16-fp8ple",
                "hooks": {"UserPromptSubmit": [{"hooks": [
                    {"type": "command", "command": f"bun {HOOK_PATH}"},
                ]}]},
            }))
            tiers = {"pin": "fable", **configured_tiers(lambda key, default: default)}
            bridge = HookBridge(settings, root, model_tiers_provider=lambda: tiers)
            bridge.environment.update(HOME=str(home), LIFEOS_DIR=str(lifeos))
            try:
                bridge.stop("Local answer", session_id="pin-probe", model="flashnext-w4a16-fp8ple", reasoning_effort="medium")
                result = bridge.pre_llm_call("Plan the design", session_id="pin-probe")
            finally:
                bridge.close()

            self.assertIn("MODEL RUNG", result["context"])
            row = json.loads((lifeos / "MEMORY/OBSERVABILITY/model-rung.jsonl").read_text().splitlines()[-1])
            self.assertEqual((row["pin"], row["live"], row["gap"]), ("fable", "sonnet", 2))

    def test_local_model_names_do_not_override_configured_tiers(self):
        with tempfile.TemporaryDirectory(prefix="lifeos-tier-name-") as directory:
            home = Path(directory)
            root = home / ".claude"
            lifeos = root / "LIFEOS"
            lifeos.mkdir(parents=True)
            settings = root / "settings.json"
            settings.write_text(json.dumps({
                "model": "local-haiku-v2",
                "hooks": {"UserPromptSubmit": [{"hooks": [
                    {"type": "command", "command": f"bun {HOOK_PATH}"},
                ]}]},
            }))
            values = {"fable_model": "local-sonnet-v3", "fable_effort": "ultra"}
            tiers = {"pin": "fable", **configured_tiers(values.get)}
            bridge = HookBridge(settings, root, model_tiers_provider=lambda: tiers)
            bridge.environment.update(HOME=str(home), LIFEOS_DIR=str(lifeos))
            try:
                bridge.stop("Local answer", session_id="names-probe", model="local-sonnet-v3", reasoning_effort="ultra")
                result = bridge.pre_llm_call("Continue", session_id="names-probe")
            finally:
                bridge.close()

            self.assertIsNone(result)
            row = json.loads((lifeos / "MEMORY/OBSERVABILITY/model-rung.jsonl").read_text().splitlines()[-1])
            self.assertEqual((row["pin"], row["live"], row["event"]), ("fable", "fable", "on-pin"))
