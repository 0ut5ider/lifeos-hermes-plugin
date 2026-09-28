# ABOUTME: Verifies the native LifeOS HookHealer repairs a registered script at SessionStart.
# ABOUTME: Runs through the Hermes bridge with a disposable home and settings file.

import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from lifeos_hook_bridge.bridge import HookBridge


HEALER_PATH = os.environ.get("LIFEOS_HOOK_HEALER_PATH")


@unittest.skipUnless(HEALER_PATH and shutil.which("bun"), "LifeOS HookHealer and Bun are required")
class NativeHookHealerTests(unittest.TestCase):
    def test_session_start_heals_registered_direct_executable(self):
        with tempfile.TemporaryDirectory(prefix="lifeos-hook-healer-") as directory:
            home = Path(directory)
            claude_dir = home / ".claude"
            hooks_dir = claude_dir / "hooks"
            hooks_dir.mkdir(parents=True)
            target = hooks_dir / "Registered.hook.sh"
            target.write_text("#!/bin/sh\nexit 0\n")
            target.chmod(0o644)
            settings = claude_dir / "settings.json"
            settings.write_text(json.dumps({"hooks": {
                "SessionStart": [{"hooks": [{"type": "command", "command": f"bun {HEALER_PATH}"}]}],
                "Stop": [{"hooks": [{"type": "command", "command": "$HOME/.claude/hooks/Registered.hook.sh"}]}],
            }}))

            with patch.dict(os.environ, {"HOME": str(home)}):
                bridge = HookBridge(settings, claude_dir)
                try:
                    bridge.pre_llm_call("Begin", session_id="healer-probe")
                finally:
                    bridge.close()

            self.assertTrue(target.stat().st_mode & 0o111)
            rows = [json.loads(line) for line in (claude_dir / "LIFEOS/MEMORY/OBSERVABILITY/hook-healer.jsonl").read_text().splitlines()]
            self.assertTrue(any(row.get("event") == "healed" and row.get("path") == str(target) for row in rows))
