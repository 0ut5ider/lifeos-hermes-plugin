# ABOUTME: Checks all installed LifeOS SessionEnd handlers under parallel bridge dispatch.
# ABOUTME: Uses installed hook source with a disposable home and LifeOS directory.

import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from lifeos_hook_bridge.bridge import HookBridge


HOOK_DIR = os.environ.get("LIFEOS_SESSION_END_HOOK_DIR")
HOOK_NAMES = (
    "WorkCompletionLearning.hook.ts",
    "SessionCleanup.hook.ts",
    "UpdateCounts.hook.ts",
    "MemoryHealthGate.hook.ts",
    "DocIntegrity.hook.ts",
    "IntegrityCheck.hook.ts",
)


@unittest.skipUnless(HOOK_DIR and shutil.which("bun"), "installed LifeOS SessionEnd hooks and Bun are required")
class NativeSessionEndAllTests(unittest.TestCase):
    def test_all_six_handlers_complete_under_parallel_dispatch(self):
        with tempfile.TemporaryDirectory(prefix="lifeos-session-end-all-") as directory:
            home = Path(directory)
            root = home / ".claude"
            root.mkdir()
            settings = root / "settings.json"
            settings.write_text(json.dumps({"hooks": {
                "SessionEnd": [{"hooks": [
                    {"type": "command", "command": f"bun {Path(HOOK_DIR) / name}"}
                    for name in HOOK_NAMES
                ]}],
            }}))

            with patch.dict(os.environ, {"HOME": str(home)}):
                bridge = HookBridge(settings, root)
                bridge.environment["LIFEOS_NOTIFICATION_CHANNEL"] = "discord"
                try:
                    outcomes = bridge._run("SessionEnd", bridge._payload("SessionEnd", "all-six-probe"))
                finally:
                    bridge.close()

            self.assertEqual(len(outcomes), len(HOOK_NAMES))
            self.assertEqual([process.returncode for process, _ in outcomes], [0] * len(HOOK_NAMES))
