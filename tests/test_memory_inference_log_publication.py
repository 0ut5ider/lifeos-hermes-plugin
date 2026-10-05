# ABOUTME: Verifies current authority, bounded metadata, and interrupted inference-log recovery.
# ABOUTME: Uses the actual memory service, native validation, and real publisher processes.
import json
from pathlib import Path
import subprocess
import sys
import unittest

from lifeos_hook_bridge.memory_service import MemoryService
import test_memory_delegation as delegation
from test_memory_native import OWNER


class MemoryInferenceLogPublicationTests(unittest.TestCase):
    def setUp(self):
        self.fixture = delegation.MemoryDelegationTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.root = self.fixture.root
        self.path = self.root / 'LIFEOS/MEMORY/OBSERVABILITY/model-verification.jsonl'
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.before = b'{"synthetic":"previous verification"}\n'
        self.path.write_bytes(self.before)
        self.entry = {'ts': '2026-10-04T00:00:00.000Z', 'level': 'low', 'requested': 'haiku',
                      'expected_tier': 'haiku', 'executed': 'synthetic-flashnext',
                      'downgraded': True, 'latency_ms': 10}
        self.service = MemoryService(self.fixture.configuration)

    def call(self, entry=None):
        return self.service.native(self.fixture.context, 'inference_log', {'entry': self.entry if entry is None else entry})

    def test_native_metadata_appends_exact_record_with_private_permissions(self):
        result = self.call()
        self.assertTrue(result['ok'], result)
        expected = self.before + (json.dumps(self.entry, separators=(',', ':')) + '\n').encode()
        self.assertEqual(self.path.read_bytes(), expected)
        self.assertEqual(self.path.stat().st_mode & 0o777, 0o600)

    def test_private_metadata_refuses_without_changing_previous_log(self):
        result = self.call({**self.entry, 'executed': '<private>Synthetic hidden model.</private>'})
        self.assertFalse(result['ok'], result)
        self.assertEqual(self.path.read_bytes(), self.before)

    def test_unknown_fields_and_invalid_types_refuse_before_publication(self):
        for entry in ({**self.entry, 'path': 'foreign'}, {**self.entry, 'latency_ms': True},
                      {**self.entry, 'level': {}}, {**self.entry, 'executed': 'x' * 4097}):
            with self.subTest(entry=entry):
                self.assertFalse(self.call(entry)['ok'])
                self.assertEqual(self.path.read_bytes(), self.before)

    def test_restricted_owner_cannot_publish_global_log(self):
        self.fixture.configuration.update(lambda value: value['destinations']['chat-a:200'].update(
            read=['project'], write=['project'], projects=['lab']))
        self.assertFalse(self.call()['ok'])
        self.assertEqual(self.path.read_bytes(), self.before)

    def process(self, mode):
        result = subprocess.run([sys.executable, str(Path(__file__).with_name('memory_inference_log_process.py')),
            str(self.fixture.configuration.path), mode], capture_output=True, text=True, timeout=40)
        self.assertEqual(result.stderr, '')
        return result

    def test_later_destination_edit_is_preserved(self):
        result = self.process('destination')
        self.assertEqual(result.returncode, 0, result.stdout)
        outcome = json.loads(result.stdout)
        self.assertFalse(outcome['result']['ok'], outcome)
        self.assertTrue(outcome['later_preserved'])

    def test_revocation_before_publication_preserves_log(self):
        result = self.process('authority')
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertFalse(json.loads(result.stdout)['result']['ok'])
        self.assertEqual(self.path.read_bytes(), self.before)

    def test_actual_death_after_append_restores_previous_log(self):
        result = self.process('interrupt')
        self.assertEqual(result.returncode, 73, result.stdout)
        self.assertNotEqual(self.path.read_bytes(), self.before)
        with self.fixture.fixture.memory._transaction():
            self.assertEqual(self.path.read_bytes(), self.before)
        self.assertFalse(self.fixture.fixture.memory.transaction.journal.exists())
