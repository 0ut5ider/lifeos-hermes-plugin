# ABOUTME: Tests native hot-memory recovery under current fact authority.
# ABOUTME: Uses genuine snapshots and checks retirement, later writes, and preview races.
from dataclasses import asdict
import json
import os
from pathlib import Path
import subprocess
import unittest

import test_memory_delegation as delegation
from test_memory_native import OWNER, READER
from lifeos_hook_bridge.memory_access import HOT_FILES


class MemoryRestoreTests(unittest.TestCase):
    def setUp(self):
        self.fixture=delegation.MemoryDelegationTests();self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.native=self.fixture.fixture
        self.first=self.native.remember('RULE: SyntheticRestoreCurrentMarker','restore-first','principal')['reference']
        self.second=self.native.remember('RULE: SyntheticRestoreLaterMarker','restore-second','principal')['reference']
        self.target=self.fixture.root/HOT_FILES['principal']
        snapshots=self.fixture.root/'LIFEOS/MEMORY/OBSERVABILITY/memory-snapshots'
        self.snapshot=next(path for path in snapshots.glob('PRINCIPAL_MEMORY__*.md')
                           if 'SyntheticRestoreCurrentMarker' in path.read_text())

    def native_call(self,*args,context=True,managed=True):
        if not managed:(self.fixture.root/'LIFEOS/USER/CONFIG/memory-access.json').unlink()
        environment=dict(os.environ,HOME=str(self.native.home),BUN_CONFIG_NO_AUTO_INSTALL='1')
        environment.pop('LIFEOS_MEMORY_CONTEXT',None);environment.pop('LIFEOS_MEMORY_INTERNAL',None)
        if context:environment['LIFEOS_MEMORY_CONTEXT']=json.dumps(asdict(self.fixture.context))
        module=self.fixture.root/'LIFEOS/TOOLS/MemoryRestore.ts'
        return subprocess.run(['bun','--no-install',str(module),*args],env=environment,
                              capture_output=True,text=True,timeout=30)

    def test_native_unbound_restore_cannot_republish_forgotten_fact(self):
        self.native.memory.forget(OWNER,self.first,'restore-forget')
        before=self.target.read_bytes()
        result=self.native_call('restore',self.snapshot.name,context=False)
        self.assertNotEqual(result.returncode,0)
        self.assertEqual(self.target.read_bytes(),before)
        self.assertIn('SyntheticRestoreLaterMarker',self.target.read_text())

    def test_unmanaged_native_restore_keeps_byte_copy_control(self):
        result=self.native_call('restore',self.snapshot.name,managed=False)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(self.target.read_bytes(),self.snapshot.read_bytes())

    def test_reviewed_recovery_repairs_missing_active_fact_and_preserves_later_fact(self):
        from lifeos_hook_bridge.memory_restore import preview, restore
        self.target.write_text(self.target.read_text().replace('RULE: SyntheticRestoreCurrentMarker\n',''))
        plan=preview(self.native.memory,OWNER,self.snapshot.name)
        self.assertEqual(plan['recovered_facts'],1)
        self.assertEqual(plan['preserved_facts'],1)
        result=restore(self.native.memory,OWNER,self.snapshot.name,plan['signature'],'recover-current')
        self.assertEqual(result['status'],'committed',result)
        for reference,marker in ((self.first,'Current'),(self.second,'Later')):
            fact=self.native.memory.get(OWNER,reference)
            self.assertIn('SyntheticRestore'+marker+'Marker',fact['content'])
            self.assertEqual(fact['reference'],reference)
        self.assertEqual(restore(self.native.memory,OWNER,self.snapshot.name,plan['signature'],'recover-current'),result)

    def test_recovery_never_reactivates_retired_snapshot_fact(self):
        from lifeos_hook_bridge.memory_restore import preview, restore
        self.native.memory.forget(OWNER,self.first,'restore-retire')
        plan=preview(self.native.memory,OWNER,self.snapshot.name)
        self.assertEqual(plan['excluded_snapshot_facts'],1)
        result=restore(self.native.memory,OWNER,self.snapshot.name,plan['signature'],'recover-retired')
        self.assertIn(result['status'],('committed','unchanged'),result)
        self.assertNotIn('SyntheticRestoreCurrentMarker',self.target.read_text())
        self.assertIn('SyntheticRestoreLaterMarker',self.native.memory.get(OWNER,self.second)['content'])

    def test_concurrent_later_write_invalidates_preview_without_losing_facts(self):
        from lifeos_hook_bridge.memory_restore import preview, restore
        plan=preview(self.native.memory,OWNER,self.snapshot.name)
        third=self.native.remember('RULE: SyntheticRestoreConcurrentMarker','restore-third','principal')['reference']
        before=self.target.read_bytes()
        result=restore(self.native.memory,OWNER,self.snapshot.name,plan['signature'],'recover-stale')
        self.assertEqual(result['status'],'conflict',result)
        self.assertEqual(self.target.read_bytes(),before)
        self.assertIn('ConcurrentMarker',self.native.memory.get(OWNER,third)['content'])

    def test_snapshot_change_invalidates_reviewed_recovery(self):
        from lifeos_hook_bridge.memory_restore import preview, restore
        plan=preview(self.native.memory,OWNER,self.snapshot.name)
        self.snapshot.write_text(self.snapshot.read_text()+'\n# Synthetic changed snapshot\n')
        before=self.target.read_bytes()
        result=restore(self.native.memory,OWNER,self.snapshot.name,plan['signature'],'recover-changed')
        self.assertEqual(result['status'],'conflict',result)
        self.assertEqual(self.target.read_bytes(),before)

    def test_restricted_reader_cannot_preview_native_recovery(self):
        from lifeos_hook_bridge.memory_restore import preview
        from lifeos_hook_bridge.memory_access import MemoryUnavailable
        with self.assertRaisesRegex(MemoryUnavailable,'owner'):
            preview(self.native.memory,READER,self.snapshot.name)

    def test_snapshot_reference_cannot_select_another_path_or_symlink(self):
        from lifeos_hook_bridge.memory_restore import preview
        from lifeos_hook_bridge.memory_access import MemoryUnavailable
        alias=self.snapshot.parent/'PRINCIPAL_MEMORY__2026-10-01T00-00-00-000Z.md'
        alias.symlink_to(self.target)
        for name in ('../PRINCIPAL_MEMORY.md',str(self.target),alias.name,'unknown.md'):
            with self.subTest(name=name),self.assertRaises(MemoryUnavailable):
                preview(self.native.memory,OWNER,name)

    def test_unregistered_snapshot_fact_is_not_implicitly_adopted(self):
        from lifeos_hook_bridge.memory_restore import preview, restore
        self.snapshot.write_text(self.snapshot.read_text().replace('<!-- END ENTRIES -->',
            'RULE: SyntheticRestoreUnregisteredMarker\n<!-- END ENTRIES -->'))
        plan=preview(self.native.memory,OWNER,self.snapshot.name)
        self.assertEqual(plan['excluded_snapshot_facts'],1)
        result=restore(self.native.memory,OWNER,self.snapshot.name,plan['signature'],'recover-unregistered')
        self.assertIn(result['status'],('committed','unchanged'),result)
        self.assertNotIn('SyntheticRestoreUnregisteredMarker',self.target.read_text())

    def test_native_preview_then_explicit_apply_preserves_authority_and_references(self):
        self.target.write_text(self.target.read_text().replace('RULE: SyntheticRestoreCurrentMarker\n',''))
        before=self.target.read_bytes()
        preview=self.native_call('restore',self.snapshot.name)
        self.assertEqual(preview.returncode,0,preview.stderr)
        plan=json.loads(preview.stdout)
        self.assertTrue(plan['ok']);self.assertEqual(self.target.read_bytes(),before)
        applied=self.native_call('restore',self.snapshot.name,'--signature',plan['signature'],'--request-id','native-restore')
        self.assertEqual(applied.returncode,0,applied.stderr)
        result=json.loads(applied.stdout)
        self.assertTrue(result['ok']);self.assertTrue(result['receipt']['references_preserved'])
        self.assertIn('CurrentMarker',self.native.memory.get(OWNER,self.first)['content'])
        self.assertIn('LaterMarker',self.native.memory.get(OWNER,self.second)['content'])
        repeated=self.native_call('restore',self.snapshot.name,'--signature',plan['signature'],'--request-id','native-restore')
        self.assertEqual(json.loads(repeated.stdout),result)

    def test_revoked_binding_cannot_apply_previous_native_preview(self):
        plan=json.loads(self.native_call('restore',self.snapshot.name).stdout)
        self.fixture.configuration.update(lambda config:config['accounts'].pop('chat-a:100'))
        before=self.target.read_bytes()
        denied=self.native_call('restore',self.snapshot.name,'--signature',plan['signature'])
        self.assertNotEqual(denied.returncode,0)
        self.assertEqual(self.target.read_bytes(),before)

    def test_corrected_snapshot_does_not_restore_old_revision(self):
        from lifeos_hook_bridge.memory_restore import preview, restore
        receipt=self.native.memory.correct(OWNER,self.first,'RULE: SyntheticRestoreReplacementMarker','restore-correct')
        current=self.native.memory.get(OWNER,receipt['reference'])
        plan=preview(self.native.memory,OWNER,self.snapshot.name)
        self.assertEqual(plan['excluded_snapshot_facts'],1)
        result=restore(self.native.memory,OWNER,self.snapshot.name,plan['signature'],'recover-corrected')
        self.assertEqual(result['status'],'committed',result)
        self.assertEqual(self.native.memory.get(OWNER,receipt['reference']),current)
        self.assertNotIn('SyntheticRestoreCurrentMarker',json.dumps(result))

    def test_oversized_snapshot_refuses_before_native_parsing(self):
        from lifeos_hook_bridge.memory_restore import preview, SOURCE_LIMIT
        from lifeos_hook_bridge.memory_access import MemoryUnavailable
        with self.snapshot.open('ab') as stream:stream.truncate(SOURCE_LIMIT+1)
        with self.assertRaisesRegex(MemoryUnavailable,'size limit'):
            preview(self.native.memory,OWNER,self.snapshot.name)

    def test_unregistered_current_fact_requires_review_before_recovery(self):
        from lifeos_hook_bridge.memory_restore import preview
        from lifeos_hook_bridge.memory_access import MemoryUnavailable
        self.target.write_text(self.target.read_text().replace('<!-- END ENTRIES -->',
            'RULE: SyntheticRestoreUnreviewedCurrentMarker\n<!-- END ENTRIES -->'))
        before=self.target.read_bytes()
        with self.assertRaisesRegex(MemoryUnavailable,'unregistered'):
            preview(self.native.memory,OWNER,self.snapshot.name)
        self.assertEqual(self.target.read_bytes(),before)

    def test_process_death_after_native_publication_recovers_and_retries(self):
        from lifeos_hook_bridge.memory_restore import preview, restore
        import sys
        self.target.write_text(self.target.read_text().replace('RULE: SyntheticRestoreCurrentMarker\n',''))
        before=self.target.read_bytes()
        plan=preview(self.native.memory,OWNER,self.snapshot.name)
        program='''import os,sys
from pathlib import Path
from lifeos_hook_bridge.memory_access import NativeMemory
from lifeos_hook_bridge.memory_policy import MemoryScope
from lifeos_hook_bridge.memory_restore import restore
class Interrupted(NativeMemory):
    def _native(self,action,**values):
        result=super()._native(action,**values)
        if action=='set_hot':os._exit(93)
        return result
memory=Interrupted(Path(sys.argv[1]))
scope=MemoryScope('owner','local:owner',('assistant','principal','project'),('assistant','principal','project'),('*',),'owner-test')
restore(memory,scope,sys.argv[2],sys.argv[3],'recover-interrupted')
'''
        environment=dict(os.environ,PYTHONPATH=str(Path(__file__).resolve().parents[1]))
        child=subprocess.run([sys.executable,'-c',program,str(self.fixture.root),self.snapshot.name,plan['signature']],
                             capture_output=True,text=True,env=environment,timeout=30)
        self.assertEqual(child.returncode,93,child.stderr)
        self.assertEqual(child.stdout+child.stderr,'')
        self.assertNotEqual(self.target.read_bytes(),before)
        self.assertTrue(self.native.memory.transaction.journal.exists())
        with self.native.memory._transaction():pass
        self.assertEqual(self.target.read_bytes(),before)
        self.assertFalse(self.native.memory.transaction.journal.exists())
        result=restore(self.native.memory,OWNER,self.snapshot.name,plan['signature'],'recover-interrupted')
        self.assertEqual(result['status'],'committed',result)
        self.assertIn('CurrentMarker',self.native.memory.get(OWNER,self.first)['content'])
        self.assertIn('LaterMarker',self.native.memory.get(OWNER,self.second)['content'])

    def test_recovery_receipt_does_not_quote_retired_current_drift(self):
        from lifeos_hook_bridge.memory_restore import preview, restore
        self.native.memory.forget(OWNER,self.first,'restore-drift-forget')
        self.target.write_text(self.target.read_text().replace('<!-- END ENTRIES -->',
            'RULE: SyntheticRestoreCurrentMarker\n<!-- END ENTRIES -->'))
        plan=preview(self.native.memory,OWNER,self.snapshot.name)
        result=restore(self.native.memory,OWNER,self.snapshot.name,plan['signature'],'recover-retired-drift')
        self.assertEqual(result['status'],'committed',result)
        self.assertNotIn('SyntheticRestoreCurrentMarker',json.dumps(result))
        self.assertNotIn('SyntheticRestoreCurrentMarker',self.target.read_text())

    def test_managed_list_and_latest_are_owner_previews_without_mutation(self):
        before=self.target.read_bytes()
        denied=self.native_call('list',context=False)
        self.assertNotEqual(denied.returncode,0)
        listing=self.native_call('list','principal')
        self.assertEqual(listing.returncode,0,listing.stderr)
        self.assertIn(self.snapshot.name,json.loads(listing.stdout)['snapshots'])
        latest=self.native_call('latest','principal')
        self.assertEqual(latest.returncode,0,latest.stderr)
        self.assertEqual(json.loads(latest.stdout)['snapshot'],json.loads(listing.stdout)['snapshots'][-1])
        self.assertEqual(self.target.read_bytes(),before)

    def test_recovery_preserves_committed_result_after_death_before_journal_cleanup(self):
        from lifeos_hook_bridge.memory_restore import preview, restore
        import sys
        self.target.write_text(self.target.read_text().replace('RULE: SyntheticRestoreCurrentMarker\n',''))
        plan=preview(self.native.memory,OWNER,self.snapshot.name)
        program='''import os,sys
from pathlib import Path
from lifeos_hook_bridge.memory_access import NativeMemory
from lifeos_hook_bridge.memory_policy import MemoryScope
from lifeos_hook_bridge.memory_restore import restore
memory=NativeMemory(Path(sys.argv[1]))
scope=MemoryScope('owner','local:owner',('assistant','principal','project'),('assistant','principal','project'),('*',),'owner-test')
def stop():os._exit(94)
memory.transaction.finish=stop
restore(memory,scope,sys.argv[2],sys.argv[3],'recover-committed')
'''
        environment=dict(os.environ,PYTHONPATH=str(Path(__file__).resolve().parents[1]))
        child=subprocess.run([sys.executable,'-c',program,str(self.fixture.root),self.snapshot.name,plan['signature']],
                             capture_output=True,text=True,env=environment,timeout=30)
        self.assertEqual(child.returncode,94,child.stderr)
        self.assertEqual(child.stdout+child.stderr,'')
        committed=self.target.read_bytes()
        self.assertTrue(self.native.memory.transaction.journal.exists())
        result=restore(self.native.memory,OWNER,self.snapshot.name,plan['signature'],'recover-committed')
        self.assertEqual(result['status'],'committed',result)
        self.assertEqual(self.target.read_bytes(),committed)
        self.assertFalse(self.native.memory.transaction.journal.exists())
        self.assertIn('CurrentMarker',self.native.memory.get(OWNER,self.first)['content'])


if __name__=='__main__':unittest.main()
