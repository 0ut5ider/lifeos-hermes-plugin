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
    def test_changed_user_seed_refuses_before_user_publication(self):
        from optional.lifeos_release_manager.release_initialization import NativeInitialization
        with tempfile.TemporaryDirectory() as temp:
            job, request, selected = self.fixture(Path(temp))
            initialization = NativeInitialization(job, request, selected['installed'])
            initialization.prepare(selected['candidate'].memory_module('fresh_store'))
            (initialization.seed / 'user/unreviewed.txt').write_text('Synthetic changed seed')
            with self.assertRaisesRegex(ValueError, 'prepared user'):
                _fresh_native(job, request, selected)
            self.assertFalse(initialization.user.exists())
            self.assertFalse(selected['installed'].exists())

    def fixture(self, root):
        job = root / 'job'
        job.mkdir(mode=0o700)
        reference_home = job / 'reference-home'
        reference_home.mkdir(mode=0o700)
        shutil.copytree(Path(REFERENCE), reference_home / '.claude', symlinks=True,
                        ignore=shutil.ignore_patterns('node_modules'))
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

    def test_fresh_native_resumes_after_process_exit_without_replacing_later_user_data(self):
        with tempfile.TemporaryDirectory() as temp:
            job, request, selected = self.fixture(Path(temp))
            child = os.fork()
            if child == 0:
                def terminate(point):
                    if point == 'user-published':
                        os._exit(73)
                _fresh_native(job, request, selected, checkpoint=terminate)
                os._exit(74)
            _, result = os.waitpid(child, 0)
            self.assertEqual(os.waitstatus_to_exitcode(result), 73)
            user = selected['installed'].parent / '.config/LIFEOS/USER'
            personal = user / 'later-synthetic-data.txt'
            personal.write_text('Synthetic data added after interruption')
            _fresh_native(job, request, selected)
            self.assertEqual(personal.read_text(), 'Synthetic data added after interruption')
            self.assertTrue(selected['installed'].is_dir())
            self.assertEqual((selected['installed'] / 'LIFEOS/MEMORY').resolve(), user / 'MEMORY')

    def test_fresh_native_recovers_publication_intents_and_rejects_later_program_edits(self):
        for phase in ('seed-prepared', 'user-publication-intent', 'native-publication-intent', 'native-published'):
            with self.subTest(phase=phase), tempfile.TemporaryDirectory() as temp:
                job, request, selected = self.fixture(Path(temp))
                child = os.fork()
                if child == 0:
                    _fresh_native(job, request, selected,
                        checkpoint=lambda point: os._exit(73) if point == phase else None)
                    os._exit(74)
                _, result = os.waitpid(child, 0)
                self.assertEqual(os.waitstatus_to_exitcode(result), 73)
                _fresh_native(job, request, selected)
                program = selected['installed'] / 'settings.json'
                program.write_text('{"synthetic_later_edit":true}')
                with self.assertRaisesRegex(ValueError, 'later program edit'):
                    _fresh_native(job, request, selected)
                self.assertEqual(program.read_text(), '{"synthetic_later_edit":true}')
