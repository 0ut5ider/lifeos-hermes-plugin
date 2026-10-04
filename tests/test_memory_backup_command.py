# ABOUTME: Exercises native backups through the actual Hermes command parser and plugin discovery.
# ABOUTME: Verifies selected-profile isolation and safe refusal without exposing source contents.
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

import test_memory_host as host_fixture
import test_memory_model_calls as model_fixture


class MemoryBackupCommandTests(unittest.TestCase):
    def setUp(self):
        self.fixture = host_fixture.MemoryHostTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.native = self.fixture.fixture.fixture.fixture
        self.native.remember('Synthetic private command backup marker', 'command-backup')
        (self.fixture.home / 'config.yaml').write_text(json.dumps({
            **self.fixture.fixture.host_config, 'plugins': {'enabled': ['lifeos-hook-bridge']},
            'memory': {'memory_enabled': False, 'user_profile_enabled': False}}))
        self.destination = self.native.home / 'backups/command-one'

    def run_command(self, *arguments, profile=None):
        environment = {key: os.environ[key] for key in ('PATH', 'LANG', 'TZ') if key in os.environ}
        environment.update(HOME=str(self.native.home), HERMES_HOME=str(profile or self.fixture.home),
                           PYTHONPATH=str(model_fixture.HOST), LIFEOS_HOOK_SETTINGS=str(self.native.root / 'settings.json'),
                           BUN_CONFIG_NO_AUTO_INSTALL='1')
        return subprocess.run([sys.executable, '-m', 'hermes_cli.main', 'lifeos-backup', *map(str, arguments)],
                              env=environment, capture_output=True, text=True, timeout=30)

    def test_command_creates_and_verifies_the_selected_native_store(self):
        result = self.run_command('--create', self.destination)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(result.stderr, '')
        receipt = json.loads(result.stdout)
        self.assertEqual(receipt['status'], 'committed')
        self.assertNotIn('Synthetic private command backup marker', result.stdout)
        checked = self.run_command('--inspect', self.destination, '--signature', receipt['signature'])
        self.assertEqual(checked.returncode, 0, checked.stdout + checked.stderr)
        self.assertEqual(checked.stderr, '')
        self.assertEqual(json.loads(checked.stdout)['status'], 'verified')
        self.assertNotIn('Synthetic private command backup marker', checked.stdout)
        for name, data in self.fixture.original.items():
            self.assertEqual((self.fixture.home / 'memories' / name).read_bytes(), data)
        self.assertEqual(self.fixture.fixture.received, [])

    def test_command_refuses_an_existing_destination_without_replacing_it(self):
        self.destination.mkdir(parents=True)
        marker = self.destination / 'synthetic-existing'
        marker.write_text('Preserve this synthetic prior backup.\n')
        result = self.run_command('--create', self.destination)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(json.loads(result.stderr)['status'], 'rejected')
        self.assertEqual(result.stdout, '')
        self.assertEqual(marker.read_text(), 'Preserve this synthetic prior backup.\n')

    def test_command_recovers_a_native_backup_into_a_separate_tree_without_ownership(self):
        from lifeos_hook_bridge.memory_access import NativeMemory
        from test_memory_native import OWNER
        created = self.run_command('--create', self.destination)
        self.assertEqual(created.returncode, 0, created.stdout + created.stderr)
        signature = json.loads(created.stdout)['signature']
        target = self.native.home / 'recovery/command-one'
        result = self.run_command('--recover', self.destination, '--destination', target, '--signature', signature)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(result.stderr, '')
        receipt = json.loads(result.stdout)
        self.assertEqual(receipt['status'], 'recovered')
        self.assertFalse(receipt['ownership_enabled'])
        recovered = NativeMemory(Path(receipt['root']))
        facts = recovered.recall(OWNER, 'private command backup marker')
        self.assertEqual([fact['content'] for fact in facts], ['Synthetic private command backup marker'])
        self.assertNotIn('Synthetic private command backup marker', result.stdout)
        for name, data in self.fixture.original.items():
            self.assertEqual((self.fixture.home / 'memories' / name).read_bytes(), data)
        self.assertEqual(self.fixture.fixture.received, [])

    def test_command_requires_the_reviewed_signature_and_a_separate_recovery_destination(self):
        created = self.run_command('--create', self.destination)
        self.assertEqual(created.returncode, 0, created.stdout + created.stderr)
        result = self.run_command('--recover', self.destination)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, '')
        self.assertEqual(json.loads(result.stderr)['status'], 'rejected')

    def test_selected_profile_cannot_verify_another_profiles_native_backup(self):
        created = self.run_command('--create', self.destination)
        self.assertEqual(created.returncode, 0, created.stdout + created.stderr)
        other = host_fixture.MemoryHostTests()
        other.setUp()
        self.addCleanup(other.doCleanups)
        (other.home / 'config.yaml').write_text(json.dumps({
            **other.fixture.host_config, 'plugins': {'enabled': ['lifeos-hook-bridge']},
            'memory': {'memory_enabled': False, 'user_profile_enabled': False}}))
        result = self.run_command('--inspect', self.destination, profile=other.home)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(json.loads(result.stderr)['status'], 'rejected')
        self.assertEqual(result.stdout, '')
        self.assertNotIn('Synthetic private command backup marker', result.stderr)
