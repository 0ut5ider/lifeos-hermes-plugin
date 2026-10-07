# ABOUTME: Exercises the native constitutional and state freshness migration commands.
# ABOUTME: Verifies source bytes, dry runs, owner authority, and backup destinations.
import json
import os
from pathlib import Path
import subprocess
import unittest

import test_memory_freshness as freshness_fixture


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
