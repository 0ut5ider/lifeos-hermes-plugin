# ABOUTME: Checks coordinated Hermes, bridge, and LifeOS release rollback.
# ABOUTME: Uses real files so partial changes and user-data preservation are observable.

import tempfile
import unittest
from pathlib import Path

from scripts.release_transaction import ReleaseError, apply_release, restore_release, stage_release
from scripts.system_overlay_snapshot import SnapshotError


class ReleaseTransactionTests(unittest.TestCase):
    def fixture(self, root):
        current_hermes = root / "current-hermes"
        next_hermes = root / "next-hermes"
        current_plugin = root / "current-plugin"
        next_plugin = root / "next-plugin"
        target = root / "claude"
        payload = root / "payload"
        for directory in (current_hermes, next_hermes, current_plugin, next_plugin,
                          target / "hooks", target / "LIFEOS/MEMORY", payload / "hooks"):
            directory.mkdir(parents=True)
        (current_hermes / "agent.py").write_text("old-agent")
        (current_hermes / "retired.py").write_text("retired")
        (current_hermes / ".git").mkdir()
        (current_hermes / ".git/config").write_text("keep-git")
        (next_hermes / "agent.py").write_text("new-agent")
        (current_plugin / "bridge.py").write_text("old-bridge")
        (next_plugin / "bridge.py").write_text("new-bridge")
        (target / "hooks/check.ts").write_text("old-hook")
        (payload / "hooks/check.ts").write_text("new-hook")
        (payload / "hooks/added.ts").write_text("added")
        (target / "LIFEOS/MEMORY/user.txt").write_text("private")
        config = root / "config.yaml"
        config.write_text("private-config")
        snapshot = root / "snapshot"
        stage_release(snapshot, current_hermes, next_hermes, current_plugin,
                      next_plugin, payload, target, config)
        return snapshot, current_hermes, current_plugin, target, payload, config

    def test_applies_coordinated_release_and_preserves_user_data(self):
        with tempfile.TemporaryDirectory() as directory:
            snapshot, hermes, plugin, target, payload, config = self.fixture(Path(directory))
            calls = []

            def overlay():
                for source in (payload / "hooks").iterdir():
                    (target / "hooks" / source.name).write_bytes(source.read_bytes())

            apply_release(snapshot, overlay=overlay,
                          verify=lambda: calls.append("verified"),
                          stop=lambda: calls.append("stopped"),
                          start=lambda: calls.append("started"))
            self.assertEqual(calls, ["stopped", "started", "verified"])
            self.assertEqual((hermes / "agent.py").read_text(), "new-agent")
            self.assertFalse((hermes / "retired.py").exists())
            self.assertEqual((hermes / ".git/config").read_text(), "keep-git")
            self.assertEqual((plugin / "bridge.py").read_text(), "new-bridge")
            self.assertEqual((target / "hooks/check.ts").read_text(), "new-hook")
            self.assertEqual((target / "LIFEOS/MEMORY/user.txt").read_text(), "private")
            self.assertEqual(config.read_text(), "private-config")

    def test_failed_verification_restores_code_and_partial_overlay(self):
        with tempfile.TemporaryDirectory() as directory:
            snapshot, hermes, plugin, target, payload, config = self.fixture(Path(directory))
            calls = []

            def partial_overlay():
                (target / "hooks/check.ts").write_text("new-hook")

            with self.assertRaises(SnapshotError):
                apply_release(snapshot, overlay=partial_overlay, verify=lambda: None,
                              stop=lambda: calls.append("stopped"),
                              start=lambda: calls.append("started"))
            self.assertEqual(calls, ["stopped", "started"])
            self.assertEqual((hermes / "agent.py").read_text(), "old-agent")
            self.assertEqual((hermes / "retired.py").read_text(), "retired")
            self.assertEqual((plugin / "bridge.py").read_text(), "old-bridge")
            self.assertEqual((target / "hooks/check.ts").read_text(), "old-hook")
            self.assertFalse((target / "hooks/added.ts").exists())
            self.assertEqual((target / "LIFEOS/MEMORY/user.txt").read_text(), "private")
            self.assertEqual(config.read_text(), "private-config")
            restore_release(snapshot)

    def test_failed_runtime_check_stops_gateway_before_restoring(self):
        with tempfile.TemporaryDirectory() as directory:
            snapshot, hermes, plugin, target, payload, config = self.fixture(Path(directory))
            calls = []

            def overlay():
                for source in (payload / "hooks").iterdir():
                    (target / "hooks" / source.name).write_bytes(source.read_bytes())

            def fail_check():
                config.write_text("changed-during-update")
                raise RuntimeError("synthetic runtime failure")

            with self.assertRaisesRegex(RuntimeError, "synthetic runtime failure"):
                apply_release(snapshot, overlay=overlay, verify=fail_check,
                              stop=lambda: calls.append("stopped"),
                              start=lambda: calls.append("started"))
            self.assertEqual(calls, ["stopped", "started", "stopped", "started"])
            self.assertEqual((hermes / "agent.py").read_text(), "old-agent")
            self.assertEqual((plugin / "bridge.py").read_text(), "old-bridge")
            self.assertEqual((target / "hooks/check.ts").read_text(), "old-hook")
            self.assertEqual(config.read_text(), "private-config")

    def test_candidate_change_refuses_release_before_stopping_gateway(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            snapshot, hermes, plugin, target, payload, config = self.fixture(root)
            (root / "next-hermes/agent.py").write_text("changed-after-stage")
            calls = []

            with self.assertRaisesRegex(ReleaseError, "hermes_after"):
                apply_release(snapshot, overlay=lambda: calls.append("overlay"),
                              verify=lambda: calls.append("verify"),
                              stop=lambda: calls.append("stopped"),
                              start=lambda: calls.append("started"))
            self.assertEqual(calls, [])
            self.assertEqual((hermes / "agent.py").read_text(), "old-agent")
            self.assertEqual((plugin / "bridge.py").read_text(), "old-bridge")
            self.assertEqual((target / "hooks/check.ts").read_text(), "old-hook")
            self.assertEqual(config.read_text(), "private-config")

    def test_lifeos_payload_change_refuses_release_before_stopping_gateway(self):
        with tempfile.TemporaryDirectory() as directory:
            snapshot, hermes, plugin, target, payload, config = self.fixture(Path(directory))
            (payload / "hooks/check.ts").write_text("changed-after-stage")
            calls = []

            with self.assertRaisesRegex(ReleaseError, "lifeos_payload"):
                apply_release(snapshot, overlay=lambda: calls.append("overlay"),
                              verify=lambda: calls.append("verify"),
                              stop=lambda: calls.append("stopped"),
                              start=lambda: calls.append("started"))
            self.assertEqual(calls, [])
            self.assertEqual((hermes / "agent.py").read_text(), "old-agent")
            self.assertEqual((plugin / "bridge.py").read_text(), "old-bridge")
            self.assertEqual((target / "hooks/check.ts").read_text(), "old-hook")
            self.assertEqual(config.read_text(), "private-config")


if __name__ == "__main__":
    unittest.main()
