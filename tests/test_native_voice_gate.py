# ABOUTME: Verifies LifeOS skips desktop voice output for a remote Hermes turn.
# ABOUTME: Uses the native VoiceCompletion hook and a disposable LifeOS root.

import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path

from lifeos_hook_bridge.bridge import HookBridge


VOICE_HOOK_PATH = os.environ.get("LIFEOS_VOICE_HOOK_PATH")


@unittest.skipUnless(VOICE_HOOK_PATH and shutil.which("bun"), "LifeOS VoiceCompletion and Bun are required")
class NativeVoiceGateTests(unittest.TestCase):
    def test_discord_turn_skips_desktop_voice_with_term_set(self):
        with tempfile.TemporaryDirectory(prefix="voice-gate-parity-") as directory:
            root = Path(directory)
            home = root / "home"
            home.mkdir()
            settings = root / "settings.json"
            settings.write_text(json.dumps({"hooks": {"Stop": [{"hooks": [
                {"type": "command", "command": f"bun {VOICE_HOOK_PATH}"},
            ]}]}}))
            bridge = HookBridge(settings, root)
            bridge.environment["HOME"] = str(home)
            bridge.environment["TERM"] = "xterm"
            try:
                bridge.pre_llm_call("Say done", session_id="discord-voice-probe", platform="discord")
                bridge.stop(
                    "🗣️ Test Operator: The task is complete.",
                    session_id="discord-voice-probe", platform="discord",
                )
            finally:
                bridge.close()

            voice_events = root / "LIFEOS/MEMORY/VOICE/voice-events.jsonl"
            self.assertTrue(voice_events.exists())
            events = [json.loads(line) for line in voice_events.read_text().splitlines()]
            self.assertEqual(len(events), 1)
            self.assertEqual(events[0]["hook"], "VoiceCompletion")
            self.assertEqual(events[0]["reason"], "remote_channel:discord")

    def test_discord_turn_blocks_speaker_command_before_execution(self):
        guard = Path(VOICE_HOOK_PATH).with_name("PreToolGuard.hook.ts")
        if not guard.exists():
            self.skipTest("LifeOS PreToolGuard is required")

        with tempfile.TemporaryDirectory(prefix="voice-egress-parity-") as directory:
            root = Path(directory)
            home = root / "home"
            home.mkdir()
            settings = root / "settings.json"
            settings.write_text(json.dumps({"hooks": {"PreToolUse": [{
                "matcher": "Bash", "hooks": [{"type": "command", "command": f"bun {guard}"}],
            }]}}))
            bridge = HookBridge(settings, root)
            bridge.environment["HOME"] = str(home)
            bridge.environment["TERM"] = "xterm"
            try:
                bridge.pre_llm_call("Announce done", session_id="discord-speaker-probe", platform="discord")
                result = bridge.pre_tool_call(
                    "terminal", {"command": "curl http://127.0.0.1:31337/notify"},
                    session_id="discord-speaker-probe",
                )
            finally:
                bridge.close()

            self.assertIsNotNone(result)
            self.assertEqual(result["action"], "block")
            self.assertIn("VoiceEgressGuard", result["message"])
