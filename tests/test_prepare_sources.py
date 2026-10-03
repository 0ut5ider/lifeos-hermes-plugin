# ABOUTME: Exercises repeatable preparation of patched Hermes and LifeOS source trees.
# ABOUTME: Checks that incompatible inputs do not leave an installable output.

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from lifeos_hook_bridge.install_source import HERMES_PATCHES, LIFEOS_PATCHES


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/prepare_sources.py"
HERMES_REPO = os.environ.get("LIFEOS_PREPARE_HERMES_REPO")
LIFEOS_REPO = os.environ.get("LIFEOS_PREPARE_LIFEOS_REPO")


class PrepareSourcesTests(unittest.TestCase):
    def test_source_branch_name_does_not_prevent_a_fresh_preparation(self):
        from scripts.prepare_sources import SOURCES, prepare_source
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'source'
            subprocess.run(['git', 'init', '-q', '-b', 'feature/lifeos-hook-parity', str(source)], check=True)
            (source / 'synthetic.txt').write_text('Synthetic upstream base')
            subprocess.run(['git', '-C', str(source), 'add', 'synthetic.txt'], check=True)
            subprocess.run(['git', '-C', str(source), '-c', 'user.name=Synthetic',
                            '-c', 'user.email=synthetic@example.invalid', 'commit', '-qm', 'Synthetic base'], check=True)
            base = subprocess.check_output(['git', '-C', str(source), 'rev-parse', 'HEAD'], text=True).strip()
            with patch.dict(SOURCES, {'hermes': {'base': base, 'patches': ()}}):
                result = prepare_source('hermes', source, root / 'prepared')
            self.assertEqual(result, {'base': base, 'patches': []})
            self.assertEqual((root / 'prepared/synthetic.txt').read_text(), 'Synthetic upstream base')
            self.assertEqual(subprocess.check_output(['git', '-C', str(source), 'rev-parse', 'HEAD'],
                                                     text=True).strip(), base)

    def run_prepare(self, hermes: str, lifeos: str, output: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT), "--hermes-repo", hermes,
             "--lifeos-repo", lifeos, "--output", str(output)],
            cwd=ROOT, text=True, capture_output=True,
        )

    def test_incompatible_input_leaves_no_output(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "prepared"
            result = self.run_prepare(str(ROOT), str(ROOT), output)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("required base revision", result.stderr)
            self.assertFalse(output.exists())

    def test_existing_symlink_is_not_replaced(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "prepared"
            output.symlink_to(Path(directory) / "absent")
            result = self.run_prepare(str(ROOT), str(ROOT), output)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("output already exists", result.stderr)
            self.assertTrue(output.is_symlink())

    @unittest.skipUnless(HERMES_REPO and LIFEOS_REPO, "real Hermes and LifeOS source repositories are required")
    def test_real_sources_receive_every_patch_in_order(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "prepared"
            result = self.run_prepare(HERMES_REPO, LIFEOS_REPO, output)
            self.assertEqual(result.returncode, 0, result.stderr)
            manifest = json.loads((output / "source-manifest.json").read_text())
            self.assertEqual(tuple(p["name"] for p in manifest["hermes"]["patches"]), HERMES_PATCHES)
            self.assertEqual(tuple(p["name"] for p in manifest["lifeos"]["patches"]), LIFEOS_PATCHES)
            self.assertTrue((output / "hermes/hermes_cli/plugins.py").is_file())
            self.assertTrue((output / "lifeos/LifeOS/install/LIFEOS/TOOLS/IntegrityCheck.ts").is_file())
            runtime_check = subprocess.run(
                [sys.executable, "-c", "from pm.runtime import _resident_runtime; assert _resident_runtime() is None"],
                cwd=output / "hermes", env={**os.environ, "PYTHONPATH": str(output / "hermes")},
                text=True, capture_output=True,
            )
            self.assertEqual(runtime_check.returncode, 0, runtime_check.stderr)
            for checkout in ("hermes", "lifeos"):
                check = subprocess.run(
                    ["git", "-C", str(output / checkout), "diff", "--check"],
                    text=True, capture_output=True,
                )
                self.assertEqual(check.returncode, 0, check.stderr)


if __name__ == "__main__":
    unittest.main()
