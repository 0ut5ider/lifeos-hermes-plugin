# ABOUTME: Exercises staged native mounting and durable recovery on synthetic owner profiles.
# ABOUTME: Uses real Bun, Hermes validation, private journals, and actual process death.
import json
import os
from pathlib import Path
import shlex
import signal
import subprocess
import sys
import unittest

import test_memory_administration as administration
from test_memory_admin_install import HOST


class MountTransactionTests(unittest.TestCase):
    def setUp(self):
        self.fixture = administration.MemoryAdministrationTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.root, self.profile = self.fixture.root, self.fixture.profile
        self.authorization = self.fixture.issue()
        self.addCleanup(self.fixture.admin().revoke, self.fixture.configuration, self.authorization)
        self.environment = self.fixture.admin().mount_environment(self.root, self.profile, self.authorization)
        self.hermes = self.profile / 'bin/hermes'
        self.hermes.parent.mkdir()
        self.hermes.write_text('#!/bin/sh\nexec ' + shlex.quote(sys.executable) + ' ' +
            shlex.quote(str(HOST / 'hermes_cli/main.py')) + ' "$@"\n')
        self.hermes.chmod(0o755)

    def transaction(self):
        from lifeos_hook_bridge.mount_transaction import MountTransaction
        return MountTransaction(self.root, self.profile)

    def execute(self):
        return self.transaction().execute(self.environment, self.fixture.fixture.memory.bun, str(self.hermes))

    def crash_after_soul(self):
        program = self.profile / 'kill-mount.py'
        program.write_text('import os, signal, sys\nfrom pathlib import Path\n'
            'from lifeos_hook_bridge import mount_transaction as module\n'
            'root, profile, bun, hermes = sys.argv[1:]\n'
            'publish = module.publish\n'
            'def interrupted(path, data):\n'
            '    publish(path, data)\n'
            '    if path == Path(profile) / "SOUL.md": os.kill(os.getpid(), signal.SIGKILL)\n'
            'module.publish = interrupted\n'
            'module.MountTransaction(Path(root), Path(profile)).execute(dict(os.environ), bun, hermes)\n')
        result = subprocess.run([sys.executable, str(program), str(self.root), str(self.profile),
            self.fixture.fixture.memory.bun, str(self.hermes)], env={**self.environment,
                'PYTHONPATH': str(Path(__file__).parents[1]) + os.pathsep + str(HOST)},
                text=True, capture_output=True, timeout=60)
        self.assertEqual(result.returncode, -signal.SIGKILL, result.stderr)
        self.assertEqual(result.stderr, '')

    def test_native_preparation_does_not_change_live_profile_or_workspace(self):
        stage = self.profile / 'prepared-output'
        stage.mkdir(mode=0o700)
        config = (self.profile / 'config.yaml').read_bytes()
        result = subprocess.run([self.fixture.fixture.memory.bun, '--no-install',
            str(self.root / 'LIFEOS/HERMES/Mount.ts')], env={**self.environment,
                'LIFEOS_MOUNT_DESTINATION': str(stage)}, text=True, capture_output=True, timeout=45)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, '')
        self.assertEqual((self.profile / 'config.yaml').read_bytes(), config)
        self.assertFalse((self.profile / 'SOUL.md').exists())
        self.assertFalse((self.root.parent / 'HermesWorkspace').exists())
        self.assertIn('SyntheticSafetyDoctrine', (stage / 'SOUL.md').read_text())
        self.assertEqual(json.loads((stage / 'mount-plan.json').read_text())['home'], str(self.profile))

    def test_success_publishes_verified_native_files_and_commits_the_journal(self):
        result = self.execute()
        self.assertTrue(result['mounted'])
        self.assertEqual(self.transaction().status()['state'], 'committed')
        self.assertIn('SyntheticSafetyDoctrine', (self.profile / 'SOUL.md').read_text())
        self.assertEqual((self.profile / 'SOUL.md').stat().st_mode & 0o777, 0o600)
        self.assertTrue((self.profile / 'plugins/lifeos/guard.py').exists())

    def test_late_validation_failure_restores_existing_files(self):
        (self.profile / 'SOUL.md').write_text('SyntheticPreviousPrompt\n')
        original = (self.profile / 'config.yaml').read_bytes()
        self.hermes.write_text('#!/bin/sh\ncase "$HERMES_HOME" in */stage) exit 0;; *) exit 23;; esac\n')
        with self.assertRaisesRegex(RuntimeError, 'config check'):
            self.execute()
        self.assertEqual((self.profile / 'SOUL.md').read_text(), 'SyntheticPreviousPrompt\n')
        self.assertEqual((self.profile / 'config.yaml').read_bytes(), original)
        self.assertFalse((self.profile / 'plugins/lifeos').exists())
        self.assertEqual(self.transaction().status()['state'], 'rolled_back')

    def test_process_death_recovers_all_prior_mount_files(self):
        original = (self.profile / 'config.yaml').read_bytes()
        (self.profile / 'SOUL.md').write_text('SyntheticPreviousPrompt\n')
        self.crash_after_soul()
        self.assertEqual(self.transaction().status()['state'], 'applying')
        result = self.transaction().recover()
        self.assertEqual(result['state'], 'rolled_back')
        self.assertEqual((self.profile / 'config.yaml').read_bytes(), original)
        self.assertEqual((self.profile / 'SOUL.md').read_text(), 'SyntheticPreviousPrompt\n')
        self.assertFalse((self.profile / 'plugins/lifeos').exists())

    def test_recovery_preserves_a_later_user_edit_and_refuses_before_restore(self):
        self.crash_after_soul()
        (self.profile / 'config.yaml').write_text('SyntheticLaterConfiguration\n')
        current = (self.profile / 'SOUL.md').read_bytes()
        with self.assertRaisesRegex(RuntimeError, 'changed'):
            self.transaction().recover()
        self.assertEqual((self.profile / 'config.yaml').read_text(), 'SyntheticLaterConfiguration\n')
        self.assertEqual((self.profile / 'SOUL.md').read_bytes(), current)
        self.assertEqual(self.transaction().status()['state'], 'applying')

    def test_unfinished_mount_refuses_another_mount_until_recovery(self):
        self.crash_after_soul()
        with self.assertRaisesRegex(RuntimeError, '(?i)recover'):
            self.execute()

    def test_process_death_during_restoration_can_resume_original_permissions(self):
        (self.profile / 'SOUL.md').write_text('SyntheticPreviousPrompt\n')
        (self.profile / 'SOUL.md').chmod(0o644)
        self.crash_after_soul()
        program = self.profile / 'kill-recovery.py'
        program.write_text('import os, signal, sys\nfrom pathlib import Path\n'
            'from lifeos_hook_bridge import mount_transaction as module\n'
            'root, profile = map(Path, sys.argv[1:])\n'
            'publish = module.publish\n'
            'def interrupted(path, data):\n'
            '    publish(path, data)\n'
            '    if path == profile / "SOUL.md": os.kill(os.getpid(), signal.SIGKILL)\n'
            'module.publish = interrupted\n'
            'module.MountTransaction(root, profile).recover()\n')
        result = subprocess.run([sys.executable, str(program), str(self.root), str(self.profile)],
            env={**self.environment, 'PYTHONPATH': str(Path(__file__).parents[1])},
            text=True, capture_output=True, timeout=30)
        self.assertEqual(result.returncode, -signal.SIGKILL, result.stderr)
        self.assertEqual(result.stderr, '')
        self.assertEqual(self.transaction().status()['state'], 'restoring')
        self.assertEqual(self.transaction().recover()['state'], 'rolled_back')
        self.assertEqual((self.profile / 'SOUL.md').read_text(), 'SyntheticPreviousPrompt\n')
        self.assertEqual((self.profile / 'SOUL.md').stat().st_mode & 0o777, 0o644)

    def test_invalid_target_symlink_refuses_without_overwriting_it(self):
        other = self.profile / 'synthetic-other'
        other.write_text('SyntheticKeep\n')
        (self.profile / 'SOUL.md').symlink_to(other)
        with self.assertRaises(RuntimeError):
            self.execute()
        self.assertEqual(other.read_text(), 'SyntheticKeep\n')

    def test_invalid_journal_permissions_cannot_be_used_for_recovery(self):
        self.crash_after_soul()
        journal = self.profile / '.lifeos-mount/operation.json'
        value = json.loads(journal.read_text())
        value['entries'][0]['before']['mode'] = 0o4777
        journal.write_text(json.dumps(value))
        with self.assertRaisesRegex(RuntimeError, 'metadata'):
            self.transaction().recover()

    def test_success_creates_the_native_workspace(self):
        self.execute()
        self.assertTrue((self.root.parent / 'HermesWorkspace').is_dir())


if __name__ == '__main__':
    unittest.main()
