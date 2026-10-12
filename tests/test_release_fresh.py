# ABOUTME: Exercises fresh native initialization against an actual prepared LifeOS reference.
# ABOUTME: Verifies empty personal templates, selected names, and destination refusal without production data.
import json
import os
from pathlib import Path
import shutil
import tempfile
import tomllib
import unittest

from optional.lifeos_release_manager.release_stage import load_bridge
from optional.lifeos_release_manager.release_worker import _fresh_native

REFERENCE = os.environ.get('LIFEOS_MANAGED_REFERENCE')
ORIGINALS = os.environ.get('LIFEOS_MANAGED_TEMPLATE_ORIGINALS')


@unittest.skipUnless(REFERENCE and ORIGINALS, 'A prepared native reference and retained template originals are required')
class FreshReleaseTests(unittest.TestCase):
    def fixture(self, root):
        job = root / 'job'
        job.mkdir(mode=0o700)
        reference_home = job / 'reference-home'
        reference_home.mkdir(mode=0o700)
        shutil.copytree(Path(REFERENCE), reference_home / '.claude', symlinks=True)
        shutil.copytree(Path(REFERENCE).parent / '.config', reference_home / '.config', symlinks=True)
        user = reference_home / '.config/LIFEOS/USER'
        for source in Path(ORIGINALS).rglob('*'):
            if source.is_file():
                target = user / source.relative_to(ORIGINALS)
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)
        link = reference_home / '.claude/LIFEOS/USER'
        link.unlink()
        link.symlink_to(user)
        home = root / 'account'
        home.mkdir(mode=0o700)
        request = {'runtime': {'reference': str(reference_home / '.claude')},
                   'name': 'SyntheticAdrian', 'assistant': 'SyntheticCerebo'}
        selected = {'installed': home / '.claude',
                    'candidate': load_bridge(Path(__file__).resolve().parents[1] / 'lifeos_hook_bridge')}
        return job, request, selected

    def test_fresh_install_sets_native_identity_and_empties_shipped_personal_templates(self):
        with tempfile.TemporaryDirectory() as temp:
            job, request, selected = self.fixture(Path(temp))
            _fresh_native(job, request, selected)
            installed = selected['installed']
            user = installed / 'LIFEOS/USER'
            values = tomllib.loads((user / 'CONFIG/LIFEOS_CONFIG.toml').read_text())
            self.assertEqual(values['principal']['name'], 'SyntheticAdrian')
            self.assertEqual(values['da']['name'], 'SyntheticCerebo')
            self.assertIn('SyntheticAdrian', (user / 'PRINCIPAL/PRINCIPAL_IDENTITY.md').read_text())
            self.assertIn('SyntheticCerebo', (user / 'DIGITAL_ASSISTANT/DA_IDENTITY.md').read_text())
            self.assertEqual((installed / 'LIFEOS/MEMORY').resolve(), (user / 'MEMORY').resolve())
            self.assertTrue(user.resolve().is_relative_to(installed.parent / '.config'))
            self.assertFalse((user / 'WORK/SAMPLE_CONSULTING').exists())
            self.assertEqual((user / 'FINANCES/vendors.yaml').read_text(), 'vendors: []\n')
            self.assertNotIn(request['runtime']['reference'], (installed / 'settings.json').read_text())

    def test_fresh_install_preserves_an_existing_user_destination(self):
        with tempfile.TemporaryDirectory() as temp:
            job, request, selected = self.fixture(Path(temp))
            user = selected['installed'].parent / '.config/LIFEOS/USER'
            user.mkdir(parents=True)
            (user / 'keep.txt').write_text('Synthetic later data')
            with self.assertRaises(ValueError):
                _fresh_native(job, request, selected)
            self.assertEqual((user / 'keep.txt').read_text(), 'Synthetic later data')
            self.assertFalse(selected['installed'].exists())
