# ABOUTME: Tests previewed adoption of native facts, learning notes, and pending proposals.
# ABOUTME: Uses real LifeOS files and refuses stale previews or forgotten source reactivation.
from pathlib import Path
import os
import subprocess
import sys
import unittest

import test_memory_proposals as proposal_fixture
import test_memory_native as native_fixture


class MemoryAdoptionTests(unittest.TestCase):
    def setUp(self):
        self.fixture = proposal_fixture.MemoryProposalTests(); self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.memory = self.fixture.memory
        self.scope = self.fixture.scope

    def native_note(self, content='Synthetic native project marker', name='Synthetic native note'):
        result = self.memory._native('add',item={'type':'knowledge','entity_type':'research','name':name,'content':content})
        self.assertTrue(result['ok'],result)
        return Path(result['path'])

    def test_adoption_keeps_native_files_and_truthful_unknown_provenance(self):
        note = self.native_note()
        self.memory._native('add',item={'type':'memory','actor':'principal','content':'RULE: adopted native owner marker'})
        before = note.read_bytes()
        preview = self.memory.preview_adoption(self.scope)
        self.assertEqual(len(preview['records']),2,preview)
        self.assertEqual(self.memory.recall(self.scope,'marker'),[])
        receipt = self.memory.adopt(self.scope,preview['signature'],{},'adopt-once')
        self.assertEqual(receipt['status'],'committed',receipt)
        self.assertEqual(receipt['facts_adopted'],2)
        found = self.memory.recall(self.scope,'marker')
        self.assertEqual(len(found),2)
        self.assertTrue(all(row['writer']=='native:unattributed' for row in found),found)
        self.assertEqual(note.read_bytes(),before)
        self.assertEqual(receipt,self.memory.adopt(self.scope,preview['signature'],{},'adopt-once'))
        self.assertEqual(self.memory.preview_adoption(self.scope)['records'],[])

    def test_unknown_native_project_assignment_is_private_until_owner_classifies_it(self):
        note = self.native_note()
        preview = self.memory.preview_adoption(self.scope)
        self.memory.adopt(self.scope,preview['signature'],{},'unclassified')
        self.assertEqual(self.memory.recall(native_fixture.READER,'marker'),[])
        second = self.native_note('Synthetic explicitly classified project marker','Classified native note')
        preview = self.memory.preview_adoption(self.scope)
        receipt = self.memory.adopt(self.scope,preview['signature'],{second.relative_to(self.memory.root).as_posix():'lab'},'classified')
        self.assertEqual(receipt['status'],'committed',receipt)
        found = self.memory.recall(native_fixture.READER,'classified project marker')
        self.assertEqual(len(found),1)
        self.assertEqual(found[0]['project'],'lab')
        self.assertNotEqual(found[0]['source']['path'],note.relative_to(self.memory.root).as_posix())

    def test_stale_preview_never_indexes_changed_native_content(self):
        note = self.native_note()
        preview = self.memory.preview_adoption(self.scope)
        note.write_text(note.read_text()+'\nUnreviewed synthetic additional marker\n')
        result = self.memory.adopt(self.scope,preview['signature'],{},'stale')
        self.assertEqual(result['status'],'conflict',result)
        self.assertEqual(self.memory.recall(self.scope,'marker'),[])

    def test_adoption_does_not_reactivate_forgotten_native_sections(self):
        self.native_note()
        preview = self.memory.preview_adoption(self.scope)
        self.memory.adopt(self.scope,preview['signature'],{},'first-adopt')
        fact = self.memory.recall(self.scope,'marker')[0]
        self.memory.forget(self.scope,fact['reference'],'forget-native')
        preview = self.memory.preview_adoption(self.scope)
        result = self.memory.adopt(self.scope,preview['signature'],{},'later-adopt')
        self.assertEqual(result['facts_adopted'],0,result)
        self.assertEqual(self.memory.recall(self.scope,'marker'),[])

    def test_pending_native_proposal_adoption_preserves_approval_checks(self):
        native = self.memory._native('add',item=self.fixture.item())
        self.assertTrue(native['ok'],native)
        preview = self.memory.preview_adoption(self.scope)
        self.assertEqual(len(preview['proposals']),1,preview)
        result = self.memory.adopt(self.scope,preview['signature'],{},'adopt-queue')
        self.assertEqual(result['proposals_adopted'],1,result)
        row = self.memory.review_proposals(self.scope)[0]
        self.assertEqual(row['writer'],'native:unattributed')
        approved = self.memory.decide_proposal(self.scope,row['reference'],'accept','adopted-accept')
        self.assertEqual(approved['status'],'committed',approved)
        self.assertIn(self.fixture.item()['edit'],self.fixture.target.read_text())

    def test_learning_notes_remain_historical_and_can_be_corrected(self):
        note = self.memory.root / 'LIFEOS/MEMORY/LEARNING/SYSTEM/2026-09/synthetic.md'
        note.parent.mkdir(parents=True)
        note.write_text('---\ntype: learning\ntitle: Synthetic learning\n---\nHistorical synthetic learning marker\n')
        preview = self.memory.preview_adoption(self.scope)
        self.memory.adopt(self.scope,preview['signature'],{},'adopt-learning')
        found = self.memory.recall(self.scope,'learning marker')[0]
        self.assertEqual(found['status'],'historical',found)
        self.assertEqual(found['source']['kind'],'learning')
        self.assertEqual(self.memory.recall(native_fixture.READER,'learning marker'),[])
        context = self.memory.relevant_context(self.scope,'learning marker',{'threshold':0})
        self.assertIn('historical',context['markdownBlock'])
        corrected = self.memory.correct(self.scope,found['reference'],'Corrected synthetic learning marker','correct-learning')
        self.assertEqual(corrected['status'],'committed',corrected)
        current = self.memory.recall(self.scope,'learning marker')
        self.assertEqual(len(current),1,current)
        self.assertEqual(current[0]['status'],'active')
        self.assertEqual(current[0]['content'],'Corrected synthetic learning marker')
        self.assertIn('Historical',note.read_text())

    def test_restricted_reader_cannot_adopt_or_preview_owner_sources(self):
        self.native_note()
        with self.assertRaisesRegex(RuntimeError,'owner'):
            self.memory.preview_adoption(native_fixture.READER)
        result = self.memory.adopt(native_fixture.READER,'unverified',{},'reader-adopt')
        self.assertEqual(result['status'],'rejected',result)

    def test_private_markup_and_invalid_native_notes_are_excluded_from_preview(self):
        note = self.memory.root / 'LIFEOS/MEMORY/LEARNING/SYSTEM/2026-09/private.md'
        note.parent.mkdir(parents=True)
        note.write_text('<private>PRIVATE-NATIVE-MARKER</private>\n')
        preview = self.memory.preview_adoption(self.scope)
        self.assertEqual(preview['records'],[])
        self.assertEqual(len(preview['excluded']),1,preview)
        self.assertNotIn('PRIVATE-NATIVE-MARKER',str(preview))

    def test_learning_body_reference_excludes_frontmatter_and_preserves_spaces(self):
        for name, text, expected in (
            ('duplicate','---\ntype: learning\ntitle: Synthetic repeated title marker\n---\nSynthetic repeated title marker\n','Synthetic repeated title marker'),
            ('spaces','Synthetic trailing whitespace marker   \n','Synthetic trailing whitespace marker   '),
        ):
            with self.subTest(name=name):
                note = self.memory.root/f'LIFEOS/MEMORY/LEARNING/SYSTEM/2026-09/{name}.md'
                note.parent.mkdir(parents=True,exist_ok=True); note.write_text(text)
                preview = self.memory.preview_adoption(self.scope)
                receipt = self.memory.adopt(self.scope,preview['signature'],{},name)
                self.assertEqual(receipt['status'],'committed',receipt)
                found = self.memory.recall(self.scope,'marker')
                self.assertTrue(any(row['content']==expected for row in found),found)
                reference = next(row['reference'] for row in found if row['content']==expected)
                self.assertEqual(self.memory.get(self.scope,reference)['content'],expected)

    def test_source_mtime_changes_cannot_adopt_unpreviewed_learning(self):
        note = self.memory.root/'LIFEOS/MEMORY/LEARNING/SYSTEM/2026-09/old.md'
        note.parent.mkdir(parents=True); note.write_text('Synthetic unrelated learning marker\n')
        os.utime(note,(1,1))
        saved = self.memory.remember(self.scope,category='principal',content='RULE: Synthetic retired unrelated preference',
                                    title='',project='',request_id='retired-preference')
        self.memory.forget(self.scope,saved['reference'],'forget-preference')
        preview = self.memory.preview_adoption(self.scope)
        self.assertEqual(preview['records'],[])
        import time
        os.utime(note,(time.time()+100,time.time()+100))
        receipt = self.memory.adopt(self.scope,preview['signature'],{},'changed-mtime')
        self.assertEqual(receipt['status'],'conflict',receipt)
        self.assertEqual(self.memory.recall(self.scope,'unrelated learning'),[])

    def test_hot_quotation_of_forgotten_claim_is_not_adopted(self):
        saved = self.memory.remember(self.scope,category='principal',content='RULE: Synthetic retired routing port 8123',
                                    title='',project='',request_id='retired-hot')
        self.memory.forget(self.scope,saved['reference'],'forget-hot')
        self.memory._native('add',item={'type':'memory','actor':'principal',
                                      'content':'RULE: Historical note says Synthetic retired routing port 8123 in retained history.'})
        preview = self.memory.preview_adoption(self.scope)
        self.assertEqual(preview['records'],[],preview)
        self.assertTrue(preview['excluded'])

    def test_discovery_does_not_drop_learning_notes_after_hot_limit(self):
        notes = self.memory.root / 'LIFEOS/MEMORY/LEARNING/SYSTEM/2026-09'
        notes.mkdir(parents=True)
        for number in range(501):
            (notes / f'{number:04}.md').write_text(f'Synthetic collection learning marker {number}\n')
        environment = dict(os.environ, HOME=str(self.memory.root.parent),
                           LIFEOS_DIR=str(self.memory.root/'LIFEOS'), LIFEOS_MEMORY_INTERNAL='1')
        script = "const m=await import(process.argv[1]); console.log(m.discoverAllItems().filter(n=>n.noteClass==='learning').length)"
        result = subprocess.run(['bun','--no-install','-e',script,str(self.memory.root/'LIFEOS/TOOLS/MemoryRetriever.ts')],
                                env=environment,capture_output=True,text=True,check=True)
        self.assertEqual(result.stdout.strip(),'500')
        preview = self.memory.preview_adoption(self.scope)
        self.assertEqual(len(preview['records']),501)
        receipt = self.memory.adopt(self.scope,preview['signature'],{},'whole-learning-tree')
        self.assertEqual(receipt['facts_adopted'],501,receipt)

    def test_native_appended_sections_have_distinct_stable_references(self):
        self.native_note('Synthetic first section marker')
        self.native_note('Synthetic second section marker')
        preview = self.memory.preview_adoption(self.scope)
        self.assertEqual(len(preview['records']),2,preview)
        self.memory.adopt(self.scope,preview['signature'],{},'sections')
        found = self.memory.recall(self.scope,'section marker')
        self.assertEqual(len(found),2,found)
        first = next(row for row in found if 'first' in row['content'])
        result = self.memory.correct(self.scope,first['reference'],'Synthetic corrected section marker','correct-section')
        self.assertEqual(result['status'],'committed',result)
        found = self.memory.recall(self.scope,'section marker')
        self.assertEqual({row['content'] for row in found},{'Synthetic corrected section marker','Synthetic second section marker'})

    def test_wrapped_forgotten_claim_cannot_return_through_archive_adoption(self):
        saved = self.memory.remember(self.scope,category='project',content='Synthetic retired routing port 8123',
                                     title='Removed route',project='lab',request_id='route')
        self.memory.forget(self.scope,saved['reference'],'forget-route')
        self.native_note('Summary contains Synthetic retired routing port 8123 in retained history.','Wrapped quotation')
        preview = self.memory.preview_adoption(self.scope)
        self.assertEqual(preview['records'],[],preview)
        self.assertTrue(preview['excluded'])

    def test_malformed_hot_markers_are_reported_without_exposing_entries(self):
        path = self.memory.root/'LIFEOS/USER/PRINCIPAL/PRINCIPAL_MEMORY.md'
        path.write_text('RULE: synthetic unbounded hot entry\n')
        preview = self.memory.preview_adoption(self.scope)
        self.assertEqual(preview['records'],[],preview)
        self.assertTrue(any(row['path'].endswith('PRINCIPAL_MEMORY.md') for row in preview['excluded']),preview)

    def test_learning_correction_recovers_new_destination_after_process_interruption(self):
        note = self.memory.root/'LIFEOS/MEMORY/LEARNING/SYSTEM/2026-09/recovery.md'
        note.parent.mkdir(parents=True)
        note.write_text('Synthetic historical recovery marker\n')
        preview = self.memory.preview_adoption(self.scope)
        self.memory.adopt(self.scope,preview['signature'],{},'adopt-recovery')
        reference = self.memory.recall(self.scope,'recovery marker')[0]['reference']
        script = """import os,sys,json
from pathlib import Path
sys.path.insert(0,str(Path.cwd()/'tests'))
from test_memory_native import OWNER
from lifeos_hook_bridge.memory_access import NativeMemory
memory=NativeMemory(Path(sys.argv[1]))
def interrupt(*args,**kwargs): os._exit(73)
memory._record=interrupt
memory.correct(OWNER,json.loads(sys.argv[2]),'Synthetic corrected recovery marker','recovery-correction')
"""
        import json
        child = subprocess.run([sys.executable,'-c',script,str(self.memory.root),json.dumps(reference)],
                               capture_output=True,text=True)
        self.assertEqual(child.returncode,73,child.stderr)
        research = self.memory.root/'LIFEOS/MEMORY/KNOWLEDGE/Research'
        self.assertEqual(len(list(research.glob('*.md'))),1)
        self.assertEqual(self.memory.recall(self.scope,'recovery marker')[0]['content'],'Synthetic historical recovery marker')
        self.assertEqual(list(research.glob('*.md')),[])
        receipt = self.memory.correct(self.scope,reference,'Synthetic corrected recovery marker','recovery-correction')
        self.assertEqual(receipt['status'],'committed',receipt)


if __name__ == '__main__':
    unittest.main()
