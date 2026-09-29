# ABOUTME: Tests LifeOS update file ownership against a fresh candidate install.
# ABOUTME: Rejects changed system files and collisions while leaving user data outside the plan.

import hashlib
import tempfile
import unittest
from pathlib import Path

from lifeos_hook_bridge.update_plan import UpdateConflict, apply_system_plan, plan_system_files


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class UpdatePlanTests(unittest.TestCase):
    def fixture(self, root):
        current = root / "home/.claude"
        reference = root / "reference/.claude"
        source = root / "candidate/LifeOS/install"
        for tree in (current, reference, source):
            (tree / "hooks").mkdir(parents=True)
        (current / "hooks/kept.ts").write_text("v1")
        (current / "hooks/removed.ts").write_text("removed")
        (current / "LIFEOS/USER").mkdir(parents=True)
        (current / "LIFEOS/USER/principal.txt").write_text("private")
        (source / "hooks/kept.ts").write_text("v2")
        (source / "hooks/added.ts").write_text("added")
        (reference / "hooks/kept.ts").write_text("v2")
        (reference / "hooks/added.ts").write_text("added")
        baseline = {"installed_root": str(current.resolve()), "files": {
            "hooks/kept.ts": digest(current / "hooks/kept.ts"),
            "hooks/removed.ts": digest(current / "hooks/removed.ts"),
        }}
        return current, reference, source, baseline

    def test_plans_replacement_addition_and_removal(self):
        with tempfile.TemporaryDirectory() as directory:
            current, reference, source, baseline = self.fixture(Path(directory))
            plan = plan_system_files(current, baseline, source, reference)
            self.assertEqual(plan["replace"], ["hooks/kept.ts"])
            self.assertEqual(plan["add"], ["hooks/added.ts"])
            self.assertEqual(plan["remove"], ["hooks/removed.ts"])
            self.assertEqual((current / "LIFEOS/USER/principal.txt").read_text(), "private")

    def test_applies_plan_to_staged_tree_without_touching_live_data(self):
        with tempfile.TemporaryDirectory() as directory:
            current, reference, source, baseline = self.fixture(Path(directory))
            staged = Path(directory) / "staged"
            import shutil
            shutil.copytree(current, staged, symlinks=True)
            plan = plan_system_files(current, baseline, source, reference)
            apply_system_plan(staged, source, plan)
            self.assertEqual((staged / "hooks/kept.ts").read_text(), "v2")
            self.assertEqual((staged / "hooks/added.ts").read_text(), "added")
            self.assertFalse((staged / "hooks/removed.ts").exists())
            self.assertEqual((staged / "LIFEOS/USER/principal.txt").read_text(), "private")
            self.assertEqual((current / "hooks/kept.ts").read_text(), "v1")

    def test_rejects_edited_managed_file(self):
        with tempfile.TemporaryDirectory() as directory:
            current, reference, source, baseline = self.fixture(Path(directory))
            (current / "hooks/kept.ts").write_text("operator edit")
            with self.assertRaisesRegex(UpdateConflict, "changed since baseline"):
                plan_system_files(current, baseline, source, reference)

    def test_rejects_new_file_collision(self):
        with tempfile.TemporaryDirectory() as directory:
            current, reference, source, baseline = self.fixture(Path(directory))
            (current / "hooks/added.ts").write_text("foreign")
            with self.assertRaisesRegex(UpdateConflict, "collides"):
                plan_system_files(current, baseline, source, reference)

    def test_ignores_payload_file_not_deployed_by_fresh_installer(self):
        with tempfile.TemporaryDirectory() as directory:
            current, reference, source, baseline = self.fixture(Path(directory))
            (source / "hooks/not-installed.ts").write_text("source only")
            plan = plan_system_files(current, baseline, source, reference)
            self.assertNotIn("hooks/not-installed.ts", plan["add"])

    def test_rejects_reference_file_that_differs_from_source(self):
        with tempfile.TemporaryDirectory() as directory:
            current, reference, source, baseline = self.fixture(Path(directory))
            (reference / "hooks/kept.ts").write_text("transformed")
            with self.assertRaisesRegex(UpdateConflict, "differs from source"):
                plan_system_files(current, baseline, source, reference)

    def test_does_not_follow_managed_path_symlink(self):
        with tempfile.TemporaryDirectory() as directory:
            current, reference, source, baseline = self.fixture(Path(directory))
            (current / "hooks/added.ts").symlink_to(current / "LIFEOS/USER/principal.txt")
            with self.assertRaisesRegex(UpdateConflict, "symbolic link"):
                plan_system_files(current, baseline, source, reference)

    def test_preserves_tracked_lockfile_generated_by_dependency_install(self):
        with tempfile.TemporaryDirectory() as directory:
            current, reference, source, baseline = self.fixture(Path(directory))
            (current / "hooks/bun.lock").write_text("old generated lock")
            (source / "hooks/bun.lock").write_text("source lock")
            (reference / "hooks/bun.lock").write_text("new generated lock")
            baseline["files"]["hooks/bun.lock"] = digest(current / "hooks/bun.lock")
            plan = plan_system_files(current, baseline, source, reference)
            self.assertNotIn("hooks/bun.lock", plan["remove"])
            self.assertIn("hooks/bun.lock", plan["dependency_locks"])


if __name__ == "__main__":
    unittest.main()
