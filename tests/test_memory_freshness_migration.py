# ABOUTME: Exercises the native constitutional and state freshness migration commands.
# ABOUTME: Verifies source bytes, dry runs, owner authority, and backup destinations.
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

import test_memory_freshness as freshness_fixture
from test_memory_native import OWNER


class MemoryFreshnessMigrationTests(unittest.TestCase):
    def setUp(self):
        self.fixture = freshness_fixture.MemoryFreshnessTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.root = self.fixture.root
        self.targets = [self.root / relative for relative in (
            'LIFEOS/USER/DIGITAL_ASSISTANT/DA_IDENTITY.md',
            'LIFEOS/USER/PRINCIPAL/PRINCIPAL_IDENTITY.md', 'LIFEOS/USER/PROJECTS.md',
            'LIFEOS/LIFEOS_SYSTEM_PROMPT.md', 'LIFEOS/USER/TELOS/PRINCIPAL_TELOS.md',
            'LIFEOS/DOCUMENTATION/ARCHITECTURE_SUMMARY.md',
            'LIFEOS/DOCUMENTATION/LifeosSystemArchitecture.md')]
        for path in self.targets:
            path.write_text('# Synthetic migration body for ' + path.name + '\n')

    def call(self, *args, context=True):
        return subprocess.run(['bun', '--no-install', str(self.root / 'LIFEOS/TOOLS/MigrateContextFreshness.ts'), *args],
            env=self.fixture.environment(context=context), capture_output=True, text=True, timeout=30)

    def snapshot(self):
        return {str(path): path.read_bytes() for path in self.targets}

    def test_owner_migration_preserves_body_and_native_backup_bytes(self):
        before = self.snapshot()
        result = self.call()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, '')
        self.assertIn('sha256 match:', result.stdout)
        for path in self.targets:
            with self.subTest(path=path.name):
                self.assertIn('convention: pai-freshness-v1', path.read_text())
                self.assertTrue(path.read_bytes().endswith(before[str(path)]))
                backup = path.parent / 'Backups' / (path.stem + '-2026-05-03-23-00-00.md')
                self.assertEqual(backup.read_bytes(), before[str(path)])

    def test_owner_dry_run_preserves_sources_and_creates_no_backups(self):
        before = self.snapshot()
        result = self.call('--dry-run')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('Synthetic migration body', result.stdout)
        self.assertIn('(dry-run - no files written)', result.stdout)
        self.assertEqual(self.snapshot(), before)
        self.assertFalse(any((path.parent / 'Backups').exists() for path in self.targets))

    def test_owner_read_without_write_refuses_migration(self):
        before = self.snapshot()
        self.fixture.fixture.configuration.update(lambda c: c['destinations']['chat-a:200'].update(write=[]))
        self.assertNotEqual(self.call().returncode, 0)
        self.assertEqual(self.snapshot(), before)
        self.assertFalse(any((path.parent / 'Backups').exists() for path in self.targets))

    def test_missing_context_refuses_migration_and_dry_run_disclosure(self):
        before = self.snapshot()
        for args in ([], ['--dry-run']):
            with self.subTest(args=args):
                result = self.call(*args, context=False)
                self.assertNotEqual(result.returncode, 0)
                self.assertNotIn('Synthetic migration body', result.stdout)
                self.assertEqual(self.snapshot(), before)

    def test_read_only_owner_can_preview_without_publication(self):
        self.fixture.fixture.configuration.update(lambda c: c['destinations']['chat-a:200'].update(write=[]))
        before = self.snapshot()
        result = self.call('--dry-run')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('Synthetic migration body', result.stdout)
        self.assertEqual(self.snapshot(), before)

    def test_revocation_preserves_sources_and_backup_absence(self):
        before = self.snapshot()
        self.fixture.fixture.configuration.update(lambda c: c['accounts'].pop('chat-a:100'))
        self.assertNotEqual(self.call().returncode, 0)
        self.assertEqual(self.snapshot(), before)
        self.assertFalse(any((path.parent / 'Backups').exists() for path in self.targets))

    def test_state_stamp_requires_write_authority(self):
        paths = list((self.root / 'LIFEOS/USER/TELOS').glob('*_STATE/*.md'))
        self.assertEqual(len(paths), 2)
        before = {str(path): path.read_bytes() for path in paths}
        self.fixture.fixture.configuration.update(lambda c: c['destinations']['chat-a:200'].update(write=[]))
        self.assertNotEqual(self.call('--state').returncode, 0)
        self.assertEqual({str(path): path.read_bytes() for path in paths}, before)

    def test_private_permissions_cover_sources_and_original_byte_backups(self):
        result = self.call()
        self.assertEqual(result.returncode, 0, result.stderr)
        for path in self.targets:
            with self.subTest(path=path.name):
                self.assertEqual(path.stat().st_mode & 0o777, 0o600)
                backup = path.parent / 'Backups' / (path.stem + '-2026-05-03-23-00-00.md')
                self.assertEqual(backup.stat().st_mode & 0o777, 0o600)

    def test_foreign_backup_directory_refuses_before_source_publication(self):
        target = self.targets[0]
        foreign = self.fixture.fixture.fixture.home / 'foreign-migration-backups'
        foreign.mkdir()
        (target.parent / 'Backups').symlink_to(foreign)
        before = self.snapshot()
        self.assertNotEqual(self.call().returncode, 0)
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(list(foreign.iterdir()), [])

    def test_managed_and_standalone_console_and_source_bytes_match(self):
        before = self.snapshot()
        managed = self.call()
        self.assertEqual(managed.returncode, 0, managed.stderr)
        written = self.snapshot()
        connector = self.root / 'LIFEOS/USER/CONFIG/memory-access.json'
        settings = connector.read_bytes()
        connector.unlink()
        try:
            for name, data in before.items():
                Path(name).write_bytes(data)
            native = self.call(context=False)
            self.assertEqual(native.returncode, 0, native.stderr)
            self.assertEqual((managed.stdout, managed.stderr), (native.stdout, native.stderr))
            self.assertEqual(self.snapshot(), written)
        finally:
            connector.write_bytes(settings); connector.chmod(0o600)

    def process(self, mode, relative=None):
        result = subprocess.run([sys.executable, str(Path(__file__).with_name('memory_freshness_migration_process.py')),
            str(self.fixture.fixture.configuration.path), mode, *([relative] if relative else [])], env=self.fixture.environment(),
            capture_output=True, text=True, timeout=30)
        self.assertEqual(result.stderr, '')
        return result

    def test_source_change_preserves_later_edit_and_creates_no_backup(self):
        before = self.snapshot()
        result = self.process('source')
        self.assertEqual(result.returncode, 0)
        self.assertFalse(json.loads(result.stdout)['ok'])
        expected = dict(before)
        expected[str(self.targets[0])] += b'\nSynthetic later migration edit\n'
        self.assertEqual(self.snapshot(), expected)
        with self.fixture.memory._transaction():
            self.assertEqual(self.snapshot(), expected)
        self.assertFalse(any((path.parent / 'Backups').exists() for path in self.targets))

    def test_owner_change_after_render_preserves_sources_and_backup_absence(self):
        before = self.snapshot()
        result = self.process('authority')
        self.assertEqual(result.returncode, 0)
        self.assertFalse(json.loads(result.stdout)['ok'])
        with self.fixture.memory._transaction():
            self.assertEqual(self.snapshot(), before)
        self.assertFalse(any((path.parent / 'Backups').exists() for path in self.targets))

    def test_process_death_recovers_source_and_existing_backup_bytes(self):
        target = self.targets[0]
        backup = target.parent / 'Backups' / (target.stem + '-2026-05-03-23-00-00.md')
        backup.parent.mkdir()
        backup.write_text('Synthetic preserved earlier backup\n')
        prior_backup = backup.read_bytes()
        before = self.snapshot()
        result = self.process('interrupt')
        self.assertEqual(result.returncode, 73)
        self.assertNotEqual(target.read_bytes(), before[str(target)])
        self.assertEqual(backup.read_bytes(), before[str(target)])
        self.assertTrue(self.fixture.memory.transaction.journal.exists())
        with self.fixture.memory._transaction():
            self.assertEqual(self.snapshot(), before)
            self.assertEqual(backup.read_bytes(), prior_backup)
        self.assertFalse(self.fixture.memory.transaction.journal.exists())
        self.assertEqual(self.call().returncode, 0)

    def test_interrupted_system_publications_recover_all_sources_and_backups(self):
        before = self.snapshot()
        for relative in ('LIFEOS/LIFEOS_SYSTEM_PROMPT.md', 'LIFEOS/DOCUMENTATION/ARCHITECTURE_SUMMARY.md',
                         'LIFEOS/DOCUMENTATION/LifeosSystemArchitecture.md'):
            with self.subTest(relative=relative):
                result = self.process('interrupt', relative)
                self.assertEqual(result.returncode, 73)
                self.assertNotEqual((self.root / relative).read_bytes(), before[str(self.root / relative)])
                with self.fixture.memory._transaction():
                    self.assertEqual(self.snapshot(), before)
                    for path in self.targets:
                        backup = path.parent / 'Backups' / (path.stem + '-2026-05-03-23-00-00.md')
                        self.assertFalse(backup.exists())

    def test_retired_source_blocks_apply_without_partial_publication(self):
        memory = self.fixture.memory
        saved = memory.remember(OWNER, category='principal', content='RULE: Synthetic retired migration body',
            title='', project='', request_id='migration-retired')
        target = self.targets[0]
        target.write_text(target.read_text() + '\nSynthetic retired migration body\n')
        memory.forget(OWNER, saved['reference'], 'migration-forget')
        before = self.snapshot()
        result = self.call()
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn('WROTE:', result.stdout)
        self.assertNotIn('Synthetic retired migration body', result.stdout)
        with memory._transaction():
            self.assertEqual(self.snapshot(), before)
        self.assertFalse(any((path.parent / 'Backups').exists() for path in self.targets))

    def test_exact_review_allows_safe_older_context_migration(self):
        from lifeos_hook_bridge.memory_source_review import preview, approve
        memory = self.fixture.memory
        saved = memory.remember(OWNER, category='principal', content='RULE: Synthetic unrelated migration retirement',
            title='', project='', request_id='migration-older')
        memory.forget(OWNER, saved['reference'], 'migration-older-forget')
        paths = [str(path.relative_to(self.root)) for path in self.targets]
        plan = preview(memory, OWNER, paths)
        self.assertTrue(all(item['accepted'] for item in plan['sources']))
        self.assertEqual(approve(memory, OWNER, paths, plan['signature'])['status'], 'committed')
        self.assertEqual(self.call().returncode, 0)

    def test_backup_registry_alias_refuses_before_journal_collection(self):
        saved = self.fixture.fixture.fixture.remember('Synthetic migration registry guard', 'migration-alias')
        target = self.root / 'LIFEOS/DOCUMENTATION/ARCHITECTURE_SUMMARY.md'
        backup = target.parent / 'Backups' / (target.stem + '-2026-05-03-23-00-00.md')
        backup.parent.mkdir()
        os.link(self.fixture.memory.database, backup)
        before = self.snapshot()
        self.assertNotEqual(self.call().returncode, 0)
        self.assertTrue(backup.samefile(self.fixture.memory.database))
        self.assertEqual(self.snapshot(), before)
        self.assertFalse(self.fixture.memory.transaction.journal.exists())
        self.assertEqual(self.fixture.memory.get(OWNER, saved['reference'])['content'], 'Synthetic migration registry guard')

    def test_context_migration_does_not_read_the_excluded_telos_target(self):
        (self.root / 'LIFEOS/USER/TELOS/TELOS.md').write_text('<private>Synthetic unrelated private TELOS</private>')
        result = self.call()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn('Synthetic unrelated private TELOS', result.stdout)

    def test_state_membership_preserves_body_review_and_write_clocks(self):
        path = self.root / 'LIFEOS/USER/TELOS/CURRENT_STATE/SYNTHETIC_CUSTOM.md'
        before = path.read_text()
        result = self.call('--state')
        self.assertEqual(result.returncode, 0, result.stderr)
        after = path.read_text()
        self.assertIn('convention: pai-freshness-v1', after)
        self.assertIn('last_updated_by: migration', after)
        self.assertIn('last_updated: 2026-10-02', after)
        self.assertIn('last_reviewed: 2026-10-01', after)
        self.assertEqual(before.split('\n---\n', 1)[1], after.split('\n---\n', 1)[1])

    def test_foreign_system_backup_directory_refuses_without_changes(self):
        target = self.root / 'LIFEOS/LIFEOS_SYSTEM_PROMPT.md'
        foreign = self.fixture.fixture.fixture.home / 'foreign-system-migration-backups'
        foreign.mkdir()
        (target.parent / 'Backups').symlink_to(foreign)
        before = self.snapshot()
        self.assertNotEqual(self.call().returncode, 0)
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(list(foreign.iterdir()), [])

    def test_all_supported_large_sources_keep_complete_bodies_and_backups(self):
        for character in ('x', 'é'):
            with self.subTest(character=character):
                for path in self.targets:
                    prefix = '# Synthetic large migration body\n'
                    path.write_text(prefix + character * ((240 * 1024 - len(prefix)) // len(character.encode())) + '\n')
                before = self.snapshot()
                result = self.call()
                self.assertEqual(result.returncode, 0, result.stderr)
                for path in self.targets:
                    with self.subTest(path=path.name):
                        self.assertTrue(path.read_bytes().endswith(before[str(path)]))
                        backup = path.parent / 'Backups' / (path.stem + '-2026-05-03-23-00-00.md')
                        self.assertEqual(backup.read_bytes(), before[str(path)])

    def test_invalid_service_options_refuse_before_source_or_backup_changes(self):
        from lifeos_hook_bridge.memory_service import MemoryService
        service = MemoryService(self.fixture.fixture.configuration)
        before = self.snapshot()
        for arguments in ({'dry_run': 'false', 'state': False}, {'dry_run': True, 'state': []},
                          {'dry_run': 0, 'state': False},
                          {'dry_run': False, 'state': False, 'paths': ['../outside']}):
            with self.subTest(arguments=arguments):
                self.assertFalse(service.native(self.fixture.fixture.context,
                    'freshness_migration', arguments)['ok'])
                self.assertEqual(self.snapshot(), before)
                self.assertFalse(any((path.parent / 'Backups').exists() for path in self.targets))

    def test_missing_connector_durable_marker_refuses_without_migration(self):
        before = self.snapshot()
        (self.root / 'LIFEOS/USER/CONFIG/memory-http.json').write_text('{"version":1,"managed":true}')
        (self.root / 'LIFEOS/USER/CONFIG/memory-access.json').unlink()
        self.assertNotEqual(self.call(context=False).returncode, 0)
        self.assertEqual(self.snapshot(), before)
        self.assertFalse(any((path.parent / 'Backups').exists() for path in self.targets))
