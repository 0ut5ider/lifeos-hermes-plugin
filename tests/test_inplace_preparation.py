# ABOUTME: Checks the in-place preparation helpers that choose host files and build the preview tree.
# ABOUTME: Uses disposable real Git checkouts; the owner's checkout must remain unchanged.
from pathlib import Path
import subprocess
import tempfile
import unittest

from optional.lifeos_release_manager.inplace_preparation import build_preview, desired_host_files


def git(*args, cwd):
    return subprocess.run(['git', *args], cwd=cwd, check=True, text=True, capture_output=True).stdout.strip()


class DesiredHostFilesTests(unittest.TestCase):
    def test_new_entry_targets_receive_their_patched_files(self):
        staged = {'a.py': {'stock': Path('/s/a.py'), 'patched': Path('/p/a.py')}}
        self.assertEqual(desired_host_files({}, staged), {'a.py': Path('/p/a.py')})

    def test_targets_only_the_recorded_release_changed_return_to_their_originals(self):
        staged = {'a.py': {'stock': Path('/s/a.py'), 'patched': Path('/p/a.py')}}
        record = {'files': {'a.py': {'stock': 'x', 'patched': 'y'}, 'b.py': {'stock': 'x', 'patched': 'y'},
                            'added.py': {'stock': None, 'patched': 'y'}}}
        self.assertEqual(desired_host_files({}, staged, record, {'a.py': Path('/o/a.py'), 'b.py': Path('/o/b.py')}),
                         {'a.py': Path('/p/a.py'), 'b.py': Path('/o/b.py'), 'added.py': None})


class PreviewTests(unittest.TestCase):
    def test_preview_copies_tracked_files_and_overlays_the_desired_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'hermes-agent'
            (source / 'hermes_cli').mkdir(parents=True)
            git('init', '-q', cwd=source)
            (source / 'hermes_cli/plugins.py').write_text('stock\n')
            (source / 'run.sh').write_text('#!/bin/sh\n')
            (source / 'run.sh').chmod(0o755)
            (source / 'removed.py').write_text('added by the last release\n')
            (source / '.gitignore').write_text('venv/\n')
            git('add', '.', cwd=source)
            git('-c', 'user.name=T', '-c', 'user.email=t@example.invalid', 'commit', '-qm', 'base', cwd=source)
            (source / 'venv').mkdir()
            (source / 'venv/ignored').write_text('not copied\n')
            patched = root / 'patched.py'
            patched.write_text('patched\n')
            added = root / 'new_hook.py'
            added.write_text('added\n')
            (root / 'job').mkdir()
            preview = build_preview(source, {'hermes_cli/plugins.py': patched, 'hermes_cli/new_hook.py': added,
                                             'removed.py': None}, root / 'job/hermes-preview')
            self.assertEqual((preview / 'hermes_cli/plugins.py').read_text(), 'patched\n')
            self.assertEqual((preview / 'hermes_cli/new_hook.py').read_text(), 'added\n')
            self.assertFalse((preview / 'removed.py').exists())
            self.assertFalse((preview / 'venv').exists())
            self.assertTrue((preview / 'run.sh').stat().st_mode & 0o100)
            self.assertEqual((source / 'hermes_cli/plugins.py').read_text(), 'stock\n')
            self.assertEqual(git('status', '--porcelain', cwd=source), '')


if __name__ == '__main__':
    unittest.main()
