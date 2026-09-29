# ABOUTME: Checks LifeOS source preparation against an actual disposable Git repository.
# ABOUTME: Keeps failed or unsupported revisions out of the install candidate directory.

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from lifeos_hook_bridge.install_source import IncompatibleLifeOS, prepare_lifeos


def git(*args, cwd):
    return subprocess.run(["git", *args], cwd=cwd, check=True, text=True,
                          capture_output=True).stdout.strip()


class InstallSourceTests(unittest.TestCase):
    def fixture(self, root):
        upstream = root / "upstream"
        upstream.mkdir()
        git("init", "-q", "-b", "main", cwd=upstream)
        version = upstream / "LifeOS/install/LIFEOS/VERSION"
        version.parent.mkdir(parents=True)
        version.write_text("7.40.4\n")
        git("add", "LifeOS", cwd=upstream)
        git("-c", "user.name=Test", "-c", "user.email=test@example.invalid",
            "commit", "-qm", "fixture", cwd=upstream)
        revision = git("rev-parse", "HEAD", cwd=upstream)
        version.write_text("7.40.4-patched\n")
        patches = root / "patches"
        patches.mkdir()
        (patches / "lifeos-test.patch").write_text(git("diff", "--", "LifeOS", cwd=upstream) + "\n")
        git("checkout", "--", "LifeOS", cwd=upstream)
        return upstream, revision, patches

    def test_prepares_exact_upstream_revision_and_patch(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            upstream, revision, patches = self.fixture(root)
            target = root / "candidate"
            manifest = prepare_lifeos(str(upstream), target, revision, patches,
                                      ("lifeos-test.patch",))
            self.assertEqual((target / "LifeOS/install/LIFEOS/VERSION").read_text(), "7.40.4-patched\n")
            self.assertEqual(manifest["upstream_commit"], revision)
            self.assertEqual(manifest["patches"][0]["name"], "lifeos-test.patch")
            self.assertEqual(json.loads((target / "lifeos-source-manifest.json").read_text()), manifest)
            self.assertEqual(git("rev-parse", "HEAD", cwd=target), revision)

    def test_new_upstream_revision_is_not_silently_installed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            upstream, supported, patches = self.fixture(root)
            (upstream / "LifeOS/install/LIFEOS/VERSION").write_text("7.40.5\n")
            git("add", "LifeOS", cwd=upstream)
            git("-c", "user.name=Test", "-c", "user.email=test@example.invalid",
                "commit", "-qm", "later", cwd=upstream)
            target = root / "candidate"
            with self.assertRaises(IncompatibleLifeOS):
                prepare_lifeos(str(upstream), target, supported, patches,
                               ("lifeos-test.patch",))
            self.assertFalse(target.exists())

    def test_failed_patch_leaves_no_candidate(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            upstream, revision, patches = self.fixture(root)
            (patches / "lifeos-test.patch").write_text("invalid patch\n")
            target = root / "candidate"
            with self.assertRaises(IncompatibleLifeOS):
                prepare_lifeos(str(upstream), target, revision, patches,
                               ("lifeos-test.patch",))
            self.assertFalse(target.exists())


if __name__ == "__main__":
    unittest.main()
