     1	# ABOUTME: Tests owner-facing memory status and controls against native synthetic records.
     2	# ABOUTME: Keeps sharing explicit and verifies that diagnostics do not claim unfinished activation.
     3	from pathlib import Path
     4	from concurrent.futures import ThreadPoolExecutor
     5	import threading
     6	import unittest
     7	
     8	from lifeos_hook_bridge.memory_preferences import MemoryPreferences
     9	from lifeos_hook_bridge.memory_service import MemoryConfiguration
    10	import test_memory_sharing as sharing_fixture
    11	
    12	
    13	class MemoryPreferencesTests(unittest.TestCase):
    14	    def setUp(self):
    15	        self.fixture = sharing_fixture.MemorySharingTests(); self.fixture.setUp()
    16	        self.addCleanup(self.fixture.doCleanups)
    17	        self.preferences = MemoryPreferences(self.fixture.fixture.config, self.fixture.fixture.fixture.root,
    18	                                             self.fixture.keys, Path('/usr/bin/python3'),
    19	                                             Path(__file__).parents[1]/'lifeos_hook_bridge/memory_mcp.py')
    20	
    21	    def test_missing_configuration_and_partial_setup_are_not_reported_active(self):
    22	        self.fixture.fixture.config.unlink()
    23	        missing = self.preferences.status()
    24	        self.assertEqual(missing['state'], 'not_configured')
    25	        self.assertFalse(missing['sharing_enabled'])
    26	        self.assertFalse(missing['activation_ready'])
    27	        self.assertIn('native_proposal_policy', missing['remaining_gates'])
    28	
    29	    def test_health_reports_native_recall_without_enabling_ownership(self):
    30	        self.fixture.fixture.fixture.remember()
    31	        result = self.preferences.status()
    32	        self.assertEqual(result['state'], 'prepared')
    33	        self.assertEqual(result['native_health'], 'ok')
    34	        self.assertEqual(result['active_facts'], 1)
    35	        self.assertFalse(result['ownership_enabled'])
    36	        self.assertEqual(result['automatic_review'], 'Native LifeOS hooks')
    37	        self.assertFalse(result['proposal_review_available'])
    38	
    39	    def test_owner_review_uses_current_native_records_and_strict_tool_arguments(self):
    40	        saved = self.fixture.fixture.fixture.remember()
    41	        result = self.preferences.review('lifeos_memory_search', {'query':'synthetic lab'})
    42	        self.assertEqual(result['results'][0]['reference'], saved['reference'])
    43	        result = self.preferences.review('lifeos_memory_forget', {'reference':saved['reference'], 'request_id':'owner-forget','dry_run':True})
    44	        self.assertEqual(result['status'], 'rejected')
    45	        result = self.preferences.review('lifeos_memory_forget', {'reference':saved['reference'], 'request_id':'owner-forget'})
    46	        self.assertEqual(result['status'], 'committed')
    47	        self.assertEqual(self.preferences.status()['active_facts'], 0)
    48	
    49	    def test_owner_previews_and_adopts_native_sources_without_enabling_ownership(self):
    50	        memory = self.fixture.fixture.fixture.memory
    51	        result = memory._native('add',item={'type':'knowledge','entity_type':'research',
    52	                                           'name':'Synthetic owner adoption','content':'Synthetic owner source marker'})
    53	        self.assertTrue(result['ok'],result)
    54	        preview = self.preferences.preview_adoption()
    55	        self.assertEqual(len(preview['records']),1,preview)
    56	        path = preview['records'][0]['path']
    57	        receipt = self.preferences.adopt({'signature':preview['signature'],'projects':{path:'lab'},'request_id':'owner-adoption'})
    58	        self.assertEqual(receipt['status'],'committed',receipt)
    59	        self.assertEqual(self.preferences.review('lifeos_memory_search',{'query':'source marker'})['results'][0]['project'],'lab')
    60	        self.assertFalse(self.preferences.status()['ownership_enabled'])
    61	        with self.assertRaises(ValueError):
    62	            self.preferences.adopt({'signature':preview['signature'],'projects':{},'request_id':'bad','root':'untrusted'})
    63	
    64	    def test_sharing_disable_revokes_services_without_deleting_grants_or_facts(self):
    65	        self.fixture.sharing.enroll('reader', sharing_fixture.public_key(52),projects=['lab'],model_route='unknown')
    66	        saved = self.fixture.fixture.fixture.remember()
    67	        self.preferences.sharing(False)
    68	        config = MemoryConfiguration(self.fixture.fixture.config).load()
    69	        self.assertIn('reader', config['clients'])
    70	        self.assertEqual(self.fixture.fixture.service.call_client('reader','lifeos_memory_get',{'reference':saved['reference']})['status'],'rejected')
    71	        self.assertEqual(self.preferences.review('lifeos_memory_get',{'reference':saved['reference']})['status'],'ok')
    72	        with self.assertRaises(ValueError):
    73	            self.preferences.sharing('yes')
    74	
    75	    def test_configuration_for_another_installation_is_refused(self):
    76	        config = MemoryConfiguration(self.fixture.fixture.config)
    77	        config.update(lambda value:value.update(root=str(self.fixture.fixture.fixture.root.parent/'other')))
    78	        self.assertEqual(self.preferences.status()['state'],'unavailable')
    79	        with self.assertRaises(RuntimeError):
    80	            self.preferences.sharing(True)
    81	
    82	    def test_owner_can_review_and_decide_pending_native_proposals(self):
    83	        from test_memory_proposals import MemoryProposalTests
    84	        fixture = MemoryProposalTests(); fixture.setUp()
    85	        self.addCleanup(fixture.doCleanups)
    86	        config = fixture.fixture.home / 'hermes/lifeos-memory.json'
    87	        MemoryConfiguration(config).save({'version':1,'root':str(fixture.fixture.root),
    88	                                          'principal':'owner','accounts':{},'destinations':{}})
    89	        preferences = MemoryPreferences(config,fixture.fixture.root,fixture.fixture.home/'keys',
    90	                                        Path('/usr/bin/python3'),Path(__file__).parents[1]/'lifeos_hook_bridge/memory_mcp.py')
    91	        saved = fixture.enqueue()
    92	        self.assertTrue(preferences.status()['proposal_review_available'])
    93	        rows = preferences.review('lifeos_memory_proposals',{})['results']
    94	        self.assertEqual(len(rows),1)
    95	        self.assertEqual(rows[0]['edit'],fixture.item()['edit'])
    96	        self.assertEqual(rows[0]['reference'],saved['receipt']['proposal_reference'])
    97	        approved = preferences.review('lifeos_memory_decide_proposal',{
    98	            'reference':rows[0]['reference'],'decision':'accept','request_id':'owner-approve'})
    99	        self.assertEqual(approved['status'],'committed',approved)
   100	        self.assertEqual(preferences.review('lifeos_memory_proposals',{})['results'],[])
   101	        self.assertIn(fixture.item()['edit'],fixture.target.read_text())
   102	        stale = preferences.review('lifeos_memory_decide_proposal',{
   103	            'reference':rows[0]['reference'],'decision':'accept','request_id':'owner-again'})
   104	        self.assertEqual(stale['status'],'conflict',stale)
   105	
   106	    def test_enrollment_and_revocation_recheck_installation_inside_configuration_update(self):
   107	        for action in ('enroll','revoke'):
   108	            with self.subTest(action=action):
   109	                config = MemoryConfiguration(self.fixture.fixture.config)
   110	                identifier = 'race-' + action
   111	                key = sharing_fixture.public_key(70 if action == 'enroll' else 71)
   112	                config.update(lambda value:value.update(root=str(self.preferences.root)))
   113	                if action == 'revoke':
   114	                    self.preferences.enroll({'client':identifier,'public_key':key,
   115	                                             'projects':['lab'],'model_route':'unknown'})
   116	                checked, proceed = threading.Event(), threading.Event()
   117	                class ObservedPreferences(MemoryPreferences):
   118	                    def _configuration(instance, *, account=None):
   119	                        result = super()._configuration(account=account); checked.set()
   120	                        if not proceed.wait(10):
   121	                            raise RuntimeError('Preference test barrier timed out')
   122	                        return result
   123	                observed = ObservedPreferences(config.path,self.preferences.root,self.fixture.keys,
   124	                                               Path('/usr/bin/python3'),Path(__file__).parents[1]/'lifeos_hook_bridge/memory_mcp.py')
   125	                def operation():
   126	                    if action == 'revoke':
   127	                        return observed.revoke(identifier)
   128	                    return observed.enroll({'client':identifier,'public_key':key,
   129	                                            'projects':['lab'],'model_route':'unknown'})
   130	                with ThreadPoolExecutor(max_workers=1) as pool:
   131	                    pending = pool.submit(operation)
   132	                    self.assertTrue(checked.wait(10))
   133	                    config.update(lambda value:value.update(root=str(self.preferences.root.parent/'other')))
   134	                    before, keys = config.load(), self.fixture.keys.read_text()
   135	                    proceed.set()
   136	                    with self.assertRaises(RuntimeError):
   137	                        pending.result(timeout=10)
   138	                self.assertEqual(config.load(),before)
   139	                self.assertEqual(self.fixture.keys.read_text(),keys)
   140	
   141	    def test_configuration_mutations_recheck_owner_after_initial_authorization(self):
   142	        account = 'dashboard:basic:synthetic-owner'
   143	        for action in ('sharing', 'enroll', 'revoke'):
   144	            with self.subTest(action=action):
   145	                config = MemoryConfiguration(self.fixture.fixture.config)
   146	                config.update(lambda value: value['accounts'].update({account: value['principal']}))
   147	                identifier = 'owner-race-' + action
   148	                if action == 'revoke':
   149	                    self.preferences.enroll({'client': identifier, 'public_key': sharing_fixture.public_key(81),
   150	                        'projects': ['lab'], 'model_route': 'unknown'}, account=account)
   151	                checked, proceed = threading.Event(), threading.Event()
   152	                class ObservedPreferences(MemoryPreferences):
   153	                    def _configuration(instance, *, account=None):
   154	                        result = super()._configuration(account=account)
   155	                        checked.set()
   156	                        if not proceed.wait(10):
   157	                            raise RuntimeError('Owner authorization test barrier timed out')
   158	                        return result
   159	                observed = ObservedPreferences(config.path, self.preferences.root, self.fixture.keys,
   160	                    Path('/usr/bin/python3'), Path(__file__).parents[1] / 'lifeos_hook_bridge/memory_mcp.py')
   161	                def operation():
   162	                    if action == 'sharing':
   163	                        return observed.sharing(True, account=account)
   164	                    if action == 'revoke':
   165	                        return observed.revoke(identifier, account=account)
   166	                    return observed.enroll({'client': identifier, 'public_key': sharing_fixture.public_key(82),
   167	                        'projects': ['lab'], 'model_route': 'unknown'}, account=account)
   168	                with ThreadPoolExecutor(max_workers=1) as pool:
   169	                    pending = pool.submit(operation)
   170	                    self.assertTrue(checked.wait(10))
   171	                    config.update(lambda value: value['accounts'].pop(account))
   172	                    before, keys = config.load(), self.fixture.keys.read_text()
   173	                    proceed.set()
   174	                    with self.assertRaises(PermissionError):
   175	                        pending.result(timeout=10)
   176	                self.assertEqual(config.load(), before)
   177	                self.assertEqual(self.fixture.keys.read_text(), keys)
   178	
   179	
   180	if __name__ == '__main__':
   181	    unittest.main()
