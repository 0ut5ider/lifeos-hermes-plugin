# ABOUTME: Verifies private publication recovery against actual files and SQLite receipts.
# ABOUTME: Checks expected publication hashes before restoring interrupted artifact groups.
import hashlib
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

from lifeos_hook_bridge.memory_access import MemoryUnavailable
from lifeos_hook_bridge.memory_transaction import MemoryTransaction


class MemoryPublicationRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix='publication-recovery-')
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.transaction = MemoryTransaction(self.root / 'state', lambda name: self.root / name)
        self.transaction.state.mkdir(mode=0o700)
        self.connection = sqlite3.connect(self.root / 'operations.db')
        self.addCleanup(self.connection.close)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute('CREATE TABLE operations (writer TEXT, request_id TEXT, receipt TEXT)')
        self.first, self.second = self.root / 'first', self.root / 'second'
        self.first.write_bytes(b'Synthetic original first artifact')

    def reserve(self, status='unknown', expected=None):
        arguments = {} if expected is None else {'expected': expected}
        self.transaction.prepare('synthetic-writer', 'synthetic-operation', ['first', 'second'], **arguments)
        self.connection.execute('INSERT INTO operations VALUES (?,?,?)',
            ('synthetic-writer', 'synthetic-operation', json.dumps({'status': status})))
        self.connection.commit()

    def digests(self):
        return {name: hashlib.sha256(data).hexdigest() for name, data in
            {'first': b'Synthetic published first artifact', 'second': b'Synthetic published second artifact'}.items()}

    def test_unknown_original_operation_restores_existing_and_absent_targets(self):
        self.reserve()
        self.first.write_bytes(b'Synthetic published first artifact')
        self.second.write_bytes(b'Synthetic published second artifact')
        self.transaction.recover(self.connection)
        self.assertEqual(self.first.read_bytes(), b'Synthetic original first artifact')
        self.assertFalse(self.second.exists())
        self.assertFalse(self.transaction.journal.exists())
        self.assertEqual(self.connection.execute('SELECT COUNT(*) FROM operations').fetchone()[0], 0)

    def test_committed_original_operation_keeps_publications_and_removes_its_journal(self):
        self.reserve(status='committed')
        self.first.write_bytes(b'Synthetic published first artifact')
        self.transaction.recover(self.connection)
        self.assertEqual(self.first.read_bytes(), b'Synthetic published first artifact')
        self.assertFalse(self.transaction.journal.exists())
        self.assertEqual(self.connection.execute('SELECT COUNT(*) FROM operations').fetchone()[0], 1)

    def test_expected_publications_restore_only_original_or_owned_artifact_bytes(self):
        self.reserve(expected=self.digests())
        self.first.write_bytes(b'Synthetic published first artifact')
        self.transaction.recover(self.connection)
        self.assertEqual(self.first.read_bytes(), b'Synthetic original first artifact')
        self.assertFalse(self.second.exists())

    def test_later_edit_refuses_before_any_member_of_the_group_is_restored(self):
        self.reserve(expected=self.digests())
        self.first.write_bytes(b'Synthetic published first artifact')
        self.second.write_bytes(b'Synthetic later owner edit')
        before = self.first.read_bytes(), self.second.read_bytes()
        with self.assertRaisesRegex(MemoryUnavailable, 'later'):
            self.transaction.recover(self.connection)
        self.assertEqual((self.first.read_bytes(), self.second.read_bytes()), before)
        self.assertTrue(self.transaction.journal.exists())
        self.assertEqual(self.connection.execute('SELECT COUNT(*) FROM operations').fetchone()[0], 1)

    def test_invalid_expected_hashes_refuse_without_creating_a_recovery_journal(self):
        for expected in ([], {}, {'first': 'bad', 'second': 'bad'}, {'first': self.digests()['first']},
                {**self.digests(), 'third': 'a' * 64}, {'first': [], 'second': {}}):
            with self.subTest(expected=expected), self.assertRaises(ValueError):
                self.transaction.prepare('writer', 'operation', ['first', 'second'], expected=expected)
            self.assertFalse(self.transaction.journal.exists())

    def test_changed_expected_journal_hash_refuses_without_restoring_any_file(self):
        self.reserve(expected=self.digests())
        document = json.loads(self.transaction.journal.read_text())
        document['copies'][0]['after_digest'] = []
        self.transaction.journal.write_text(json.dumps(document))
        self.first.write_bytes(b'Synthetic published first artifact')
        with self.assertRaises(MemoryUnavailable):
            self.transaction.recover(self.connection)
        self.assertEqual(self.first.read_bytes(), b'Synthetic published first artifact')
        self.assertTrue(self.transaction.journal.exists())

    def test_invalid_operation_journal_shapes_refuse_before_any_recovery_effect(self):
        self.reserve(expected=self.digests())
        document = json.loads(self.transaction.journal.read_text())
        malformed = [[], None, {**document, 'copies': None}, {**document, 'copies': [42]},
            {**document, 'copies': [None]}, {**document, 'writer': []}, {**document, 'request_id': {}},
            {key: value for key, value in document.items() if key != 'writer'},
            {**document, 'copies': [document['copies'][0], {**document['copies'][1], 'data': '!bad base64!'}]}]
        for value in malformed:
            with self.subTest(value=value):
                self.transaction.journal.write_text(json.dumps(value))
                self.first.write_bytes(b'Synthetic published first artifact')
                with self.assertRaises(MemoryUnavailable):
                    self.transaction.recover(self.connection)
                self.assertEqual(self.first.read_bytes(), b'Synthetic published first artifact')
                self.assertFalse(self.second.exists())
                self.assertTrue(self.transaction.journal.exists())

    def test_expected_deleted_publication_restores_original_and_absent_targets(self):
        self.reserve(expected={'first':None,'second':self.digests()['second']})
        self.first.unlink()
        self.second.write_bytes(b'Synthetic published second artifact')
        self.transaction.recover(self.connection)
        self.assertEqual(self.first.read_bytes(),b'Synthetic original first artifact')
        self.assertFalse(self.second.exists())

    def test_later_recreation_of_expected_deleted_file_blocks_all_recovery(self):
        self.reserve(expected={'first':None,'second':self.digests()['second']})
        self.first.unlink()
        self.first.write_bytes(b'Synthetic later recreated owner artifact')
        self.second.write_bytes(b'Synthetic published second artifact')
        with self.assertRaises(MemoryUnavailable):self.transaction.recover(self.connection)
        self.assertEqual(self.first.read_bytes(),b'Synthetic later recreated owner artifact')
        self.assertEqual(self.second.read_bytes(),b'Synthetic published second artifact')
        self.assertTrue(self.transaction.journal.exists())


if __name__ == '__main__':
    unittest.main()
