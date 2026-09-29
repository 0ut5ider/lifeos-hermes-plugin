# ABOUTME: Tests dependency directory replacement from a fresh LifeOS reference install.
# ABOUTME: Ensures package roots stay inside LifeOS-owned paths and foreign packages survive.

import tempfile
import unittest
from pathlib import Path

from lifeos_hook_bridge.update_dependencies import UpdateDependencyConflict, sync_dependencies


class UpdateDependencyTests(unittest.TestCase):
    def test_replaces_package_and_generated_dependencies(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            old = root / "old"
            new = root / "new"
            reference = root / "reference"
            staged = root / "staged"
            for base in (old, new, reference, staged):
                (base / "skills/Example").mkdir(parents=True)
            (old / "skills/Example/package.json").write_text('{"version":"1"}')
            (new / "skills/Example/package.json").write_text('{"version":"2"}')
            (reference / "skills/Example/package.json").write_text('{"version":"2"}')
            (staged / "skills/Example/package.json").write_text('{"version":"1"}')
            (reference / "skills/Example/bun.lock").write_text("new-lock")
            (staged / "skills/Example/bun.lock").write_text("old-lock")
            (reference / "skills/Example/node_modules").mkdir()
            (staged / "skills/Example/node_modules").mkdir()
            (reference / "skills/Example/node_modules/library.txt").write_text("new library")
            (staged / "skills/Example/node_modules/library.txt").write_text("old library")
            (staged / "skills/Foreign").mkdir()
            (staged / "skills/Foreign/package.json").write_text("foreign")

            result = sync_dependencies(staged, old, new, reference)

            self.assertEqual(result["package_roots"], ["skills/Example"])
            self.assertEqual((staged / "skills/Example/package.json").read_text(), '{"version":"2"}')
            self.assertEqual((staged / "skills/Example/bun.lock").read_text(), "new-lock")
            self.assertEqual((staged / "skills/Example/node_modules/library.txt").read_text(), "new library")
            self.assertEqual((staged / "skills/Foreign/package.json").read_text(), "foreign")

    def test_rejects_collision_with_foreign_package_root(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ("old", "new", "reference", "staged"):
                (root / name / "skills/Example").mkdir(parents=True)
            (root / "new/skills/Example/package.json").write_text("new")
            (root / "reference/skills/Example/package.json").write_text("new")
            (root / "staged/skills/Example/package.json").write_text("foreign")
            with self.assertRaisesRegex(UpdateDependencyConflict, "collides"):
                sync_dependencies(root / "staged", root / "old", root / "new", root / "reference")

    def test_removes_dependency_tree_for_removed_package(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ("old", "new", "reference", "staged"):
                (root / name / "skills/Example").mkdir(parents=True)
            (root / "old/skills/Example/package.json").write_text("old")
            (root / "staged/skills/Example/package.json").write_text("old")
            (root / "staged/skills/Example/bun.lock").write_text("old-lock")
            (root / "staged/skills/Example/node_modules").mkdir()
            (root / "staged/skills/Example/node_modules/library.txt").write_text("old library")
            sync_dependencies(root / "staged", root / "old", root / "new", root / "reference")
            self.assertFalse((root / "staged/skills/Example/node_modules").exists())
            self.assertFalse((root / "staged/skills/Example/bun.lock").exists())
