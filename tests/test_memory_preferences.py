# ABOUTME: Tests owner-facing memory status and controls against native synthetic records.
# ABOUTME: Keeps sharing explicit and verifies that diagnostics do not claim unfinished activation.
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import threading
import unittest

from lifeos_hook_bridge.memory_preferences import MemoryPreferences
from lifeos_hook_bridge.memory_service import MemoryConfiguration
import test_memory_sharing as sharing_fixture
from sharing_component import COMPONENT


class MemoryPreferencesTests(unittest.TestCase):
    def setUp(self):
        self.fixture = sharing_fixture.MemorySharingTests(); self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.preferences = MemoryPreferences(self.fixture.fixture.config, self.fixture.fixture.fixture.root, Path('/usr/bin/python3'),
                                             Path(__file__).parents[1]/'lifeos_hook_bridge/memory_mcp.py',
                                             sharing_component=COMPONENT, sharing_options={'keys_file': self.fixture.keys})

    def test_missing_configuration_and_partial_setup_are_not_reported_active(self):
        self.fixture.fixture.config.unlink()
        missing = self.preferences.status()
        self.assertEqual(missing['state'], 'not_configured')
        self.assertFalse(missing['sharing_enabled'])
        self.assertFalse(missing['activation_ready'])
        self.assertIn('native_proposal_policy', missing['remaining_gates'])

    def test_health_reports_native_recall_without_enabling_ownership(self):
        self.fixture.fixture.fixture.remember()
        result = self.preferences.status()
        self.assertEqual(result['state'], 'prepared')
        self.assertEqual(result['native_health'], 'ok')
        self.assertEqual(result['active_facts'], 1)
        self.assertFalse(result['ownership_enabled'])
        self.assertEqual(result['automatic_review'], 'Native LifeOS hooks')
        self.assertFalse(result['proposal_review_available'])

    def test_owner_review_uses_current_native_records_and_strict_tool_arguments(self):
        saved = self.fixture.fixture.fixture.remember()
        result = self.preferences.review('lifeos_memory_search', {'query':'synthetic lab'})
        self.assertEqual(result['results'][0]['reference'], saved['reference'])
        result = self.preferences.review('lifeos_memory_forget', {'reference':saved['reference'], 'request_id':'owner-forget','dry_run':True})
        self.assertEqual(result['status'], 'rejected')
        result = self.preferences.review('lifeos_memory_forget', {'reference':saved['reference'], 'request_id':'owner-forget'})
        self.assertEqual(result['status'], 'committed')
        self.assertEqual(self.preferences.status()['active_facts'], 0)

    def test_owner_previews_and_adopts_native_sources_without_enabling_ownership(self):
        memory = self.fixture.fixture.fixture.memory
        result = memory._native('add',item={'type':'knowledge','entity_type':'research',
                                           'name':'Synthetic owner adoption','content':'Synthetic owner source marker'})
        self.assertTrue(result['ok'],result)
        preview = self.preferences.preview_adoption()
        self.assertEqual(len(preview['records']),1,preview)
        path = preview['records'][0]['path']
        receipt = self.preferences.adopt({'signature':preview['signature'],'projects':{path:'lab'},'request_id':'owner-adoption'})
        self.assertEqual(receipt['status'],'committed',receipt)
        self.assertEqual(self.preferences.review('lifeos_memory_search',{'query':'source marker'})['results'][0]['project'],'lab')
        self.assertFalse(self.preferences.status()['ownership_enabled'])
        with self.assertRaises(ValueError):
            self.preferences.adopt({'signature':preview['signature'],'projects':{},'request_id':'bad','root':'untrusted'})

    def test_sharing_disable_revokes_services_without_deleting_grants_or_facts(self):
        self.fixture.sharing.enroll('reader', sharing_fixture.public_key(52),projects=['lab'],model_route='unknown')
        saved = self.fixture.fixture.fixture.remember()
        self.preferences.sharing(False)
        config = MemoryConfiguration(self.fixture.fixture.config).load()
        self.assertIn('reader', config['clients'])
        self.assertEqual(self.fixture.fixture.service.call_client('reader','lifeos_memory_get',{'reference':saved['reference']})['status'],'rejected')
        self.assertEqual(self.preferences.review('lifeos_memory_get',{'reference':saved['reference']})['status'],'ok')
        with self.assertRaises(ValueError):
            self.preferences.sharing('yes')

    def test_configuration_for_another_installation_is_refused(self):
        config = MemoryConfiguration(self.fixture.fixture.config)
        config.update(lambda value:value.update(root=str(self.fixture.fixture.fixture.root.parent/'other')))
        self.assertEqual(self.preferences.status()['state'],'unavailable')
        with self.assertRaises(RuntimeError):
            self.preferences.sharing(True)

    def test_owner_can_review_and_decide_pending_native_proposals(self):
        from test_memory_proposals import MemoryProposalTests
        fixture = MemoryProposalTests(); fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        config = fixture.fixture.home / 'hermes/lifeos-memory.json'
        MemoryConfiguration(config).save({'version':1,'root':str(fixture.fixture.root),
                                          'principal':'owner','accounts':{},'destinations':{}})
        preferences = MemoryPreferences(config,fixture.fixture.root,
                                        Path('/usr/bin/python3'),Path(__file__).parents[1]/'lifeos_hook_bridge/memory_mcp.py')
        saved = fixture.enqueue()
        self.assertTrue(preferences.status()['proposal_review_available'])
        rows = preferences.review('lifeos_memory_proposals',{})['results']
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]['edit'],fixture.item()['edit'])
        self.assertEqual(rows[0]['reference'],saved['receipt']['proposal_reference'])
        approved = preferences.review('lifeos_memory_decide_proposal',{
            'reference':rows[0]['reference'],'decision':'accept','request_id':'owner-approve'})
        self.assertEqual(approved['status'],'committed',approved)
        self.assertEqual(preferences.review('lifeos_memory_proposals',{})['results'],[])
        self.assertIn(fixture.item()['edit'],fixture.target.read_text())
        stale = preferences.review('lifeos_memory_decide_proposal',{
            'reference':rows[0]['reference'],'decision':'accept','request_id':'owner-again'})
        self.assertEqual(stale['status'],'conflict',stale)

    def test_enrollment_and_revocation_recheck_installation_inside_configuration_update(self):
        for action in ('enroll','revoke'):
            with self.subTest(action=action):
                config = MemoryConfiguration(self.fixture.fixture.config)
                identifier = 'race-' + action
                key = sharing_fixture.public_key(70 if action == 'enroll' else 71)
                config.update(lambda value:value.update(root=str(self.preferences.root)))
                if action == 'revoke':
                    self.preferences.enroll({'client':identifier,'public_key':key,
                                             'projects':['lab'],'model_route':'unknown'})
                checked, proceed = threading.Event(), threading.Event()
                class ObservedPreferences(MemoryPreferences):
                    def _configuration(instance, *, account=None):
                        result = super()._configuration(account=account); checked.set()
                        if not proceed.wait(10):
                            raise RuntimeError('Preference test barrier timed out')
                        return result
                observed = ObservedPreferences(config.path, self.preferences.root,
                                               Path('/usr/bin/python3'), Path(__file__).parents[1]/'lifeos_hook_bridge/memory_mcp.py',
                                               sharing_component=COMPONENT, sharing_options={'keys_file': self.fixture.keys})
                def operation():
                    if action == 'revoke':
                        return observed.revoke(identifier)
                    return observed.enroll({'client':identifier,'public_key':key,
                                            'projects':['lab'],'model_route':'unknown'})
                with ThreadPoolExecutor(max_workers=1) as pool:
                    pending = pool.submit(operation)
                    self.assertTrue(checked.wait(10))
                    config.update(lambda value:value.update(root=str(self.preferences.root.parent/'other')))
                    before, keys = config.load(), self.fixture.keys.read_text()
                    proceed.set()
                    with self.assertRaises(RuntimeError):
                        pending.result(timeout=10)
                self.assertEqual(config.load(),before)
                self.assertEqual(self.fixture.keys.read_text(),keys)

    def test_configuration_mutations_recheck_owner_after_initial_authorization(self):
        account = 'dashboard:basic:synthetic-owner'
        for action in ('sharing', 'enroll', 'revoke'):
            with self.subTest(action=action):
                config = MemoryConfiguration(self.fixture.fixture.config)
                config.update(lambda value: value['accounts'].update({account: value['principal']}))
                identifier = 'owner-race-' + action
                if action == 'revoke':
                    self.preferences.enroll({'client': identifier, 'public_key': sharing_fixture.public_key(81),
                        'projects': ['lab'], 'model_route': 'unknown'}, account=account)
                checked, proceed = threading.Event(), threading.Event()
                class ObservedPreferences(MemoryPreferences):
                    def _configuration(instance, *, account=None):
                        result = super()._configuration(account=account)
                        checked.set()
                        if not proceed.wait(10):
                            raise RuntimeError('Owner authorization test barrier timed out')
                        return result
                observed = ObservedPreferences(config.path, self.preferences.root,
                    Path('/usr/bin/python3'), Path(__file__).parents[1]/'lifeos_hook_bridge/memory_mcp.py',
                    sharing_component=COMPONENT, sharing_options={'keys_file': self.fixture.keys})
                def operation():
                    if action == 'sharing':
                        return observed.sharing(True, account=account)
                    if action == 'revoke':
                        return observed.revoke(identifier, account=account)
                    return observed.enroll({'client': identifier, 'public_key': sharing_fixture.public_key(82),
                        'projects': ['lab'], 'model_route': 'unknown'}, account=account)
                with ThreadPoolExecutor(max_workers=1) as pool:
                    pending = pool.submit(operation)
                    self.assertTrue(checked.wait(10))
                    config.update(lambda value: value['accounts'].pop(account))
                    before, keys = config.load(), self.fixture.keys.read_text()
                    proceed.set()
                    with self.assertRaises(PermissionError):
                        pending.result(timeout=10)
                self.assertEqual(config.load(), before)
                self.assertEqual(self.fixture.keys.read_text(), keys)


if __name__ == '__main__':
    unittest.main()
