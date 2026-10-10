# ABOUTME: Verifies actual Linux owner moves, access-time changes, and interrupted file recovery.
# ABOUTME: Requires small metadata journals that preserve media bytes and later owner edits.
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest

from lifeos_hook_bridge.memory_access import MemoryUnavailable
from lifeos_hook_bridge.memory_moves import MemoryMoves, fingerprint, inventory, move
from lifeos_hook_bridge.memory_transaction import MemoryTransaction


class MemoryMoveTests(unittest.TestCase):
    def setUp(self):
        self.directory=tempfile.TemporaryDirectory(prefix='memory-moves-')
        self.addCleanup(self.directory.cleanup)
        self.root=Path(self.directory.name)
        self.source=self.root/'source'
        self.source.write_bytes(b'Synthetic recoverable owner media.\n')
        self.destination=self.root/'trash/source'
        self.destination.parent.mkdir()
        self.artifact=self.root/'artifact'
        self.artifact.mkdir()
        (self.artifact/'transcript.md').write_text('Synthetic owner derivative.\n')
        self.quarantine=self.root/'quarantine'
        paths={'inbox:source':self.source,'trash:source':self.destination,
               'artifacts:synthetic1':self.artifact,'quarantine:synthetic1':self.quarantine}
        self.moves=MemoryMoves(lambda name:paths[name])
        self.ledger=self.root/'ledger'
        self.ledger.write_bytes(b'Synthetic original ledger.\n')
        self.expected=b'Synthetic tombstone ledger.\n'
        self.transaction=MemoryTransaction(self.root/'state',lambda name:self.root/name,moves=self.moves)
        self.transaction.state.mkdir()
        self.connection=sqlite3.connect(self.root/'operations.db')
        self.connection.row_factory=sqlite3.Row
        self.addCleanup(self.connection.close)
        self.connection.execute('CREATE TABLE operations (writer TEXT, request_id TEXT, receipt TEXT)')

    def entries(self):
        return [{'source':'inbox:source','destination':'trash:source','digest':fingerprint(self.source),'remove':False},
                {'source':'artifacts:synthetic1','destination':'quarantine:synthetic1','digest':fingerprint(self.artifact),'remove':True,'inventory':inventory(self.artifact)}]

    def reserve(self,entries,status='unknown'):
        self.transaction.prepare('synthetic-owner','synthetic-delete',['ledger'],
            expected={'ledger':hashlib.sha256(self.expected).hexdigest()})
        self.connection.execute('INSERT INTO operations VALUES (?,?,?)',
            ('synthetic-owner','synthetic-delete',json.dumps({'status':status})))
        self.connection.commit()
        self.transaction.prepare_moves(entries)
        self.ledger.write_bytes(self.expected)

    def test_read_access_time_change_does_not_reject_unchanged_owner_media(self):
        before=self.source.stat()
        os.utime(self.source,ns=(before.st_mtime_ns-10_000_000_000,before.st_mtime_ns))
        digest=fingerprint(self.source)
        self.assertEqual(len(digest),64)
        self.assertGreater(self.source.stat().st_atime_ns,before.st_mtime_ns-10_000_000_000)
        self.assertEqual(fingerprint(self.source),digest)

    def test_actual_no_replacement_rename_preserves_existing_trash(self):
        self.destination.write_bytes(b'Synthetic prior trash.\n')
        with self.assertRaises(FileExistsError):move(self.source,self.destination)
        self.assertEqual(self.source.read_bytes(),b'Synthetic recoverable owner media.\n')
        self.assertEqual(self.destination.read_bytes(),b'Synthetic prior trash.\n')

    def test_interruption_after_first_move_restores_media_and_exact_ledger(self):
        entries=self.entries()
        self.reserve(entries)
        move(self.source,self.destination)
        self.transaction.recover(self.connection)
        self.assertEqual(self.source.read_bytes(),b'Synthetic recoverable owner media.\n')
        self.assertFalse(self.destination.exists())
        self.assertTrue(self.artifact.exists())
        self.assertEqual(self.ledger.read_bytes(),b'Synthetic original ledger.\n')
        self.assertFalse(self.transaction.journal.exists())

    def test_interruption_after_all_moves_restores_artifacts_and_source(self):
        entries=self.entries()
        self.reserve(entries)
        self.moves.apply(entries)
        self.transaction.recover(self.connection)
        self.assertTrue(self.source.exists())
        self.assertEqual((self.artifact/'transcript.md').read_text(),'Synthetic owner derivative.\n')
        self.assertFalse(self.quarantine.exists())
        self.assertFalse(self.destination.exists())

    def test_later_ledger_edit_prevents_all_move_recovery(self):
        entries=self.entries()
        self.reserve(entries)
        self.moves.apply(entries)
        self.ledger.write_bytes(b'Synthetic later owner ledger.\n')
        with self.assertRaises(MemoryUnavailable):self.transaction.recover(self.connection)
        self.assertFalse(self.source.exists())
        self.assertTrue(self.destination.exists())
        self.assertTrue(self.quarantine.exists())
        self.assertEqual(self.ledger.read_bytes(),b'Synthetic later owner ledger.\n')
        self.assertTrue(self.transaction.journal.exists())

    def test_later_source_recreation_prevents_all_move_and_ledger_recovery(self):
        entries=self.entries()
        self.reserve(entries)
        self.moves.apply(entries)
        self.source.write_bytes(b'Synthetic newly recreated owner media.\n')
        with self.assertRaises(MemoryUnavailable):self.transaction.recover(self.connection)
        self.assertEqual(self.source.read_bytes(),b'Synthetic newly recreated owner media.\n')
        self.assertTrue(self.destination.exists())
        self.assertTrue(self.quarantine.exists())
        self.assertEqual(self.ledger.read_bytes(),self.expected)

    def test_committed_recovery_removes_only_selected_quarantine_and_keeps_trash(self):
        entries=self.entries()
        self.reserve(entries,status='committed')
        self.moves.apply(entries)
        self.transaction.recover(self.connection)
        self.assertFalse(self.quarantine.exists())
        self.assertFalse(self.artifact.exists())
        self.assertEqual(self.destination.read_bytes(),b'Synthetic recoverable owner media.\n')
        self.assertEqual(self.ledger.read_bytes(),self.expected)
        self.assertFalse(self.transaction.journal.exists())

    def test_later_quarantine_edit_refuses_committed_cleanup(self):
        entries=self.entries()
        self.reserve(entries,status='committed')
        self.moves.apply(entries)
        (self.quarantine/'transcript.md').write_text('Synthetic later derivative edit.\n')
        with self.assertRaises(MemoryUnavailable):self.transaction.recover(self.connection)
        self.assertEqual((self.quarantine/'transcript.md').read_text(),'Synthetic later derivative edit.\n')
        self.assertTrue(self.transaction.journal.exists())

    def test_large_media_journal_keeps_metadata_without_media_bytes(self):
        with self.source.open('wb') as stream:stream.truncate(32*1024*1024)
        entries=self.entries()
        self.reserve(entries)
        journal=self.transaction.journal.read_bytes()
        self.assertLess(len(journal),3000)
        self.moves.apply(entries)
        self.transaction.recover(self.connection)
        self.assertEqual(self.source.stat().st_size,32*1024*1024)

    def test_committed_partial_cleanup_finishes_remaining_original_artifacts(self):
        (self.artifact/'second.md').write_text('Synthetic second derivative.\n')
        entries=self.entries()
        self.reserve(entries,status='committed')
        self.moves.apply(entries)
        (self.quarantine/'transcript.md').unlink()
        self.transaction.recover(self.connection)
        self.assertFalse(self.quarantine.exists())
        self.assertTrue(self.destination.exists())
        self.assertFalse(self.transaction.journal.exists())

    def test_committed_partial_cleanup_preserves_a_later_remaining_edit(self):
        (self.artifact/'second.md').write_text('Synthetic second derivative.\n')
        entries=self.entries()
        self.reserve(entries,status='committed')
        self.moves.apply(entries)
        (self.quarantine/'transcript.md').unlink()
        (self.quarantine/'second.md').write_text('Synthetic later owner derivative.\n')
        with self.assertRaises(MemoryUnavailable):self.transaction.recover(self.connection)
        self.assertEqual((self.quarantine/'second.md').read_text(),'Synthetic later owner derivative.\n')
        self.assertTrue(self.transaction.journal.exists())

    def test_move_reservation_requires_expected_ledger_identity(self):
        self.transaction.prepare('synthetic-owner','unsafe-delete',['ledger'])
        before=self.transaction.journal.read_bytes()
        with self.assertRaises(MemoryUnavailable):self.transaction.prepare_moves(self.entries())
        self.assertEqual(self.transaction.journal.read_bytes(),before)
        self.assertTrue(self.source.exists())

    def test_move_recovery_requires_expected_ledger_identity_before_any_effect(self):
        entries=self.entries()
        self.reserve(entries)
        self.moves.apply(entries)
        journal=json.loads(self.transaction.journal.read_text())
        journal['copies'][0].pop('after_digest')
        self.transaction.journal.write_text(json.dumps(journal))
        before=self.ledger.read_bytes()
        with self.assertRaises(MemoryUnavailable):self.transaction.recover(self.connection)
        self.assertEqual(self.ledger.read_bytes(),before)
        self.assertFalse(self.source.exists())
        self.assertTrue(self.destination.exists())
