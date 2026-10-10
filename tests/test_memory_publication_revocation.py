# ABOUTME: Revokes actual owner authority between native batch publications.
# ABOUTME: Requires stopped mutations, unknown receipts, and recovery of original bytes.
from contextlib import closing, contextmanager
from dataclasses import replace
import json
import sqlite3
import unittest
from pathlib import Path

from lifeos_hook_bridge.memory_runtime import MemoryRuntime
from lifeos_hook_bridge.memory_service import MemoryService
from lifeos_hook_bridge.memory_transaction import publish
import test_memory_knowledge_harvest as knowledge_fixture
import test_memory_proposal_gc as proposal_fixture
import test_memory_session_harvest as session_fixture


class MemoryPublicationRevocationTests(unittest.TestCase):
    def fixture(self, kind):
        fixture = kind()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        return fixture

    @contextmanager
    def revoke_after_publication(self, module, configuration, number):
        original = module.publish
        events = []
        def observed(path, data):
            original(path, data)
            events.append(path)
            if len(events) == number:
                configuration.update(lambda value: value['accounts'].clear())
        module.publish = observed
        try:
            yield events
        finally:
            module.publish = original

    def assert_pending(self, fixture, response):
        self.assertEqual(response.get('code'), 'EACCESS_CHANGED', response)
        memory = fixture.fixture.fixture.memory
        self.assertTrue(memory.transaction.journal.exists())
        with closing(sqlite3.connect(memory.database)) as connection:
            receipts = [json.loads(row[0]) for row in connection.execute('SELECT receipt FROM operations')]
        self.assertEqual([row['status'] for row in receipts], ['unknown'], receipts)
        return memory

    def recover(self, memory):
        with memory._transaction() as connection:
            self.assertEqual(connection.execute('SELECT COUNT(*) FROM operations').fetchone()[0], 0)
        self.assertFalse(memory.transaction.journal.exists())

    def test_session_revocation_stops_later_learning_and_keeps_recovery(self):
        from lifeos_hook_bridge import memory_session_harvest as module
        for number in (1, 2):
            with self.subTest(publication=number):
                fixture = self.fixture(session_fixture.MemorySessionHarvestTests)
                configuration = fixture.fixture.configuration
                second = replace(fixture.context, session_id='synthetic-second-session')
                runtime = MemoryRuntime(configuration.path)
                with fixture.fixture.fixture.memory._transaction() as connection:
                    state = runtime._stamp(configuration.load(), second, connection)
                states = json.loads(runtime.state_path.read_text())
                states[second.session_id] = state
                publish(runtime.state_path, json.dumps(states).encode())
                row = {'type':'user', 'sessionId':second.session_id, 'timestamp':'2026-10-08T12:01:00+00:00',
                    'message':{'role':'user', 'content':'Actually, I meant to keep synthetic receipts for this lab.'}}
                publish(fixture.transcripts / (second.session_id + '.jsonl'), (json.dumps(row) + '\n').encode())
                with self.revoke_after_publication(module, configuration, number) as events:
                    response = MemoryService(configuration).native(fixture.context, 'session_harvest',
                        {'recent':20, 'all':False, 'session':None, 'projects_dir':None, 'dry_run':False, 'mine':False})
                self.assertEqual(len(events), number)
                memory = self.assert_pending(fixture, response)
                self.assertEqual(len(fixture.notes()), number)
                self.recover(memory)
                self.assertEqual(fixture.notes(), [])

    def test_proposal_revocation_stops_later_files_and_log_and_keeps_recovery(self):
        from lifeos_hook_bridge import memory_proposal_gc as module
        for number in (1, 2, 3):
            with self.subTest(publication=number):
                fixture = self.fixture(proposal_fixture.MemoryProposalGCTests)
                configuration = fixture.fixture.configuration
                second = fixture.root / 'LIFEOS/USER/PROJECTS.md'
                second.write_text('## Memory-System Proposals\n- Synthetic expired rule [SUPERSEDED]\n- Keep the synthetic current rule.\n')
                before = {path:path.read_bytes() for path in (fixture.target, second)}
                log = fixture.root / module.LOG
                with self.revoke_after_publication(module, configuration, number) as events:
                    response = MemoryService(configuration).native(fixture.fixture.context, 'proposal_gc',
                        {'apply':True, 'auto':True, 'route':False})
                self.assertEqual(len(events), number)
                memory = self.assert_pending(fixture, response)
                if number == 1:
                    self.assertEqual(second.read_bytes(), before[second])
                self.assertEqual(log.exists(), number == 3)
                self.recover(memory)
                for path, data in before.items():
                    self.assertEqual(path.read_bytes(), data)
                self.assertFalse(log.exists())

    def test_knowledge_revocation_stops_state_and_deletion_and_keeps_recovery(self):
        from lifeos_hook_bridge import memory_knowledge_harvest as module
        for number in (1, 2):
            with self.subTest(publication=number):
                fixture = self.fixture(knowledge_fixture.MemoryKnowledgeHarvestTests)
                configuration = fixture.fixture.configuration
                before = fixture.queue.read_bytes()
                with self.revoke_after_publication(module, configuration, number) as events:
                    response = MemoryService(configuration).native(fixture.fixture.context, 'knowledge_harvest',
                        {'source':'research', 'dry_run':False, 'max_notes':20, 'request_id':'synthetic-revoked-harvest'})
                self.assertEqual(len(events), number)
                memory = self.assert_pending(fixture, response)
                self.assertEqual(fixture.queue.read_bytes(), before)
                self.assertEqual(fixture.state.exists(), number == 2)
                self.recover(memory)
                self.assertEqual(fixture.queue.read_bytes(), before)
                self.assertFalse(fixture.note.exists())
                self.assertFalse(fixture.state.exists())

    def test_knowledge_revocation_before_record_retirement_preserves_registered_sources(self):
        from lifeos_hook_bridge import memory_knowledge_harvest as module
        fixture = self.fixture(knowledge_fixture.MemoryKnowledgeHarvestTests)
        source, reference = fixture.seed()
        original_source = source.read_bytes()
        original_queue = fixture.queue.read_bytes()
        configuration = fixture.fixture.configuration
        original = module.publish
        events = []
        def observed(path, data):
            original(path, data)
            events.append(path)
            if path == fixture.state:
                configuration.update(lambda value: value['accounts'].clear())
        module.publish = observed
        try:
            response = MemoryService(configuration).native(fixture.fixture.context, 'knowledge_harvest',
                {'source':'research', 'dry_run':False, 'max_notes':20, 'request_id':'synthetic-revoked-expiry'})
        finally:
            module.publish = original
        self.assertIn(fixture.state, events)
        memory = fixture.fixture.fixture.memory
        self.assertTrue(memory.transaction.journal.exists())
        self.assertEqual(response.get('code'), 'EACCESS_CHANGED', response)
        with closing(sqlite3.connect(memory.database)) as connection:
            record = connection.execute('SELECT path,status,revision FROM records WHERE id=?', (reference['id'],)).fetchone()
            receipt = json.loads(connection.execute('SELECT receipt FROM operations WHERE request_id=?',
                ('synthetic-revoked-expiry',)).fetchone()[0])
        self.assertEqual(record, ('LIFEOS/MEMORY/KNOWLEDGE/Research/synthetic-seed.md', 'active', 1))
        self.assertEqual(receipt['status'], 'unknown')
        self.assertEqual(source.read_bytes(), original_source)
        self.assertEqual(fixture.queue.read_bytes(), original_queue)
        with memory._transaction(): pass
        self.assertEqual(source.read_bytes(), original_source)
        self.assertFalse((fixture.knowledge / '_archive/Research/synthetic-seed.md').exists())

    def test_knowledge_revocation_after_queue_deletion_keeps_recovery(self):
        fixture = self.fixture(knowledge_fixture.MemoryKnowledgeHarvestTests)
        configuration = fixture.fixture.configuration
        before = fixture.queue.read_bytes()
        original = Path.unlink
        seen = []
        def observed(path, *args, **kwargs):
            original(path, *args, **kwargs)
            if path == fixture.queue:
                configuration.update(lambda value: value['accounts'].clear())
                seen.append(path)
        Path.unlink = observed
        try:
            response = MemoryService(configuration).native(fixture.fixture.context, 'knowledge_harvest',
                {'source':'research', 'dry_run':False, 'max_notes':20, 'request_id':'synthetic-revoked-deletion'})
        finally:
            Path.unlink = original
        self.assertEqual(seen, [fixture.queue])
        memory = self.assert_pending(fixture, response)
        self.recover(memory)
        self.assertEqual(fixture.queue.read_bytes(), before)
        self.assertFalse(fixture.note.exists())
        self.assertFalse(fixture.state.exists())
