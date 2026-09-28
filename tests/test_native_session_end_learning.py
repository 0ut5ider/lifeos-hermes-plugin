# ABOUTME: Checks LifeOS work learning after the SessionEnd cleanup has completed.
# ABOUTME: Uses native hooks and a disposable work registry through the Hermes bridge.

import json
import os
import shutil
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from lifeos_hook_bridge.bridge import HookBridge


LEARNING_PATH = os.environ.get("LIFEOS_WORK_COMPLETION_PATH")
CLEANUP_PATH = os.environ.get("LIFEOS_SESSION_CLEANUP_PATH")


@unittest.skipUnless(LEARNING_PATH and CLEANUP_PATH and shutil.which("bun"), "LifeOS SessionEnd hooks and Bun are required")
class NativeSessionEndLearningTests(unittest.TestCase):
    def test_learning_survives_cleanup_finishing_first(self):
        with tempfile.TemporaryDirectory(prefix="lifeos-session-end-") as directory:
            root = Path(directory)
            lifeos = root / "LIFEOS"
            state = lifeos / "MEMORY/STATE"
            work = lifeos / "MEMORY/WORK/order-probe"
            state.mkdir(parents=True)
            work.mkdir(parents=True)
            session_id = "session-end-order-probe"
            now = datetime.now(timezone.utc).isoformat()
            registry = {"sessions": {"order-probe": {
                "sessionUUID": session_id, "phase": "execute", "task": "Verify learning order",
                "updatedAt": now, "started": now, "progress": "1/1", "isa": True,
            }}}
            (state / "work.json").write_text(json.dumps(registry))
            (work / "ISA.md").write_text(
                f"---\ntask: Verify learning order\nphase: execute\nstatus: ACTIVE\n"
                f"created_at: {now}\ncompleted_at: null\nupdated: {now}\n---\n"
                "# Order probe\n\n## Claims\n- [x] Learning survives cleanup\n"
            )
            settings = root / "settings.json"

            def run_hook(command):
                settings.write_text(json.dumps({"hooks": {
                    "SessionEnd": [{"hooks": [{"type": "command", "command": f"bun {command}"}]}],
                }}))
                bridge = HookBridge(settings, root)
                bridge.environment["LIFEOS_NOTIFICATION_CHANNEL"] = "discord"
                try:
                    bridge.session_end(session_id=session_id)
                finally:
                    bridge.close()

            run_hook(CLEANUP_PATH)
            completed = json.loads((state / "work.json").read_text())
            self.assertEqual(completed["sessions"]["order-probe"]["phase"], "complete")
            self.assertIn("phase: complete", (work / "ISA.md").read_text())

            run_hook(LEARNING_PATH)
            learnings = list((lifeos / "MEMORY/LEARNING").rglob("*_work_*.md"))
            self.assertEqual(len(learnings), 1)
            self.assertIn(f"**Session:** {session_id}", learnings[0].read_text())
            self.assertIn("1/1 closed", learnings[0].read_text())
