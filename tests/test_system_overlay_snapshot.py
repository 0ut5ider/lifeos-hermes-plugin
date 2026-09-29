# ABOUTME: Exercises snapshots around LifeOS system overlays.
# ABOUTME: Verifies exact rollback and refusal after an intervening edit.

import tempfile
import unittest
from pathlib import Path

from scripts.system_overlay_snapshot import SnapshotError, restore_snapshot, take_snapshot, verify_overlay


class SystemOverlaySnapshotTests(unittest.TestCase):
    def test_restores_updated_and_created_system_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            payload = root / "payload"
            target = root / "target"
            snapshot = root / "snapshot"
            (payload / "hooks").mkdir(parents=True)
            (target / "hooks").mkdir(parents=True)
            (target / "LIFEOS/MEMORY").mkdir(parents=True)
            (target / "LIFEOS/MEMORY/user.txt").write_text("private")
            (payload / "hooks/current.ts").write_text("new")
            (payload / "hooks/added.ts").write_text("added")
            (target / "hooks/current.ts").write_text("old")

            manifest = take_snapshot(payload, target, snapshot)
            self.assertEqual([item["path"] for item in manifest["files"]], ["hooks/added.ts", "hooks/current.ts"])
            (target / "hooks/current.ts").write_text("new")
            (target / "hooks/added.ts").write_text("added")

            restore_snapshot(snapshot, target)
            self.assertEqual((target / "hooks/current.ts").read_text(), "old")
            self.assertFalse((target / "hooks/added.ts").exists())
            self.assertEqual((target / "LIFEOS/MEMORY/user.txt").read_text(), "private")

    def test_refuses_intervening_edit_before_restoring_any_file(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            payload = root / "payload"
            target = root / "target"
            (payload / "hooks").mkdir(parents=True)
            (target / "hooks").mkdir(parents=True)
            (payload / "hooks/first.ts").write_text("new-first")
            (payload / "hooks/second.ts").write_text("new-second")
            (target / "hooks/first.ts").write_text("old-first")
            (target / "hooks/second.ts").write_text("old-second")
            snapshot = root / "snapshot"
            take_snapshot(payload, target, snapshot)
            (target / "hooks/first.ts").write_text("new-first")
            (target / "hooks/second.ts").write_text("operator-edit")

            with self.assertRaises(SnapshotError):
                restore_snapshot(snapshot, target)
            self.assertEqual((target / "hooks/first.ts").read_text(), "new-first")
            self.assertEqual((target / "hooks/second.ts").read_text(), "operator-edit")

    def test_restores_partially_applied_overlay(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            payload = root / "payload"
            target = root / "target"
            (payload / "hooks").mkdir(parents=True)
            (target / "hooks").mkdir(parents=True)
            (target / "LIFEOS/MEMORY").mkdir(parents=True)
            (target / "LIFEOS/MEMORY/user.txt").write_text("private")
            (payload / "hooks/first.ts").write_text("new-first")
            (payload / "hooks/second.ts").write_text("new-second")
            (payload / "hooks/added.ts").write_text("added")
            (target / "hooks/first.ts").write_text("old-first")
            (target / "hooks/second.ts").write_text("old-second")
            snapshot = root / "snapshot"
            take_snapshot(payload, target, snapshot)
            (target / "hooks/first.ts").write_text("new-first")

            with self.assertRaises(SnapshotError):
                verify_overlay(snapshot, target)
            restore_snapshot(snapshot, target)
            self.assertEqual((target / "hooks/first.ts").read_text(), "old-first")
            self.assertEqual((target / "hooks/second.ts").read_text(), "old-second")
            self.assertFalse((target / "hooks/added.ts").exists())
            self.assertEqual((target / "LIFEOS/MEMORY/user.txt").read_text(), "private")

    def test_version_matches_lifeos_trimmed_marker(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            payload = root / "payload"
            target = root / "target"
            (payload / "LIFEOS").mkdir(parents=True)
            (target / "LIFEOS").mkdir(parents=True)
            (payload / "LIFEOS/VERSION").write_text("1.2.3\n")
            (target / "LIFEOS/VERSION").write_text("1.2.2\n")
            snapshot = root / "snapshot"
            take_snapshot(payload, target, snapshot)
            (target / "LIFEOS/VERSION").write_text("1.2.3")
            verify_overlay(snapshot, target)
            restore_snapshot(snapshot, target)
            self.assertEqual((target / "LIFEOS/VERSION").read_text(), "1.2.2\n")

    def test_preserves_divergent_file_before_restore(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            payload = root / "payload"
            target = root / "target"
            (payload / "hooks").mkdir(parents=True)
            (target / "hooks").mkdir(parents=True)
            (payload / "hooks/summary.md").write_text("release")
            (target / "hooks/summary.md").write_text("prior")
            snapshot = root / "snapshot"
            take_snapshot(payload, target, snapshot)
            (target / "hooks/summary.md").write_text("generated timestamp")

            result = restore_snapshot(snapshot, target, preserve_divergent=True)
            self.assertEqual(result["preserved_divergent"], ["hooks/summary.md"])
            self.assertEqual((target / "hooks/summary.md").read_text(), "prior")
            self.assertEqual((snapshot / "divergent/hooks/summary.md").read_text(), "generated timestamp")


if __name__ == "__main__":
    unittest.main()
