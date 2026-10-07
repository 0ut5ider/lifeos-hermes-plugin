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

    def prepare(self, config):
        (self.profile / 'config.yaml').write_text(config)
        stage = self.profile / 'prepared-output'
        stage.mkdir(mode=0o700)
        result = subprocess.run([self.fixture.fixture.memory.bun, '--no-install',
            str(self.root / 'LIFEOS/HERMES/Mount.ts')], env={**self.environment,
                'LIFEOS_MOUNT_DESTINATION': str(stage)}, text=True, capture_output=True, timeout=45)
        self.assertEqual(result.returncode, 0, result.stderr)
        check = subprocess.run([str(self.hermes), 'config', 'check'], env={**self.environment,
            'HERMES_HOME': str(stage)}, text=True, capture_output=True, timeout=120)
        self.assertEqual(check.returncode, 0, check.stdout + check.stderr)
        return (stage / 'config.yaml').read_text()

    def test_plugin_list_after_column_zero_comment_stays_one_key(self):
        # Stock Hermes writes plugins.enabled after a column-zero section banner.
        config = self.prepare('plugins:\n  clone_timeout_seconds: 300\n\n'
            '# ====\n# Model Configuration\n# ====\n  enabled:\n    - lifeos-hook-bridge\n'
            '  disabled: []\nmodel:\n  default: local\n')
        self.assertEqual(config.count('\n  enabled:'), 1, config)
        self.assertIn('  enabled:\n    - lifeos\n    - lifeos-hook-bridge\n', config)

    def test_deny_list_after_column_zero_comment_is_reconciled(self):
        config = self.prepare('approvals:\n  mode: manual\n# ====\n# Deny list\n# ====\n'
            '  deny:\n    - "synthetic-stale-glob"\nmodel:\n  default: local\n')
        self.assertEqual(config.count('\n  deny:'), 1, config)
        self.assertNotIn('synthetic-stale-glob', config)

    def test_mount_enables_batch_without_changing_the_model(self):
        from ruamel.yaml import YAML
        yaml = YAML(typ='safe')
        before = yaml.load((self.profile / 'config.yaml').read_text())
        self.execute()
        after = yaml.load((self.profile / 'config.yaml').read_text())
        self.assertEqual(after['file_tools']['patch_format'], 'v4a')
        self.assertEqual(after.get('model'), before.get('model'))

    def test_mount_preserves_an_explicit_file_tool_capability(self):
        from ruamel.yaml import YAML
        yaml = YAML(typ='safe')
        path = self.profile / 'config.yaml'
        path.write_text(path.read_text() + '\nfile_tools:\n  patch_format: replace\n')
        self.execute()
        self.assertEqual(yaml.load(path.read_text())['file_tools']['patch_format'], 'replace')

    def test_batch_capability_preserves_other_config_bytes(self):
        from lifeos_hook_bridge.mount_transaction import _enable_batch_edits
        from ruamel.yaml import YAML
        for options in ('', 'file_tools: {other: keep}\n',
                        'file_tools:\n  other: keep\n'):
            with self.subTest(options=options):
                stage = self.profile / 'capability-stage'
                stage.mkdir(exist_ok=True)
                prefix = 'model:\n  default: "local"\nplugins:\n  enabled:\n    - lifeos\n'
                suffix = 'skills:\n  external_dirs:\n    - "/synthetic/skills"\n'
                original = prefix + options + suffix
                (stage / 'config.yaml').write_text(original)
                _enable_batch_edits(stage)
                actual = (stage / 'config.yaml').read_text()
                self.assertTrue(actual.startswith(prefix), actual)
                self.assertIn(suffix, actual)
                parsed = YAML(typ='safe').load(actual)
                self.assertEqual(parsed['file_tools']['patch_format'], 'v4a')
                if options:
                    self.assertEqual(parsed['file_tools']['other'], 'keep')

    def test_finished_journal_of_another_installation_does_not_block_a_new_mount(self):
        from lifeos_hook_bridge.mount_transaction import MountError, MountTransaction
        self.execute()
        other = MountTransaction(self.root, self.profile, self.root.parent / 'other-baseline.json')
        self.assertEqual(other.status(), {'state': 'none', 'recovery_required': False})
        journal = json.loads(other.journal.read_text())
        journal['state'] = 'applying'
        other.journal.write_text(json.dumps(journal))
        with self.assertRaisesRegex(MountError, 'another installation'):
            other.status()

    def test_selected_home_keeps_the_configured_account_workspace(self):
        from lifeos_hook_bridge import lifeos_installation
        workspace = self.profile.parent / 'account-workspace'
        lifeos_installation.publish(self.profile, self.root.parent, workspace)
        self.execute()
        self.assertTrue(workspace.is_dir())
        self.assertFalse((self.root.parent / 'HermesWorkspace').exists())
        self.assertIn(str(workspace), (self.profile / '.env').read_text())

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

    def test_completed_mounts_remove_credential_bearing_snapshots(self):
        (self.profile / '.env').write_text('SYNTHETIC_PROVIDER_KEY=synthetic-mount-secret\n')
        for _ in range(2):
            result = self.execute()
            self.assertEqual(self.transaction().status()['state'], 'committed')
            self.assertFalse(Path(result['snapshot']).exists())
            self.assertEqual(list(self.transaction().state.glob('*/stage/.env')), [])
        self.assertIn('synthetic-mount-secret', (self.profile / '.env').read_text())

    def test_pending_recovery_retains_copies_until_rollback_completes(self):
        self.crash_after_soul()
        manifest = json.loads(self.transaction().journal.read_text())
        snapshot = Path(manifest['snapshot'])
        self.assertTrue((snapshot / 'previous/0').is_file())
        self.assertEqual(self.transaction().status()['state'], 'applying')
        self.assertTrue(snapshot.exists())
        self.assertEqual(self.transaction().recover()['state'], 'rolled_back')
        self.assertFalse(snapshot.exists())
        self.assertEqual(self.transaction().status()['state'], 'rolled_back')

    def test_failed_validation_removes_unneeded_credential_copies(self):
        self.hermes.write_text('#!/bin/sh\nexit 23\n')
        # Prepared configuration validation uses the real runtime and passes before this check fails.
        with self.assertRaisesRegex(RuntimeError, 'config check'):
            self.execute()
        self.assertEqual(self.transaction().status()['state'], 'rolled_back')
        self.assertEqual([path for path in self.transaction().state.iterdir() if path.is_dir()], [])

    def test_killed_preparation_cleans_owned_orphan_without_changing_live_files(self):
        original = (self.profile / 'config.yaml').read_bytes()
        program = self.profile / 'kill-preparation.py'
        program.write_text('import os, signal, sys\nfrom pathlib import Path\n'
            'from lifeos_hook_bridge import mount_transaction as module\n'
            'root, profile, bun, hermes = sys.argv[1:]\n'
            'def interrupted(*args): os.kill(os.getpid(), signal.SIGKILL)\n'
            'module._check_prepared_config = interrupted\n'
            'module.MountTransaction(Path(root), Path(profile)).execute(dict(os.environ), bun, hermes)\n')
        result = subprocess.run([sys.executable, str(program), str(self.root), str(self.profile),
            self.fixture.fixture.memory.bun, str(self.hermes)], env={**self.environment,
                'PYTHONPATH': str(Path(__file__).parents[1]) + os.pathsep + str(HOST)},
                text=True, capture_output=True, timeout=60)
        self.assertEqual(result.returncode, -signal.SIGKILL, result.stderr)
        self.assertEqual(result.stderr, '')
        self.assertTrue(list(self.transaction().state.glob('*/stage/.env')))
        self.assertEqual(self.transaction().status()['state'], 'none')
        self.assertEqual([path for path in self.transaction().state.iterdir() if path.is_dir()], [])
        self.assertEqual((self.profile / 'config.yaml').read_bytes(), original)

    def test_snapshot_cleanup_preserves_unrecognized_directories_and_link_targets(self):
        self.transaction().state.mkdir(mode=0o700)
        unknown = self.transaction().state / ('b' * 32)
        unknown.mkdir(mode=0o700)
        (unknown / 'keep.txt').write_text('Synthetic unrelated data')
        outside = self.profile / 'synthetic-outside'
        outside.mkdir()
        (outside / 'keep.txt').write_text('Synthetic link target')
        (self.transaction().state / ('c' * 32)).symlink_to(outside)
        self.execute()
        self.assertEqual((unknown / 'keep.txt').read_text(), 'Synthetic unrelated data')
        self.assertEqual((outside / 'keep.txt').read_text(), 'Synthetic link target')


if __name__ == '__main__':
    unittest.main()
