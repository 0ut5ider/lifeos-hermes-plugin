# ABOUTME: Characterizes native derivative planning, status, and publication authority.
# ABOUTME: Uses actual native child writers with isolated synthetic sources.
import json
import os
from pathlib import Path
import subprocess
import unittest
from dataclasses import asdict
import shutil

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

    def test_actual_child_failure_keeps_trigger_hash_pending_for_retry(self):
        self.fixture.output.parent.mkdir(parents=True, exist_ok=True)
        foreign = self.fixture.fixture.fixture.home / 'foreign-hash-output.json'
        foreign.write_bytes(b'{"synthetic_foreign":"preserved"}\n')
        self.fixture.output.symlink_to(foreign)
        result = self.call('--force')
        self.assertEqual(result.returncode, 1)
        self.assertIn('[DerivedSync] action failed:', result.stderr)
        self.assertEqual(result.stdout, '')
        hashes = json.loads(self.state.read_text())['fileHashes']
        self.assertNotIn(str(self.fixture.identity), hashes)
        self.assertEqual(len(hashes), 2)
        self.assertIn('changed: 1', self.successful('--dry-run').stdout)
        self.assertEqual(foreign.read_bytes(), b'{"synthetic_foreign":"preserved"}\n')
        self.fixture.output.unlink()
        self.successful()
        self.assertEqual(self.successful().stdout, '')

    def test_owner_status_retains_native_counts_after_actual_publication(self):
        self.successful('--force')
        result = self.successful('--status')
        self.assertIn('watched files: 3', result.stdout)
        self.assertIn('changed=3 actions=1 dryRun=false', result.stdout)
        self.assertIn('last run:', result.stdout)

    def test_foreign_lock_destination_refuses_before_child_publication(self):
        lock = self.root / 'LIFEOS/MEMORY/STATE/derived-sync.lock'
        lock.parent.mkdir(parents=True, exist_ok=True)
        foreign = self.fixture.fixture.fixture.home / 'foreign-sync-lock'
        foreign.write_bytes(b'99999999\n2026-10-04T00:00:00Z\n')
        lock.symlink_to(foreign)
        self.assertNotEqual(self.call('--force').returncode, 0)
        self.assertEqual(foreign.read_bytes(), b'99999999\n2026-10-04T00:00:00Z\n')
        self.assertFalse(self.fixture.output.exists())
        self.assertFalse(self.state.exists())

    def test_dead_owner_lock_recovers_and_uses_private_permissions(self):
        lock = self.root / 'LIFEOS/MEMORY/STATE/derived-sync.lock'
        lock.parent.mkdir(parents=True, exist_ok=True)
        lock.write_text('99999999\n2026-10-04T00:00:00Z\n')
        lock.chmod(0o600)
        self.successful('--force')
        self.assertFalse(lock.exists())
        self.assertEqual(self.state.stat().st_mode & 0o777, 0o600)

    def test_original_native_control_matches_plan_hashes_and_child_effects(self):
        control = Path(os.environ['LIFEOS_FRESHNESS_CONTROL_SOURCE']) / 'LIFEOS/TOOLS/DerivedSync.ts'
        self.fixture.env.write_text('SYNTHETIC_KEEP=fixture\nDENYLIST_SALT=synthetic-stable-sync-salt\n')
        plan = self.successful('--dry-run').stdout
        self.successful('--force')
        state = json.loads(self.state.read_text())['fileHashes']
        payload, environment = self.fixture.output.read_bytes(), self.fixture.env.read_bytes()
        command = json.loads(self.log.read_text().splitlines()[-1])['actions'][0]['cmd']
        self.state.unlink(); self.log.unlink(); self.fixture.output.unlink()
        tools = self.root / 'LIFEOS/TOOLS'
        source = tools.resolve()
        tools.unlink(); tools.mkdir()
        for path in source.iterdir():
            if path.name != 'DerivedSync.ts':
                (tools / path.name).symlink_to(path)
        shutil.copyfile(control, tools / 'DerivedSync.ts')
        self.assertEqual(self.successful('--dry-run').stdout, plan)
        self.successful('--force')
        self.assertEqual(json.loads(self.state.read_text())['fileHashes'], state)
        self.assertEqual(self.fixture.output.read_bytes(), payload)
        self.assertEqual(self.fixture.env.read_bytes(), environment)
        self.assertEqual(json.loads(self.log.read_text().splitlines()[-1])['actions'][0]['cmd'], command)
        self.assertEqual(self.successful().stdout, '')
