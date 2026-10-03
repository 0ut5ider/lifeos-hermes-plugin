     1	# ABOUTME: Tests previewed adoption of native facts, learning notes, and pending proposals.
     2	# ABOUTME: Uses real LifeOS files and refuses stale previews or forgotten source reactivation.
     3	from pathlib import Path
     4	import os
     5	import subprocess
     6	import sys
     7	import unittest
     8	
     9	import test_memory_proposals as proposal_fixture
    10	import test_memory_native as native_fixture
    11	
    12	
    13	class MemoryAdoptionTests(unittest.TestCase):
    14	    def setUp(self):
    15	        self.fixture = proposal_fixture.MemoryProposalTests(); self.fixture.setUp()
    16	        self.addCleanup(self.fixture.doCleanups)
    17	        self.memory = self.fixture.memory
    18	        self.scope = self.fixture.scope
    19	
    20	    def native_note(self, content='Synthetic native project marker', name='Synthetic native note'):
    21	        result = self.memory._native('add',item={'type':'knowledge','entity_type':'research','name':name,'content':content})
    22	        self.assertTrue(result['ok'],result)
    23	        return Path(result['path'])
    24	
    25	    def test_adoption_keeps_native_files_and_truthful_unknown_provenance(self):
    26	        note = self.native_note()
    27	        self.memory._native('add',item={'type':'memory','actor':'principal','content':'RULE: adopted native owner marker'})
    28	        before = note.read_bytes()
    29	        preview = self.memory.preview_adoption(self.scope)
    30	        self.assertEqual(len(preview['records']),2,preview)
    31	        self.assertEqual(self.memory.recall(self.scope,'marker'),[])
    32	        receipt = self.memory.adopt(self.scope,preview['signature'],{},'adopt-once')
    33	        self.assertEqual(receipt['status'],'committed',receipt)
    34	        self.assertEqual(receipt['facts_adopted'],2)
    35	        found = self.memory.recall(self.scope,'marker')
    36	        self.assertEqual(len(found),2)
    37	        self.assertTrue(all(row['writer']=='native:unattributed' for row in found),found)
    38	        self.assertEqual(note.read_bytes(),before)
    39	        self.assertEqual(receipt,self.memory.adopt(self.scope,preview['signature'],{},'adopt-once'))
    40	        self.assertEqual(self.memory.preview_adoption(self.scope)['records'],[])
    41	
    42	    def test_unknown_native_project_assignment_is_private_until_owner_classifies_it(self):
    43	        note = self.native_note()
    44	        preview = self.memory.preview_adoption(self.scope)
    45	        self.memory.adopt(self.scope,preview['signature'],{},'unclassified')
    46	        self.assertEqual(self.memory.recall(native_fixture.READER,'marker'),[])
    47	        second = self.native_note('Synthetic explicitly classified project marker','Classified native note')
    48	        preview = self.memory.preview_adoption(self.scope)
    49	        receipt = self.memory.adopt(self.scope,preview['signature'],{second.relative_to(self.memory.root).as_posix():'lab'},'classified')
    50	        self.assertEqual(receipt['status'],'committed',receipt)
    51	        found = self.memory.recall(native_fixture.READER,'classified project marker')
    52	        self.assertEqual(len(found),1)
    53	        self.assertEqual(found[0]['project'],'lab')
    54	        self.assertNotEqual(found[0]['source']['path'],note.relative_to(self.memory.root).as_posix())
    55	
    56	    def test_stale_preview_never_indexes_changed_native_content(self):
    57	        note = self.native_note()
    58	        preview = self.memory.preview_adoption(self.scope)
    59	        note.write_text(note.read_text()+'\nUnreviewed synthetic additional marker\n')
    60	        result = self.memory.adopt(self.scope,preview['signature'],{},'stale')
    61	        self.assertEqual(result['status'],'conflict',result)
    62	        self.assertEqual(self.memory.recall(self.scope,'marker'),[])
    63	
    64	    def test_adoption_does_not_reactivate_forgotten_native_sections(self):
    65	        self.native_note()
    66	        preview = self.memory.preview_adoption(self.scope)
    67	        self.memory.adopt(self.scope,preview['signature'],{},'first-adopt')
    68	        fact = self.memory.recall(self.scope,'marker')[0]
    69	        self.memory.forget(self.scope,fact['reference'],'forget-native')
    70	        preview = self.memory.preview_adoption(self.scope)
    71	        result = self.memory.adopt(self.scope,preview['signature'],{},'later-adopt')
    72	        self.assertEqual(result['facts_adopted'],0,result)
    73	        self.assertEqual(self.memory.recall(self.scope,'marker'),[])
    74	
    75	    def test_pending_native_proposal_adoption_preserves_approval_checks(self):
    76	        native = self.memory._native('add',item=self.fixture.item())
    77	        self.assertTrue(native['ok'],native)
    78	        preview = self.memory.preview_adoption(self.scope)
    79	        self.assertEqual(len(preview['proposals']),1,preview)
    80	        result = self.memory.adopt(self.scope,preview['signature'],{},'adopt-queue')
    81	        self.assertEqual(result['proposals_adopted'],1,result)
    82	        row = self.memory.review_proposals(self.scope)[0]
    83	        self.assertEqual(row['writer'],'native:unattributed')
    84	        approved = self.memory.decide_proposal(self.scope,row['reference'],'accept','adopted-accept')
    85	        self.assertEqual(approved['status'],'committed',approved)
    86	        self.assertIn(self.fixture.item()['edit'],self.fixture.target.read_text())
    87	
    88	    def test_learning_notes_remain_historical_and_can_be_corrected(self):
    89	        note = self.memory.root / 'LIFEOS/MEMORY/LEARNING/SYSTEM/2026-09/synthetic.md'
    90	        note.parent.mkdir(parents=True)
    91	        note.write_text('---\ntype: learning\ntitle: Synthetic learning\n---\nHistorical synthetic learning marker\n')
    92	        preview = self.memory.preview_adoption(self.scope)
    93	        self.memory.adopt(self.scope,preview['signature'],{},'adopt-learning')
    94	        found = self.memory.recall(self.scope,'learning marker')[0]
    95	        self.assertEqual(found['status'],'historical',found)
    96	        self.assertEqual(found['source']['kind'],'learning')
    97	        self.assertEqual(self.memory.recall(native_fixture.READER,'learning marker'),[])
    98	        context = self.memory.relevant_context(self.scope,'learning marker',{'threshold':0})
    99	        self.assertIn('historical',context['markdownBlock'])
   100	        corrected = self.memory.correct(self.scope,found['reference'],'Corrected synthetic learning marker','correct-learning')
   101	        self.assertEqual(corrected['status'],'committed',corrected)
   102	        current = self.memory.recall(self.scope,'learning marker')
   103	        self.assertEqual(len(current),1,current)
   104	        self.assertEqual(current[0]['status'],'active')
   105	        self.assertEqual(current[0]['content'],'Corrected synthetic learning marker')
   106	        self.assertIn('Historical',note.read_text())
   107	
   108	    def test_restricted_reader_cannot_adopt_or_preview_owner_sources(self):
   109	        self.native_note()
   110	        with self.assertRaisesRegex(RuntimeError,'owner'):
   111	            self.memory.preview_adoption(native_fixture.READER)
   112	        result = self.memory.adopt(native_fixture.READER,'unverified',{},'reader-adopt')
   113	        self.assertEqual(result['status'],'rejected',result)
   114	
   115	    def test_private_markup_and_invalid_native_notes_are_excluded_from_preview(self):
   116	        note = self.memory.root / 'LIFEOS/MEMORY/LEARNING/SYSTEM/2026-09/private.md'
   117	        note.parent.mkdir(parents=True)
   118	        note.write_text('<private>PRIVATE-NATIVE-MARKER</private>\n')
   119	        preview = self.memory.preview_adoption(self.scope)
   120	        self.assertEqual(preview['records'],[])
   121	        self.assertEqual(len(preview['excluded']),1,preview)
   122	        self.assertNotIn('PRIVATE-NATIVE-MARKER',str(preview))
   123	
   124	    def test_learning_body_reference_excludes_frontmatter_and_preserves_spaces(self):
   125	        for name, text, expected in (
   126	            ('duplicate','---\ntype: learning\ntitle: Synthetic repeated title marker\n---\nSynthetic repeated title marker\n','Synthetic repeated title marker'),
   127	            ('spaces','Synthetic trailing whitespace marker   \n','Synthetic trailing whitespace marker   '),
   128	        ):
   129	            with self.subTest(name=name):
   130	                note = self.memory.root/f'LIFEOS/MEMORY/LEARNING/SYSTEM/2026-09/{name}.md'
   131	                note.parent.mkdir(parents=True,exist_ok=True); note.write_text(text)
   132	                preview = self.memory.preview_adoption(self.scope)
   133	                receipt = self.memory.adopt(self.scope,preview['signature'],{},name)
   134	                self.assertEqual(receipt['status'],'committed',receipt)
   135	                found = self.memory.recall(self.scope,'marker')
   136	                self.assertTrue(any(row['content']==expected for row in found),found)
   137	                reference = next(row['reference'] for row in found if row['content']==expected)
   138	                self.assertEqual(self.memory.get(self.scope,reference)['content'],expected)
   139	
   140	    def test_source_mtime_changes_cannot_adopt_unpreviewed_learning(self):
   141	        note = self.memory.root/'LIFEOS/MEMORY/LEARNING/SYSTEM/2026-09/old.md'
   142	        note.parent.mkdir(parents=True); note.write_text('Synthetic unrelated learning marker\n')
   143	        os.utime(note,(1,1))
   144	        saved = self.memory.remember(self.scope,category='principal',content='RULE: Synthetic retired unrelated preference',
   145	                                    title='',project='',request_id='retired-preference')
   146	        self.memory.forget(self.scope,saved['reference'],'forget-preference')
   147	        preview = self.memory.preview_adoption(self.scope)
   148	        self.assertEqual(preview['records'],[])
   149	        import time
   150	        os.utime(note,(time.time()+100,time.time()+100))
   151	        receipt = self.memory.adopt(self.scope,preview['signature'],{},'changed-mtime')
   152	        self.assertEqual(receipt['status'],'conflict',receipt)
   153	        self.assertEqual(self.memory.recall(self.scope,'unrelated learning'),[])
   154	
   155	    def test_hot_quotation_of_forgotten_claim_is_not_adopted(self):
   156	        saved = self.memory.remember(self.scope,category='principal',content='RULE: Synthetic retired routing port 8123',
   157	                                    title='',project='',request_id='retired-hot')
   158	        self.memory.forget(self.scope,saved['reference'],'forget-hot')
   159	        self.memory._native('add',item={'type':'memory','actor':'principal',
   160	                                      'content':'RULE: Historical note says Synthetic retired routing port 8123 in retained history.'})
   161	        preview = self.memory.preview_adoption(self.scope)
   162	        self.assertEqual(preview['records'],[],preview)
   163	        self.assertTrue(preview['excluded'])
   164	
   165	    def test_discovery_does_not_drop_learning_notes_after_hot_limit(self):
   166	        notes = self.memory.root / 'LIFEOS/MEMORY/LEARNING/SYSTEM/2026-09'
   167	        notes.mkdir(parents=True)
   168	        for number in range(501):
   169	            (notes / f'{number:04}.md').write_text(f'Synthetic collection learning marker {number}\n')
   170	        environment = dict(os.environ, HOME=str(self.memory.root.parent),
   171	                           LIFEOS_DIR=str(self.memory.root/'LIFEOS'), LIFEOS_MEMORY_INTERNAL='1')
   172	        script = "const m=await import(process.argv[1]); console.log(m.discoverAllItems().filter(n=>n.noteClass==='learning').length)"
   173	        result = subprocess.run(['bun','--no-install','-e',script,str(self.memory.root/'LIFEOS/TOOLS/MemoryRetriever.ts')],
   174	                                env=environment,capture_output=True,text=True,check=True)
   175	        self.assertEqual(result.stdout.strip(),'500')
   176	        preview = self.memory.preview_adoption(self.scope)
   177	        self.assertEqual(len(preview['records']),501)
   178	        receipt = self.memory.adopt(self.scope,preview['signature'],{},'whole-learning-tree')
   179	        self.assertEqual(receipt['facts_adopted'],501,receipt)
   180	
   181	    def test_native_appended_sections_have_distinct_stable_references(self):
   182	        self.native_note('Synthetic first section marker')
   183	        self.native_note('Synthetic second section marker')
   184	        preview = self.memory.preview_adoption(self.scope)
   185	        self.assertEqual(len(preview['records']),2,preview)
   186	        self.memory.adopt(self.scope,preview['signature'],{},'sections')
   187	        found = self.memory.recall(self.scope,'section marker')
   188	        self.assertEqual(len(found),2,found)
   189	        first = next(row for row in found if 'first' in row['content'])
   190	        result = self.memory.correct(self.scope,first['reference'],'Synthetic corrected section marker','correct-section')
   191	        self.assertEqual(result['status'],'committed',result)
   192	        found = self.memory.recall(self.scope,'section marker')
   193	        self.assertEqual({row['content'] for row in found},{'Synthetic corrected section marker','Synthetic second section marker'})
   194	
   195	    def test_wrapped_forgotten_claim_cannot_return_through_archive_adoption(self):
   196	        saved = self.memory.remember(self.scope,category='project',content='Synthetic retired routing port 8123',
   197	                                     title='Removed route',project='lab',request_id='route')
   198	        self.memory.forget(self.scope,saved['reference'],'forget-route')
   199	        self.native_note('Summary contains Synthetic retired routing port 8123 in retained history.','Wrapped quotation')
   200	        preview = self.memory.preview_adoption(self.scope)
   201	        self.assertEqual(preview['records'],[],preview)
   202	        self.assertTrue(preview['excluded'])
   203	
   204	    def test_malformed_hot_markers_are_reported_without_exposing_entries(self):
   205	        path = self.memory.root/'LIFEOS/USER/PRINCIPAL/PRINCIPAL_MEMORY.md'
   206	        path.write_text('RULE: synthetic unbounded hot entry\n')
   207	        preview = self.memory.preview_adoption(self.scope)
   208	        self.assertEqual(preview['records'],[],preview)
   209	        self.assertTrue(any(row['path'].endswith('PRINCIPAL_MEMORY.md') for row in preview['excluded']),preview)
   210	
   211	    def test_learning_correction_recovers_new_destination_after_process_interruption(self):
   212	        note = self.memory.root/'LIFEOS/MEMORY/LEARNING/SYSTEM/2026-09/recovery.md'
   213	        note.parent.mkdir(parents=True)
   214	        note.write_text('Synthetic historical recovery marker\n')
   215	        preview = self.memory.preview_adoption(self.scope)
   216	        self.memory.adopt(self.scope,preview['signature'],{},'adopt-recovery')
   217	        reference = self.memory.recall(self.scope,'recovery marker')[0]['reference']
   218	        script = """import os,sys,json
   219	from pathlib import Path
   220	sys.path.insert(0,str(Path.cwd()/'tests'))
   221	from test_memory_native import OWNER
   222	from lifeos_hook_bridge.memory_access import NativeMemory
   223	memory=NativeMemory(Path(sys.argv[1]))
   224	def interrupt(*args,**kwargs): os._exit(73)
   225	memory._record=interrupt
   226	memory.correct(OWNER,json.loads(sys.argv[2]),'Synthetic corrected recovery marker','recovery-correction')
   227	"""
   228	        import json
   229	        child = subprocess.run([sys.executable,'-c',script,str(self.memory.root),json.dumps(reference)],
   230	                               capture_output=True,text=True)
   231	        self.assertEqual(child.returncode,73,child.stderr)
   232	        research = self.memory.root/'LIFEOS/MEMORY/KNOWLEDGE/Research'
   233	        self.assertEqual(len(list(research.glob('*.md'))),1)
   234	        self.assertEqual(self.memory.recall(self.scope,'recovery marker')[0]['content'],'Synthetic historical recovery marker')
   235	        self.assertEqual(list(research.glob('*.md')),[])
   236	        receipt = self.memory.correct(self.scope,reference,'Synthetic corrected recovery marker','recovery-correction')
   237	        self.assertEqual(receipt['status'],'committed',receipt)
   238	
   239	
   240	if __name__ == '__main__':
   241	    unittest.main()
