# ABOUTME: Checks Hermes source preparation against a disposable real Git repository.
# ABOUTME: Refuses altered source and staged candidates before any host apply action.

import subprocess
import tempfile
import unittest
from pathlib import Path

from lifeos_hook_bridge.install_source import (
    IncompatibleLifeOS, prepare_hermes, validate_hermes_candidate,
)


def git(*args, cwd):
    return subprocess.run(["git", *args], cwd=cwd, check=True, text=True,
                          capture_output=True).stdout.strip()


class HermesSourceTests(unittest.TestCase):
    def fixture(self, root):
        source = root / "hermes"
        source.mkdir()
        git("init", "-q", "-b", "main", cwd=source)
        (source / "hermes_cli").mkdir()
        code = source / "hermes_cli/plugins.py"
        code.write_text("VALID_HOOKS = {'pre_tool_call'}\n")
        git("add", "hermes_cli", cwd=source)
        git("-c", "user.name=Test", "-c", "user.email=test@example.invalid",
            "commit", "-qm", "fixture", cwd=source)
        revision = git("rev-parse", "HEAD", cwd=source)
        code.write_text("VALID_HOOKS = {'pre_tool_call', 'pre_turn_stop'}\n")
        patches = root / "patches"
        patches.mkdir()
        (patches / "host.patch").write_text(git("diff", "--", "hermes_cli", cwd=source) + "\n")
        git("checkout", "--", "hermes_cli", cwd=source)
        return source, revision, patches

    def test_prepares_clean_exact_source_with_ordered_patch(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, revision, patches = self.fixture(root)
            target = root / "candidate"
            manifest = prepare_hermes(source, target, revision, patches, ("host.patch",))
            self.assertEqual(manifest["base_commit"], revision)
            self.assertEqual(manifest["patches"][0]["name"], "host.patch")
            self.assertIn("pre_turn_stop", (target / "hermes_cli/plugins.py").read_text())
            self.assertEqual(validate_hermes_candidate(target, revision, patches,
                                                       ("host.patch",))["base_commit"], revision)
            (target / "hermes_cli/plugins.py").write_text("altered\n")
            with self.assertRaisesRegex(IncompatibleLifeOS, "changed"):
                validate_hermes_candidate(target, revision, patches, ("host.patch",))

    def test_refuses_modified_or_unsupported_running_source(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, revision, patches = self.fixture(root)
            (source / "untracked.txt").write_text("local")
            with self.assertRaisesRegex(IncompatibleLifeOS, "clean"):
                prepare_hermes(source, root / "candidate", revision, patches, ("host.patch",))
            (source / "untracked.txt").unlink()
            with self.assertRaisesRegex(IncompatibleLifeOS, "tested commit"):
                prepare_hermes(source, root / "candidate", "a" * 40, patches, ("host.patch",))
            self.assertFalse((root / "candidate").exists())


if __name__ == "__main__":
    unittest.main()
