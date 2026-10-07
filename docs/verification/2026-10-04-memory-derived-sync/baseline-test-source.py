# ABOUTME: Characterizes native derivative planning, status, and publication authority.
# ABOUTME: Uses actual native child writers with isolated synthetic sources.
import json
import os
from pathlib import Path
import subprocess
import unittest
from dataclasses import asdict

import test_memory_deny_hashes as hash_fixture


class MemoryDerivedSyncTests(unittest.TestCase):
    def setUp(self):
        self.fixture = hash_fixture.MemoryDenyHashesTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.root = self.fixture.root
        self.state = self.root / 'LIFEOS/MEMORY/STATE/derived-sync.json'
        self.log = self.root / 'LIFEOS/MEMORY/OBSERVABILITY/derived-sync.jsonl'

    def call(self, *args, context=True):
        environment = dict(os.environ, HOME=str(self.fixture.fixture.fixture.home), BUN_CONFIG_NO_AUTO_INSTALL='1')
        environment.pop('LIFEOS_MEMORY_INTERNAL', None)
        environment.pop('LIFEOS_MEMORY_CONTEXT', None)
        if context:
            environment['LIFEOS_MEMORY_CONTEXT'] = json.dumps(asdict(self.fixture.fixture.context))
        return subprocess.run(['bun', '--no-install', str(self.root / 'LIFEOS/TOOLS/DerivedSync.ts'), *args],
            env=environment, capture_output=True, text=True, timeout=90)

    def successful(self, *args):
        result = self.call(*args)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, '')
        return result

    def test_owner_dry_plan_keeps_native_actions_without_publishing_state(self):
        result = self.successful('--dry-run')
        self.assertIn('changed: 3', result.stdout)
        self.assertIn('DeriveDenyHashes.ts', result.stdout)
        self.assertFalse(self.state.exists())
        self.assertFalse(self.log.exists())

    def test_missing_context_cannot_plan_or_read_status(self):
        for arguments in (['--dry-run'], ['--status']):
            with self.subTest(arguments=arguments):
                result = self.call(*arguments, context=False)
                self.assertNotEqual(result.returncode, 0)
                self.assertNotIn('watched files:', result.stdout)
                self.assertNotIn('planned actions:', result.stdout)

    def test_private_identity_is_not_a_planning_source(self):
        self.fixture.identity.write_text('# Synthetic principal\n<private>FixtureSurname FixtureGivenname</private>\n')
        result = self.successful('--dry-run')
        self.assertIn('changed: 2', result.stdout)
        self.assertNotIn(str(self.fixture.identity), result.stdout)

    def test_foreign_identity_source_refuses_planning(self):
        foreign = self.fixture.fixture.fixture.home / 'foreign-sync-identity.md'
        foreign.write_text('ForeignFixtureName ForeignFixtureSurname\n')
        self.fixture.identity.unlink(); self.fixture.identity.symlink_to(foreign)
        self.assertNotEqual(self.call('--dry-run').returncode, 0)

    def test_read_only_owner_cannot_publish_sync_state_or_log(self):
        self.fixture.fixture.configuration.update(lambda value: value['destinations']['chat-a:200'].update(write=[]))
        self.call('--force')
        self.assertFalse(self.state.exists())
        self.assertFalse(self.log.exists())
        self.assertFalse(self.fixture.output.exists())
        self.assertEqual(self.fixture.env.read_text(), 'SYNTHETIC_KEEP=fixture\n')

    def test_owner_sync_state_and_log_have_private_permissions(self):
        self.successful('--force')
        self.assertEqual(self.state.stat().st_mode & 0o777, 0o600)
        self.assertEqual(self.log.stat().st_mode & 0o777, 0o600)
        self.assertIn('fileHashes', json.loads(self.state.read_text()))
        self.assertTrue(self.fixture.output.exists())
        self.assertEqual(self.successful().stdout, '')

    def test_foreign_state_destination_refuses_before_child_publication(self):
        self.state.parent.mkdir(parents=True, exist_ok=True)
        foreign = self.fixture.fixture.fixture.home / 'foreign-sync-state.json'
        before = b'{"fileHashes":{},"lastRun":"2026-10-04T00:00:00Z"}\n'
        foreign.write_bytes(before)
        self.state.symlink_to(foreign)
        self.assertNotEqual(self.call('--force').returncode, 0)
        self.assertEqual(foreign.read_bytes(), before)
        self.assertFalse(self.fixture.output.exists())
        self.assertEqual(self.fixture.env.read_text(), 'SYNTHETIC_KEEP=fixture\n')
