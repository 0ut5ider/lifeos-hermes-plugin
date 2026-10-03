# ABOUTME: Tests reviewed publication of native staged Knowledge notes.
# ABOUTME: Verifies current references, source races, retirement, indexes, and interrupted publication.
from dataclasses import asdict
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

import test_memory_delegation as delegation
from test_memory_native import OWNER, READER
from lifeos_hook_bridge.memory_access import MemoryUnavailable


class MemoryStagingTests(unittest.TestCase):
    def setUp(self):
        self.fixture=delegation.MemoryDelegationTests();self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.native=self.fixture.fixture
        self.knowledge=self.fixture.root/'LIFEOS/MEMORY/KNOWLEDGE'
        self.staged=self.knowledge/'_harvest-queue/Research/synthetic-staged-note.md'
        self.staged.parent.mkdir(parents=True)
        self.staged.write_text('---\ntitle: "Synthetic staged note"\ntype: research\ndomain: research\n'
            'created: 2026-10-01\nupdated: 2026-10-01\nquality: 5\nstatus: pending-review\n'
            'harvested_from: synthetic-source.md\n---\n\n# Synthetic staged note\n\nSyntheticStagedCurrentMarker\n')
        self.target=self.knowledge/'Research/synthetic-staged-note.md'
        self.selector='Research/synthetic-staged-note'

    def native_call(self,*args,context=True,managed=True):
        if not managed:(self.fixture.root/'LIFEOS/USER/CONFIG/memory-access.json').unlink()
        environment=dict(os.environ,HOME=str(self.native.home),LIFEOS_DIR=str(self.fixture.root/'LIFEOS'),
                         BUN_CONFIG_NO_AUTO_INSTALL='1')
        environment.pop('LIFEOS_MEMORY_CONTEXT',None);environment.pop('LIFEOS_MEMORY_INTERNAL',None)
        if context:environment['LIFEOS_MEMORY_CONTEXT']=json.dumps(asdict(self.fixture.context))
        return subprocess.run(['bun','--no-install',str(self.fixture.root/'LIFEOS/TOOLS/KnowledgeHarvester.ts'),*args],
                              capture_output=True,text=True,env=environment,timeout=30)

    def test_unbound_native_promotion_cannot_publish_or_remove_staging(self):
        result=self.native_call('promote',self.selector,context=False)
        self.assertNotEqual(result.returncode,0)
        self.assertFalse(self.target.exists())
        self.assertTrue(self.staged.exists())
        self.assertNotIn('Synthetic staged note',result.stdout+result.stderr)

    def test_standalone_native_promotion_retains_original_content_and_indexes(self):
        original=self.staged.read_text()
        result=self.native_call('promote',self.selector,managed=False)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(self.target.read_text(),original.replace('status: pending-review\n',''))
        self.assertFalse(self.staged.exists())
        self.assertIn('Synthetic staged note',(self.knowledge/'Research/_index.md').read_text())
        self.assertIn('Synthetic staged note',(self.knowledge/'_index.md').read_text())

    def test_reviewed_promotion_preserves_native_note_and_registers_project_reference(self):
        from lifeos_hook_bridge.memory_staging import preview, promote
        original=self.staged.read_text()
        plan=preview(self.native.memory,OWNER,self.selector,project='lab')
        result=promote(self.native.memory,OWNER,self.selector,plan['signature'],'promote-one',project='lab')
        self.assertEqual(result['status'],'committed',result)
        self.assertEqual(self.target.read_text(),original.replace('status: pending-review\n',''))
        self.assertFalse(self.staged.exists())
        fact=self.native.memory.get(READER,result['references'][0])
        self.assertEqual(fact['project'],'lab')
        self.assertEqual(fact['content'],'SyntheticStagedCurrentMarker')
        self.assertEqual(fact['source']['kind'],'native-promotion')
        self.assertEqual(promote(self.native.memory,OWNER,self.selector,plan['signature'],'promote-one',project='lab'),result)
        self.assertIn('Synthetic staged note',(self.knowledge/'Research/_index.md').read_text())

    def test_unclassified_promotion_stays_private_from_project_reader(self):
        from lifeos_hook_bridge.memory_staging import preview, promote
        plan=preview(self.native.memory,OWNER,self.selector)
        result=promote(self.native.memory,OWNER,self.selector,plan['signature'],'promote-unclassified')
        self.assertEqual(result['status'],'committed',result)
        self.assertEqual(self.native.memory.recall(READER,'SyntheticStagedCurrentMarker'),[])

    def test_changed_staging_preview_cannot_publish_different_bytes(self):
        from lifeos_hook_bridge.memory_staging import preview, promote
        plan=preview(self.native.memory,OWNER,self.selector,project='lab')
        self.staged.write_text(self.staged.read_text().replace('CurrentMarker','ChangedMarker'))
        result=promote(self.native.memory,OWNER,self.selector,plan['signature'],'promote-changed',project='lab')
        self.assertEqual(result['status'],'conflict',result)
        self.assertFalse(self.target.exists());self.assertTrue(self.staged.exists())

    def test_destination_collision_preserves_existing_note_and_staging(self):
        from lifeos_hook_bridge.memory_staging import preview, promote
        plan=preview(self.native.memory,OWNER,self.selector)
        self.target.parent.mkdir();self.target.write_text('SyntheticUnrelatedExistingNote')
        result=promote(self.native.memory,OWNER,self.selector,plan['signature'],'promote-collision')
        self.assertIn(result['status'],('conflict','rejected'),result)
        self.assertEqual(self.target.read_text(),'SyntheticUnrelatedExistingNote')
        self.assertTrue(self.staged.exists())

    def test_forgotten_claim_cannot_be_promoted_from_staging(self):
        from lifeos_hook_bridge.memory_staging import preview
        saved=self.native.remember('RULE: SyntheticStagedCurrentMarker','staging-retired','principal')['reference']
        self.native.memory.forget(OWNER,saved,'staging-forget')
        with self.assertRaisesRegex(MemoryUnavailable,'excluded'):
            preview(self.native.memory,OWNER,self.selector)
        self.assertFalse(self.target.exists());self.assertTrue(self.staged.exists())

    def test_restricted_context_cannot_read_staged_unclassified_content(self):
        from lifeos_hook_bridge.memory_staging import preview
        with self.assertRaisesRegex(MemoryUnavailable,'owner'):
            preview(self.native.memory,READER,self.selector)

    def test_staged_path_cannot_select_outside_files_or_symlinks(self):
        from lifeos_hook_bridge.memory_staging import preview
        for selector in ('../outside','Research/../../outside',str(self.staged)):
            with self.subTest(selector=selector),self.assertRaises(MemoryUnavailable):
                preview(self.native.memory,OWNER,selector)
        foreign=self.native.home/'foreign.md';foreign.write_text(self.staged.read_text())
        self.staged.unlink();self.staged.symlink_to(foreign)
        with self.assertRaises(MemoryUnavailable):preview(self.native.memory,OWNER,self.selector)

    def test_derived_indexes_exclude_unregistered_and_forgotten_notes(self):
        from lifeos_hook_bridge.memory_staging import preview, promote
        self.native.memory._native('add',item={'type':'knowledge','entity_type':'research',
            'name':'SyntheticUnregisteredIndexTitle','content':'SyntheticUnregisteredIndexMarker'})
        retired=self.native.remember('SyntheticRetiredIndexMarker','index-retired','project')['reference']
        self.native.memory.forget(OWNER,retired,'index-forget')
        self.staged.write_text(self.staged.read_text())
        plan=preview(self.native.memory,OWNER,self.selector)
        result=promote(self.native.memory,OWNER,self.selector,plan['signature'],'promote-indexes')
        self.assertEqual(result['status'],'committed',result)
        indexes=(self.knowledge/'Research/_index.md').read_text()+(self.knowledge/'_index.md').read_text()
        self.assertIn('Synthetic staged note',indexes)
        self.assertNotIn('SyntheticUnregisteredIndexTitle',indexes)
        self.assertNotIn('Synthetic lab routing',indexes)

    def test_staged_source_before_an_unrelated_forget_needs_fresh_review_input(self):
        from lifeos_hook_bridge.memory_staging import preview
        retired=self.native.remember('RULE: SyntheticOtherRetiredMarker','staging-aged','principal')['reference']
        self.native.memory.forget(OWNER,retired,'staging-aged-forget')
        with self.assertRaisesRegex(MemoryUnavailable,'excluded'):
            preview(self.native.memory,OWNER,self.selector)
        self.assertTrue(self.staged.exists());self.assertFalse(self.target.exists())

    def test_existing_registered_note_remains_in_derived_indexes(self):
        from lifeos_hook_bridge.memory_staging import preview, promote
        self.native.remember('SyntheticRegisteredIndexMarker','staging-index-current','project')
        plan=preview(self.native.memory,OWNER,self.selector)
        result=promote(self.native.memory,OWNER,self.selector,plan['signature'],'promote-existing-index')
        self.assertEqual(result['status'],'committed',result)
        self.assertIn('Synthetic lab routing',(self.knowledge/'Research/_index.md').read_text())

    def test_native_managed_preview_and_apply_preserve_authenticated_session(self):
        before=self.staged.read_bytes()
        result=self.native_call('promote',self.selector,'--project','lab')
        self.assertEqual(result.returncode,0,result.stderr)
        plan=json.loads(result.stdout)
        self.assertTrue(plan['ok']);self.assertEqual(self.staged.read_bytes(),before)
        self.assertFalse(self.target.exists())
        applied=self.native_call('promote',self.selector,'--project','lab','--signature',plan['signature'],
                                 '--request-id','native-promote')
        self.assertEqual(applied.returncode,0,applied.stderr)
        receipt=json.loads(applied.stdout)['receipt']
        self.assertEqual(receipt['status'],'committed',receipt)
        fact=self.native.memory.get(READER,receipt['references'][0])
        self.assertEqual(fact['writer'],'chat-a:100')
        self.assertEqual(fact['source']['session'],self.fixture.context.session_id)

    def test_bulk_promotion_commits_each_reference_and_complete_native_indexes(self):
        from lifeos_hook_bridge.memory_staging import preview, promote
        other=self.staged.with_name('synthetic-other-note.md')
        other.write_text(self.staged.read_text().replace('Synthetic staged note','Synthetic other note')
                         .replace('SyntheticStagedCurrentMarker','SyntheticStagedOtherMarker'))
        plan=preview(self.native.memory,OWNER,all=True,project='lab')
        result=promote(self.native.memory,OWNER,None,plan['signature'],'promote-bulk',all=True,project='lab')
        self.assertEqual(result['status'],'committed',result)
        self.assertEqual(result['notes_promoted'],2)
        self.assertEqual(result['indexes_published'],5)
        self.assertTrue(all(self.native.memory.get(READER,reference)['project']=='lab' for reference in result['references']))
        self.assertFalse(self.staged.exists());self.assertFalse(other.exists())

    def test_dynamic_harvest_timestamp_cannot_enter_a_derived_index(self):
        from lifeos_hook_bridge.memory_staging import preview
        state=self.knowledge/'.harvest-state.json'
        state.write_text(json.dumps({'lastHarvest':'SyntheticInvalidHarvestClockMarker',
                                     'harvestedPaths':[],'totalHarvested':0}))
        with self.assertRaisesRegex(MemoryUnavailable,'harvest state'):
            preview(self.native.memory,OWNER,self.selector)

    def test_revoked_context_cannot_apply_a_previous_native_promotion_preview(self):
        plan=json.loads(self.native_call('promote',self.selector).stdout)
        self.fixture.configuration.update(lambda config:config['accounts'].pop('chat-a:100'))
        denied=self.native_call('promote',self.selector,'--signature',plan['signature'])
        self.assertNotEqual(denied.returncode,0)
        self.assertTrue(self.staged.exists());self.assertFalse(self.target.exists())

    def test_failed_batch_preview_leaves_every_source_in_staging(self):
        from lifeos_hook_bridge.memory_staging import preview
        other=self.staged.with_name('synthetic-invalid-note.md')
        other.write_text('Synthetic note without frontmatter')
        before=self.staged.read_bytes()
        with self.assertRaises(MemoryUnavailable):preview(self.native.memory,OWNER,all=True)
        self.assertEqual(self.staged.read_bytes(),before)
        self.assertTrue(other.exists());self.assertFalse(self.target.exists())

    def test_death_after_staging_removal_recovers_all_files_and_retries(self):
        from lifeos_hook_bridge.memory_staging import preview, promote
        plan=preview(self.native.memory,OWNER,self.selector,project='lab')
        before=self.staged.read_bytes()
        program='''import os,sys
from pathlib import Path
from lifeos_hook_bridge.memory_access import NativeMemory
from lifeos_hook_bridge.memory_policy import MemoryScope
from lifeos_hook_bridge.memory_staging import promote
memory=NativeMemory(Path(sys.argv[1]))
scope=MemoryScope('owner','local:owner',('assistant','principal','project'),('assistant','principal','project'),('*',),'owner-test')
def stop():os._exit(95)
memory.transaction.flush_publication=stop
promote(memory,scope,sys.argv[2],sys.argv[3],'promote-interrupted',project='lab')
'''
        environment=dict(os.environ,PYTHONPATH=str(Path(__file__).resolve().parents[1]))
        child=subprocess.run([sys.executable,'-c',program,str(self.fixture.root),self.selector,plan['signature']],
                             capture_output=True,text=True,env=environment,timeout=30)
        self.assertEqual(child.returncode,95,child.stderr)
        self.assertEqual(child.stdout+child.stderr,'')
        self.assertTrue(self.target.exists());self.assertFalse(self.staged.exists())
        self.assertTrue((self.knowledge/'_index.md').exists())
        self.assertTrue(self.native.memory.transaction.journal.exists())
        with self.native.memory._transaction():pass
        self.assertEqual(self.staged.read_bytes(),before)
        self.assertFalse(self.target.exists());self.assertFalse((self.knowledge/'_index.md').exists())
        self.assertEqual(self.native.memory.recall(READER,'SyntheticStagedCurrentMarker'),[])
        result=promote(self.native.memory,OWNER,self.selector,plan['signature'],'promote-interrupted',project='lab')
        self.assertEqual(result['status'],'committed',result)
        self.assertIn('SyntheticStagedCurrentMarker',self.native.memory.get(READER,result['references'][0])['content'])

    def test_maximum_declared_batch_uses_actual_native_connector_deadline(self):
        import time
        from lifeos_hook_bridge.memory_staging import BATCH_LIMIT
        for index in range(BATCH_LIMIT-1):
            note=self.staged.with_name('synthetic-batch-'+str(index)+'.md')
            note.write_text(self.staged.read_text().replace('Synthetic staged note','Synthetic batch note '+str(index))
                            .replace('SyntheticStagedCurrentMarker','SyntheticStagedBatchMarker'+str(index)))
        started=time.monotonic()
        result=self.native_call('promote','--all','--project','lab')
        elapsed=time.monotonic()-started
        self.assertEqual(result.returncode,0,result.stderr)
        plan=json.loads(result.stdout)
        self.assertEqual(len(plan['notes']),BATCH_LIMIT)
        self.assertLess(elapsed,40)

    def test_staged_native_identifier_cannot_duplicate_a_current_note(self):
        import re
        from lifeos_hook_bridge.memory_staging import preview
        self.native.remember('SyntheticCurrentIdentifierMarker','staging-id-existing','project')
        existing=next((self.knowledge/'Research').glob('*.md'))
        identifier=re.search(r'^id:.*$',existing.read_text(),flags=re.MULTILINE).group()
        self.staged.write_text(self.staged.read_text().replace('---\n','---\n'+identifier+'\n',1))
        with self.assertRaisesRegex(MemoryUnavailable,'duplicate'):
            preview(self.native.memory,OWNER,self.selector)
        self.assertTrue(self.staged.exists());self.assertFalse(self.target.exists())


if __name__=='__main__':unittest.main()
