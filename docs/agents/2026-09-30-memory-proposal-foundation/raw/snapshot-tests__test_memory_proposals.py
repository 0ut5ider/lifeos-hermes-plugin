# ABOUTME: Verifies governed native proposal enqueue outcomes and safe retries.
# ABOUTME: Uses real LifeOS scope routing and synthetic approval targets.
from dataclasses import replace
import json
import shutil
from pathlib import Path
import unittest

import test_memory_native as native_fixture
from lifeos_hook_bridge.memory_policy import MemoryScope


class MemoryProposalTests(unittest.TestCase):
    def setUp(self):
        self.fixture = native_fixture.NativeMemoryTests(); self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.memory = self.fixture.memory
        tools = self.fixture.root / 'LIFEOS/TOOLS'
        tools.unlink()
        shutil.copytree(native_fixture.SOURCE / 'LIFEOS/TOOLS', tools)
        (self.fixture.root / 'LIFEOS/USER/PROJECTS.md').write_text('| **SyntheticLab** | synthetic fixture |\n')
        (self.fixture.root / 'LIFEOS/PULSE').symlink_to(native_fixture.SOURCE / 'LIFEOS/PULSE')
        config = self.fixture.root / 'LIFEOS/USER/CONFIG'
        config.mkdir()
        self.target = config / 'OPERATIONAL_RULES.md'
        self.target.write_text('# Operational rules\n')
        self.scope = replace(native_fixture.OWNER, proposals=('create', 'review', 'approve', 'auto_apply'))

    def item(self, edit='Always confirm before deploying changes to production.', **extra):
        return {'type':'proposal', 'target_kind':'operational-rule',
                'target_file':str(self.target), 'edit':edit, 'confidence':0.5,
                'rationale':'Synthetic explicit owner preference.', **extra}

    def enqueue(self, request='proposal-one', item=None, scope=None):
        return self.memory.native_add(scope or self.scope, item or self.item(), request_id=request,
                                      project='', source_session='synthetic-session')

    def test_enqueue_reports_pending_not_committed_and_has_native_reference(self):
        result = self.enqueue()
        self.assertTrue(result['ok'], result)
        receipt = result['receipt']
        self.assertEqual(receipt['status'], 'pending')
        reference = receipt['proposal_reference']
        rows = [json.loads(line) for line in Path(result['path']).read_text().splitlines()]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['id'], reference['id'])
        self.assertEqual(rows[0]['status'], 'pending')
        self.assertNotIn(self.item()['edit'], self.target.read_text())
        self.assertEqual(receipt['writer'], self.scope.writer)
        self.assertEqual(self.memory.recall(self.scope, 'production'), [])
        self.assertEqual(self.enqueue(), result)
        self.assertEqual(len(Path(result['path']).read_text().splitlines()), 1)

    def test_fact_write_grant_does_not_grant_proposal_creation(self):
        result = self.enqueue(scope=native_fixture.OWNER)
        self.assertFalse(result['ok'])
        self.assertIn('proposal', result['message'].lower())
        self.assertFalse((self.fixture.root / 'LIFEOS/MEMORY/OBSERVABILITY/pending-proposals.jsonl').exists())

    def test_native_project_diversion_is_not_reported_as_queued(self):
        result = self.enqueue(item=self.item('SyntheticLab must use a dedicated deployment checklist.'))
        self.assertTrue(result['ok'], result)
        self.assertEqual(result['receipt']['status'], 'diverted')
        path = Path(result['receipt']['destination'])
        self.assertTrue(path.is_file())
        self.assertIn('deployment checklist', path.read_text())
        self.assertFalse((self.fixture.root / 'LIFEOS/MEMORY/OBSERVABILITY/pending-proposals.jsonl').exists())
        self.assertNotIn('deployment checklist', self.target.read_text())
        self.assertEqual(self.enqueue(item=self.item('SyntheticLab must use a dedicated deployment checklist.')), result)

    def test_invalid_and_private_proposal_text_is_not_enqueued(self):
        for index, item in enumerate((self.item('<private>synthetic secret</private>'),
                                      self.item(target_kind='unknown'))):
            with self.subTest(index=index):
                result = self.enqueue(request='invalid-' + str(index), item=item)
                self.assertFalse(result['ok'], result)
        self.assertFalse((self.fixture.root / 'LIFEOS/MEMORY/OBSERVABILITY/pending-proposals.jsonl').exists())

    def test_native_accept_and_reject_keep_the_queue_state_truthful(self):
        saved = self.enqueue()
        reference = saved['receipt']['proposal_reference']
        result = self.memory.decide_proposal(self.scope, reference, 'accept', 'accept-one')
        self.assertEqual(result['status'], 'committed', result)
        self.assertEqual(result['proposal_status'], 'accepted')
        self.assertIn(self.item()['edit'], self.target.read_text())
        self.assertEqual(self.memory.decide_proposal(self.scope, reference, 'accept', 'accept-one'), result)
        self.assertEqual(self.memory.decide_proposal(self.scope, reference, 'accept', 'accept-again')['status'], 'conflict')
        other = self.enqueue('other-proposal', self.item('Always record synthetic test outcomes before the next operation.'))
        result = self.memory.decide_proposal(self.scope, other['receipt']['proposal_reference'], 'reject', 'reject-one')
        self.assertEqual(result['proposal_status'], 'rejected', result)
        self.assertNotIn('synthetic test outcomes', self.target.read_text())

    def test_creator_cannot_approve_and_stale_target_does_not_overwrite(self):
        saved = self.enqueue()
        reference = saved['receipt']['proposal_reference']
        creator = replace(self.scope, proposals=('create', 'review'))
        denied = self.memory.decide_proposal(creator, reference, 'accept', 'creator-accept')
        self.assertEqual(denied['status'], 'rejected')
        self.target.write_text('# Unrelated concurrent target update\n')
        conflict = self.memory.decide_proposal(self.scope, reference, 'accept', 'stale-accept')
        self.assertEqual(conflict['status'], 'conflict', conflict)
        self.assertEqual(self.target.read_text(), '# Unrelated concurrent target update\n')

    def test_proposal_review_requires_an_explicit_permission(self):
        self.enqueue()
        self.assertEqual(len(self.memory.review_proposals(self.scope)), 1)
        self.assertEqual(self.memory.review_proposals(native_fixture.OWNER), [])

    def test_interrupted_diversion_removes_uncommitted_files_and_can_retry(self):
        item = self.item('SyntheticLab must use a dedicated deployment checklist.')
        with self.assertRaisesRegex(RuntimeError, 'synthetic interruption'):
            with self.memory._transaction() as connection:
                payload = {'operation':'native_proposal', 'item':item}
                paths = self.memory._publication_paths(connection, payload)
                self.memory.transaction.prepare(self.scope.writer, 'interrupted', paths)
                connection.execute('INSERT INTO operations VALUES (?,?,?,?)',
                                   (self.scope.writer, 'interrupted', 'synthetic', json.dumps({'status':'unknown'})))
                connection.commit()
                native = self.memory._native('add', item=item)
                self.assertTrue(native['ok'], native)
                connection.execute('BEGIN IMMEDIATE')
                raise RuntimeError('synthetic interruption')
        records = self.fixture.root / 'LIFEOS/MEMORY/UPGRADES/records'
        self.assertEqual(len(list(records.glob('*.md'))), 1)
        unrelated = records / 'unrelated.md'
        unrelated.write_text('Unrelated publication after the operation failed.')
        with self.memory._transaction() as connection:
            self.assertEqual(list(records.glob('*.md')), [unrelated])
            self.assertIsNone(connection.execute("SELECT receipt FROM operations WHERE request_id='interrupted'").fetchone())
        self.assertFalse((records.parent / '.state.json').exists())
        result = self.enqueue('after-recovery', item)
        self.assertEqual(result['receipt']['status'], 'diverted', result)

    def test_client_creation_and_owner_approval_have_separate_grants(self):
        from lifeos_hook_bridge.memory_service import MemoryConfiguration, MemoryService
        config = self.fixture.home / 'hermes/memory.json'
        owner_destination = {'visibility':'private', 'participants':['owner'],
                             'read':['principal','assistant','project'], 'write':[], 'projects':['*'],
                             'model_routes':['local'], 'proposals':['review','approve']}
        value = {'version':1, 'root':str(self.fixture.root), 'principal':'owner', 'sharing_enabled':True,
                 'accounts':{'chat-a:owner':'owner'}, 'destinations':{'chat-a:private':owner_destination},
                 'clients':{'research':{'enabled':True, 'read':['principal','assistant','project'], 'write':[],
                                       'projects':['*'], 'model_route':'unknown', 'proposals':['create','review']}}}
        configuration = MemoryConfiguration(config); configuration.save(value)
        service = MemoryService(configuration)
        response = service.call_client('research', 'lifeos_memory_propose', {'proposal':self.item(), 'request_id':'client-proposal'})
        self.assertEqual(response['status'], 'pending', response)
        reference = response['proposal_reference']
        denied = service.call_client('research', 'lifeos_memory_decide_proposal',
                                     {'reference':reference, 'decision':'accept', 'request_id':'client-accept'})
        self.assertEqual(denied['status'], 'rejected')
        from lifeos_hook_bridge.memory_policy import SessionContext
        context = SessionContext('chat-a', 'owner', 'private', 'private', ('owner',), 'local', 'session')
        approved = service.call_context(context, 'lifeos_memory_decide_proposal',
                                       {'reference':reference, 'decision':'accept', 'request_id':'owner-accept'})
        self.assertEqual(approved['status'], 'committed', approved)
        self.assertIn(self.item()['edit'], self.target.read_text())
        value['clients']['research']['proposals'].append('approve')
        with self.assertRaises(ValueError):
            configuration.save(value)
