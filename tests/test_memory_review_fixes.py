# ABOUTME: Regression tests for memory defects that the independent review of pull request 3 reports.
# ABOUTME: Covers revocation during a client call and recovery after a later owner edit.
import json
import unittest
from unittest.mock import patch

from lifeos_hook_bridge import memory_service
from lifeos_hook_bridge.memory_service import MemoryConfiguration
import test_memory_service as service_fixture


class RevocationDuringCallTests(unittest.TestCase):
    def setUp(self):
        self.fixture = service_fixture.MemoryServiceTests(); self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.fixture.configuration['sharing_enabled'] = True
        self.fixture.configuration['clients']['research']['write'] = ['project']
        self.save()
        self.service = self.fixture.service

    def save(self):
        MemoryConfiguration(self.fixture.config).save(self.fixture.configuration)

    def revoke(self):
        self.fixture.configuration['clients']['research']['enabled'] = False
        self.save()

    def during(self, method):
        original = getattr(memory_service.NativeMemory, method)

        def revoked_first(memory, *args, **kwargs):
            self.revoke()
            return original(memory, *args, **kwargs)
        return patch.object(memory_service.NativeMemory, method, revoked_first)

    def test_search_that_finishes_after_revocation_returns_no_fact(self):
        self.fixture.fixture.remember()
        with self.during('recall'):
            result = self.service.call_client('research', 'lifeos_memory_search', {'query': 'synthetic lab'})
        self.assertEqual(result['status'], 'rejected', result)
        self.assertNotIn('results', result)

    def test_read_by_reference_that_finishes_after_revocation_returns_no_fact(self):
        saved = self.fixture.fixture.remember()
        with self.during('get'):
            result = self.service.call_client('research', 'lifeos_memory_get', {'reference': saved['reference']})
        self.assertEqual(result['status'], 'rejected', result)
        self.assertNotIn('content', json.dumps(result))

    def test_write_that_reaches_publication_after_revocation_is_not_published(self):
        arguments = {'category': 'project', 'content': 'Synthetic late finding', 'title': 'Late finding',
                     'project': 'lab', 'request_id': 'late-write'}
        with self.during('remember'):
            result = self.service.call_client('research', 'lifeos_memory_remember', arguments)
        self.assertNotEqual(result['status'], 'committed', result)
        self.fixture.configuration['clients']['research']['enabled'] = True
        self.save()
        found = self.service.call_client('research', 'lifeos_memory_search', {'query': 'late finding'})
        self.assertEqual(found['results'], [], found)

    def test_narrowed_grant_during_a_call_withholds_the_result(self):
        self.fixture.fixture.remember()
        original = memory_service.NativeMemory.recall

        def narrowed_first(memory, *args, **kwargs):
            self.fixture.configuration['clients']['research']['projects'] = ['other']
            self.save()
            return original(memory, *args, **kwargs)
        with patch.object(memory_service.NativeMemory, 'recall', narrowed_first):
            result = self.service.call_client('research', 'lifeos_memory_search', {'query': 'synthetic lab'})
        self.assertEqual(result['status'], 'rejected', result)

    def test_unchanged_grant_still_returns_the_fact(self):
        saved = self.fixture.fixture.remember()
        result = self.service.call_client('research', 'lifeos_memory_search', {'query': 'synthetic lab'})
        self.assertEqual(result['results'][0]['reference'], saved['reference'])


class RecoveryPreservationTests(unittest.TestCase):
    def setUp(self):
        import sqlite3
        import tempfile
        from pathlib import Path
        from lifeos_hook_bridge.memory_transaction import MemoryTransaction
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.root = Path(folder.name) / 'store'
        self.root.mkdir()
        self.state = Path(folder.name) / 'state'
        self.transaction = MemoryTransaction(self.state, lambda name: self.root / name)
        self.connection = sqlite3.connect(':memory:')
        self.connection.row_factory = sqlite3.Row
        self.connection.execute('CREATE TABLE operations (writer TEXT, request_id TEXT, payload_digest TEXT, receipt TEXT)')

    def interrupted(self, original):
        target = self.root / 'fact.md'
        if original is not None:
            target.write_bytes(original)
        self.state.mkdir(exist_ok=True)
        self.transaction.prepare('owner', 'request-1', ['fact.md'])
        self.connection.execute('INSERT INTO operations VALUES (?,?,?,?)',
                                ('owner', 'request-1', 'digest', json.dumps({'status': 'unknown'})))
        return target

    def preserved(self):
        folder = self.state / 'recovery-preserved'
        return sorted(path.read_bytes() for path in folder.rglob('*') if path.is_file() and path.suffix != '.json') \
            if folder.exists() else []

    def test_recovery_keeps_a_copy_of_bytes_that_differ_from_the_journal_original(self):
        target = self.interrupted(b'original fact\n')
        target.write_bytes(b'owner edit after the interruption\n')
        self.transaction.recover(self.connection)
        self.assertEqual(target.read_bytes(), b'original fact\n')
        self.assertEqual(self.preserved(), [b'owner edit after the interruption\n'])
        manifests = list((self.state / 'recovery-preserved').rglob('*.json'))
        self.assertEqual(len(manifests), 1)
        record = json.loads(manifests[0].read_text())
        self.assertEqual((record['writer'], record['request_id'], list(record['files'])), ('owner', 'request-1', ['fact.md']))
        self.assertEqual(manifests[0].stat().st_mode & 0o777, 0o600)

    def test_recovery_keeps_a_copy_before_it_removes_a_file_that_did_not_exist(self):
        target = self.interrupted(None)
        target.write_bytes(b'created after the journal\n')
        self.transaction.recover(self.connection)
        self.assertFalse(target.exists())
        self.assertEqual(self.preserved(), [b'created after the journal\n'])

    def test_recovery_of_an_unchanged_or_missing_file_preserves_nothing(self):
        target = self.interrupted(b'original fact\n')
        self.transaction.recover(self.connection)
        self.assertEqual(self.preserved(), [])
        target = self.interrupted(b'original fact\n')
        target.unlink()
        self.transaction.recover(self.connection)
        self.assertEqual((target.read_bytes(), self.preserved()), (b'original fact\n', []))
