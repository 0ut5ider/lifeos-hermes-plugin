# ABOUTME: Verifies the native LifeOS settings merge runs from Hermes SessionStart.
# ABOUTME: Uses a disposable home so the installed settings remain untouched.

import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from lifeos_hook_bridge.bridge import HookBridge


MERGE_PATH = os.environ.get("LIFEOS_MERGE_SETTINGS_PATH")
BACKPORT_PATH = os.environ.get("LIFEOS_SETTINGS_BACKPORT_PATH")


@unittest.skipUnless(MERGE_PATH and shutil.which("bun"), "LifeOS MergeSettings and Bun are required")
class NativeSettingsMergeTests(unittest.TestCase):
    @unittest.skipUnless(BACKPORT_PATH, "LifeOS SettingsBackport is required")
    def test_session_start_backports_direct_edit_before_merge(self):
        with tempfile.TemporaryDirectory(prefix="lifeos-settings-backport-") as directory:
            home = Path(directory)
            claude_dir = home / ".claude"
            overlay_dir = claude_dir / "LIFEOS/USER/CONFIG"
            state_dir = claude_dir / "LIFEOS/MEMORY/STATE"
            overlay_dir.mkdir(parents=True)
            state_dir.mkdir(parents=True)
            settings = claude_dir / "settings.json"
            system = claude_dir / "settings.system.json"
            user = overlay_dir / "settings.user.json"
            command = (
                f"bun {BACKPORT_PATH}; "
                f"bun {MERGE_PATH} --system {system} --user {user} --output {settings}"
            )
            system_data = {"hooks": {
                "SessionStart": [{"hooks": [{"type": "command", "command": command}]}],
            }, "env": {"SYSTEM_VALUE": "system"}}
            old_merged = {**system_data, "env": {**system_data["env"], "USER_VALUE": "original"}}
            live_edited = {**old_merged, "env": {**old_merged["env"], "USER_VALUE": "edited"}}
            system.write_text(json.dumps(system_data))
            user.write_text(json.dumps({"env": {"USER_VALUE": "original"}}))
            settings.write_text(json.dumps(live_edited))
            (state_dir / "settings-merge-snapshot.json").write_text(json.dumps(old_merged))

            with patch.dict(os.environ, {"HOME": str(home)}):
                bridge = HookBridge(settings, claude_dir)
                try:
                    bridge.pre_llm_call("Begin", session_id="settings-backport-probe")
                finally:
                    bridge.close()

            self.assertEqual(json.loads(user.read_text())["env"]["USER_VALUE"], "edited")
            self.assertEqual(json.loads(settings.read_text())["env"]["USER_VALUE"], "edited")

    def test_session_start_merges_user_overlay_and_writes_snapshot(self):
        with tempfile.TemporaryDirectory(prefix="lifeos-settings-merge-") as directory:
            home = Path(directory)
            claude_dir = home / ".claude"
            overlay_dir = claude_dir / "LIFEOS/USER/CONFIG"
            overlay_dir.mkdir(parents=True)
            settings = claude_dir / "settings.json"
            system = claude_dir / "settings.system.json"
            user = overlay_dir / "settings.user.json"
            command = (
                f"bun {MERGE_PATH} --system {system} --user {user} --output {settings}"
            )
            system.write_text(json.dumps({"hooks": {
                "SessionStart": [{"hooks": [{"type": "command", "command": command}]}],
            }, "env": {"SYSTEM_VALUE": "system"}}))
            user.write_text(json.dumps({"env": {"USER_VALUE": "overlay"}}))
            settings.write_text(system.read_text())

            with patch.dict(os.environ, {"HOME": str(home)}):
                bridge = HookBridge(settings, claude_dir)
                try:
                    bridge.pre_llm_call("Begin", session_id="settings-merge-probe")
                finally:
                    bridge.close()

            merged = json.loads(settings.read_text())
            self.assertEqual(merged["env"]["SYSTEM_VALUE"], "system")
            self.assertEqual(merged["env"]["USER_VALUE"], "overlay")
            snapshot = claude_dir / "LIFEOS/MEMORY/STATE/settings-merge-snapshot.json"
            self.assertEqual(json.loads(snapshot.read_text()), merged)
