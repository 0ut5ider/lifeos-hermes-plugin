# ABOUTME: Checks staging of patched Hermes files from the owner's checkout without changing the checkout.
# ABOUTME: Uses disposable real Git sources and the compatibility manifest's exact file identities.
import hashlib
import os
from pathlib import Path
import stat
import subprocess
import tempfile
import unittest

from optional.lifeos_release_manager.host_compatibility import load_manifest
from optional.lifeos_release_manager.host_patches import HostPatchRejected, stage_host_files


STOCK = "VALID_HOOKS = {'pre_tool_call'}\n"
PATCHED = "VALID_HOOKS = {'pre_tool_call', 'pre_turn_stop'}\n"
ADDED = "ENABLED = True\n"
SCRIPT = "#!/bin/sh\necho stock\n"
SCRIPT_PATCHED = "#!/bin/sh\necho patched\n"


def git(*args, cwd):
    return subprocess.run(["git", *args], cwd=cwd, check=True, text=True, capture_output=True).stdout.strip()


def digest(text):
    return hashlib.sha256(text.encode()).hexdigest()


class HostPatchStageTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.root = Path(self.folder.name)
        self.source = self.root / "hermes-agent"
        (self.source / "hermes_cli").mkdir(parents=True)
        (self.source / "scripts").mkdir()
        git("init", "-q", "-b", "main", cwd=self.source)
        (self.source / "hermes_cli/plugins.py").write_text(STOCK)
        (self.source / "scripts/run_tests.sh").write_text(SCRIPT)
        (self.source / "scripts/run_tests.sh").chmod(0o755)
        (self.source / "model_tools.py").write_text("TOOLS = []\n")
        git("add", ".", cwd=self.source)
        git("-c", "user.name=Test", "-c", "user.email=test@example.invalid", "commit", "-qm", "base", cwd=self.source)
        self.patches = self.root / "patches"
        self.patches.mkdir()
        (self.source / "hermes_cli/plugins.py").write_text(PATCHED)
        (self.source / "hermes_cli/new_hook.py").write_text(ADDED)
        git("add", "-N", "hermes_cli/new_hook.py", cwd=self.source)
        (self.patches / "first.patch").write_text(git("diff", "--", "hermes_cli", cwd=self.source) + "\n")
        git("reset", "-q", cwd=self.source)
        (self.source / "hermes_cli/new_hook.py").unlink()
        git("checkout", "--", ".", cwd=self.source)
        (self.source / "scripts/run_tests.sh").write_text(SCRIPT_PATCHED)
        (self.patches / "second.patch").write_text(git("diff", cwd=self.source) + "\n")
        git("checkout", "--", ".", cwd=self.source)
        self.entry = load_manifest({"format": 1, "dependencies": [], "hermes": [{
            "label": "v0.0.1", "commit": git("rev-parse", "HEAD", cwd=self.source),
            "patches": [{"name": name, "sha256": hashlib.sha256((self.patches / name).read_bytes()).hexdigest()}
                        for name in ("first.patch", "second.patch")],
            "files": {
                "hermes_cli/plugins.py": {"stock": digest(STOCK), "patched": digest(PATCHED)},
                "hermes_cli/new_hook.py": {"stock": None, "patched": digest(ADDED)},
                "scripts/run_tests.sh": {"stock": digest(SCRIPT), "patched": digest(SCRIPT_PATCHED)},
            }, "python": "3.14", "capabilities": {"hooks": ["pre_turn_stop"], "middleware_api": 1}}]})["hermes"][0]
        self.destination = self.root / "job/host"
        self.destination.parent.mkdir()

    def test_stages_every_patched_file_with_upstream_modes_and_retained_originals(self):
        staged = stage_host_files(self.source, self.entry, self.patches, self.destination)
        self.assertEqual(set(staged), {"hermes_cli/plugins.py", "hermes_cli/new_hook.py", "scripts/run_tests.sh"})
        self.assertEqual(staged["hermes_cli/plugins.py"]["patched"].read_text(), PATCHED)
        self.assertEqual(staged["hermes_cli/plugins.py"]["stock"].read_text(), STOCK)
        self.assertIsNone(staged["hermes_cli/new_hook.py"]["stock"])
        self.assertEqual(staged["hermes_cli/new_hook.py"]["patched"].read_text(), ADDED)
        modes = {name: stat.S_IMODE(value["patched"].stat().st_mode) for name, value in staged.items()}
        self.assertEqual(modes, {"hermes_cli/plugins.py": 0o644, "hermes_cli/new_hook.py": 0o644,
                                 "scripts/run_tests.sh": 0o755})
        self.assertEqual(stat.S_IMODE(staged["scripts/run_tests.sh"]["stock"].stat().st_mode), 0o755)
        self.assertEqual(git("status", "--porcelain", "--untracked-files=all", cwd=self.source), "")

    def test_changed_patch_file_is_refused(self):
        (self.patches / "second.patch").write_text((self.patches / "second.patch").read_text() + "\n")
        with self.assertRaisesRegex(HostPatchRejected, "second.patch"):
            stage_host_files(self.source, self.entry, self.patches, self.destination)
        self.assertFalse(self.destination.exists())

    def test_locally_edited_target_is_refused(self):
        (self.source / "hermes_cli/plugins.py").write_text(STOCK + "# local\n")
        with self.assertRaisesRegex(HostPatchRejected, "hermes_cli/plugins.py"):
            stage_host_files(self.source, self.entry, self.patches, self.destination)
        self.assertFalse(self.destination.exists())

    def test_present_added_target_is_refused(self):
        (self.source / "hermes_cli/new_hook.py").write_text(ADDED)
        with self.assertRaisesRegex(HostPatchRejected, "hermes_cli/new_hook.py"):
            stage_host_files(self.source, self.entry, self.patches, self.destination)

    def test_patch_result_that_differs_from_the_manifest_is_refused(self):
        entry = {**self.entry, "files": {**self.entry["files"],
                 "hermes_cli/plugins.py": {"stock": digest(STOCK), "patched": "0" * 64}}}
        with self.assertRaisesRegex(HostPatchRejected, "hermes_cli/plugins.py"):
            stage_host_files(self.source, entry, self.patches, self.destination)
        self.assertFalse(self.destination.exists())

    def test_patch_that_touches_an_unlisted_file_is_refused(self):
        files = dict(self.entry["files"])
        files.pop("scripts/run_tests.sh")
        with self.assertRaises(HostPatchRejected):
            stage_host_files(self.source, {**self.entry, "files": files}, self.patches, self.destination)
        self.assertFalse(self.destination.exists())

    def test_existing_destination_is_refused(self):
        self.destination.mkdir()
        with self.assertRaises(HostPatchRejected):
            stage_host_files(self.source, self.entry, self.patches, self.destination)


if __name__ == "__main__":
    unittest.main()
