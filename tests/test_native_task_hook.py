# ABOUTME: Exercises the optional Hermes count adapter in LifeOS TaskGovernance.
# ABOUTME: Set LIFEOS_TASK_HOOK_PATH to run against a patched LifeOS checkout.

import json
import os
import shutil
import subprocess
import unittest
from pathlib import Path


HOOK_PATH = os.environ.get("LIFEOS_TASK_HOOK_PATH")


@unittest.skipUnless(HOOK_PATH and shutil.which("bun"), "LifeOS hook and Bun are required")
class NativeTaskHookTests(unittest.TestCase):
    def invoke(self, **fields):
        payload = {"hook_event_name": "TaskCreated", "session_id": "hermes-test", **fields}
        return subprocess.run(
            ["bun", HOOK_PATH], input=json.dumps(payload), text=True, capture_output=True, timeout=10,
        )

    def test_capability_probe_has_no_task_description(self):
        result = self.invoke(hermes_bridge_probe=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), {"hermes_bridge_task_governance": 1})

    def test_external_count_controls_limit_without_writing_legacy_counter(self):
        legacy = Path("/tmp/pai-task-governance.json")
        before = legacy.stat().st_mtime_ns if legacy.exists() else None
        accepted = self.invoke(task_description="Meaningful task description", hermes_task_count=49)
        denied = self.invoke(task_description="Meaningful task description", hermes_task_count=50)
        self.assertEqual(accepted.returncode, 0, accepted.stderr)
        self.assertEqual(denied.returncode, 2)
        self.assertIn("session limit of 50", denied.stderr)
        after = legacy.stat().st_mtime_ns if legacy.exists() else None
        self.assertEqual(after, before)

    def test_short_description_blocks_with_external_count(self):
        result = self.invoke(task_description="short", hermes_task_count=0)
        self.assertEqual(result.returncode, 2)
        self.assertIn("description too short", result.stderr)
