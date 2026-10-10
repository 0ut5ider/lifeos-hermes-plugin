# ABOUTME: Tests current caller authority immediately before real native memory publication.
# ABOUTME: Exercises native and explicit writers after validation or source reads revoke access.
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

from lifeos_hook_bridge.memory_access import HOT_FILES
import test_memory_proposal_delegation as delegation_fixture


class MemoryPublicationAuthorityTests(unittest.TestCase):
    def setUp(self):
        self.fixture = delegation_fixture.MemoryProposalDelegationTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.memory = self.fixture.fixture.memory
        self.scope = self.fixture.fixture.scope

    def run_request(self, operation, arguments, trigger, *, interface='native', revoke=True, trigger_count=1):
        environment = dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[1]))
        response = subprocess.run([sys.executable, str(Path(__file__).with_name(
            'memory_publication_authority_process.py')), str(self.fixture.config)],
            input=json.dumps({'operation': operation, 'arguments': arguments, 'trigger': trigger,
                              'interface': interface, 'revoke': revoke, 'trigger_count': trigger_count}),
            text=True, capture_output=True, env=environment, timeout=40)
        self.assertEqual(response.returncode, 0, response.stderr)
        self.assertEqual(response.stderr, '')
        receipt = json.loads(response.stdout)
        if revoke:
            self.assertTrue(receipt['revoked'], receipt)
            after = receipt['actions'][receipt['actions'].index('authority_revoked') + 1:]
            self.assertFalse(set(after) & {'add', 'set_hot', 'proposal_decision'}, receipt)
            self.assertNotIn(receipt['result'].get('status'), ('committed', 'pending'), receipt)
            self.assertFalse(receipt['result'].get('ok', False), receipt)
        return receipt

    def add_arguments(self, item):
        return {'item': item, 'request_id': 'publication-authority', 'project': 'lab', 'observed_revision': ''}

    def test_native_hot_add_refuses_authority_revoked_during_validation(self):
        item = {'type': 'memory', 'actor': 'principal', 'content': 'RULE: Synthetic current authority marker'}
        self.run_request('add', self.add_arguments(item), 'validate')
        self.assertEqual(self.memory.read_hot(self.scope, 'principal')['entries'], [])

    def test_native_archive_add_refuses_authority_revoked_during_routing(self):
        item = {'type': 'knowledge', 'entity_type': 'research', 'name': 'Synthetic authority',
                'content': 'Synthetic current authority marker', 'source_session': 'native-session'}
        self.run_request('add', self.add_arguments(item), 'route')
        self.assertEqual(self.memory.recall(self.scope, 'authority marker'), [])

    def test_native_hot_set_refuses_authority_revoked_during_validation(self):
        path = self.fixture.root / HOT_FILES['principal']
        revision = self.memory.read_hot(self.scope, 'principal')['revision']
        self.run_request('set', {'path': str(path), 'entries': ['RULE: Synthetic current authority marker'],
            'request_id': 'publication-authority', 'observed_revision': revision, 'allow_drastic': False}, 'validate')
        self.assertEqual(self.memory.read_hot(self.scope, 'principal')['entries'], [])

    def test_native_add_set_refuses_authority_revoked_during_validation(self):
        arguments = self.add_arguments({'type': 'memory', 'actor': 'principal', 'op': 'set',
                                       'entries': ['RULE: Synthetic current authority marker']})
        arguments['observed_revision'] = self.memory.read_hot(self.scope, 'principal')['revision']
        self.run_request('add', arguments, 'validate')
        self.assertEqual(self.memory.read_hot(self.scope, 'principal')['entries'], [])

    def decision(self, decision, interface='native', trigger='validate'):
        reference = self.fixture.fixture.enqueue()['receipt']['proposal_reference']
        before = self.fixture.fixture.target.read_bytes()
        operation = 'proposal_decision' if interface == 'native' else 'lifeos_memory_decide_proposal'
        self.run_request(operation, {'reference': reference, 'decision': decision,
            'request_id': 'publication-authority'}, trigger, interface=interface)
        self.assertEqual(self.fixture.fixture.target.read_bytes(), before)
        self.assertEqual(len(self.memory.review_proposals(self.scope)), 1)

    def test_native_accept_refuses_authority_revoked_during_validation(self):
        self.decision('accept')

    def test_native_reject_refuses_authority_revoked_after_queue_read(self):
        self.decision('reject', trigger='proposal_read')

    def test_explicit_accept_refuses_authority_revoked_during_validation(self):
        self.decision('accept', interface='explicit')

    def remember(self, category):
        self.run_request('lifeos_memory_remember', {'category': category,
            'content': 'RULE: Synthetic current authority marker' if category == 'principal' else
                       'Synthetic current authority marker',
            'title': 'Synthetic authority', 'project': 'lab' if category == 'project' else '',
            'request_id': 'publication-authority'}, 'validate', interface='explicit', trigger_count=2)
        self.assertEqual(self.memory.recall(self.scope, 'authority marker'), [])

    def test_explicit_hot_remember_refuses_authority_revoked_during_validation(self):
        self.remember('principal')

    def test_explicit_archive_remember_refuses_authority_revoked_during_validation(self):
        self.remember('project')

    def change(self, category, operation, trigger):
        saved = self.memory.remember(self.scope, category=category,
            content='RULE: Synthetic original authority marker' if category == 'principal' else
                    'Synthetic original authority marker',
            title='Synthetic authority', project='lab' if category == 'project' else '', request_id='original')
        arguments = {'reference': saved['reference'], 'request_id': 'publication-authority'}
        if operation == 'correct':
            arguments['content'] = 'RULE: Synthetic changed authority marker' if category == 'principal' else \
                                   'Synthetic changed authority marker'
        self.run_request('lifeos_memory_' + operation, arguments, trigger, interface='explicit',
                         trigger_count=2 if trigger in ('route', 'read_hot', 'target_read') else 1)
        retained = self.memory.get(self.scope, saved['reference'])
        self.assertEqual(retained['status'], 'ok', retained)
        self.assertIn('original authority marker', retained['content'])

    def test_explicit_hot_correction_refuses_authority_revoked_during_validation(self):
        self.change('principal', 'correct', 'validate')

    def test_explicit_archive_correction_refuses_authority_revoked_during_routing(self):
        self.change('project', 'correct', 'route')

    def test_explicit_hot_forget_refuses_authority_revoked_after_native_read(self):
        self.change('principal', 'forget', 'read_hot')

    def test_explicit_archive_forget_refuses_authority_revoked_after_registry_read(self):
        self.change('project', 'forget', 'target_read')

    def test_unchanged_authority_allows_a_real_native_write(self):
        item = {'type': 'memory', 'actor': 'principal', 'content': 'RULE: Synthetic current authority marker'}
        receipt = self.run_request('add', self.add_arguments(item), 'validate', revoke=False)
        self.assertTrue(receipt['result']['ok'], receipt)
        self.assertEqual(self.memory.read_hot(self.scope, 'principal')['entries'], [item['content']])
