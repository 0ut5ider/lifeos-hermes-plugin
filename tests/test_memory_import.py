# ABOUTME: Verifies private Hermes import review against real native memory and synthetic profiles.
# ABOUTME: Checks complete source accounting, review bindings, permissions, and preserved original bytes.
from pathlib import Path
import json
import os
import unittest

import test_memory_native as fixture
from lifeos_hook_bridge.memory_access import MemoryUnavailable
from lifeos_hook_bridge.memory_service import MemoryConfiguration


class MemoryImportTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixture.NativeMemoryTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.profile = self.fixture.home / 'hermes'
        self.profile.mkdir(mode=0o700)
        self.sources = self.profile / 'memories'
        self.sources.mkdir(mode=0o700)
        self.configuration = MemoryConfiguration(self.profile / 'lifeos-memory.json')
        self.configuration.save({'version':1,'root':str(self.fixture.root),'principal':'owner',
            'ownership_enabled':False,'sharing_enabled':False,'accounts':{'dashboard:owner':'owner'},
            'destinations':{},'clients':{}})
        (self.profile / 'config.yaml').write_text('memory:\n  provider: builtin\n  memory_enabled: true\n  user_profile_enabled: true\n')
        os.chmod(self.profile / 'config.yaml',0o600)
        self.raw=b'\xef\xbb\xbf  synthetic A \n\xc2\xa7\n\n\xc2\xa7\n synthetic A \n\xc2\xa7\n bare \xc2\xa7 symbol\r\n'
        (self.sources / 'MEMORY.md').write_bytes(self.raw)
        self.snapshot=self.fixture.home / 'private-review'

    def operation(self):
        from lifeos_hook_bridge.memory_import import MemoryImport
        return MemoryImport(self.configuration)

    def preview(self):
        return self.operation().preview(account='dashboard:owner')

    def test_preview_accounts_for_every_byte_and_preserves_duplicate_occurrences(self):
        result=self.preview()
        source=result['sources'][0]
        self.assertEqual(source['path'],'memories/MEMORY.md')
        self.assertEqual(source['status'],'present')
        self.assertEqual(source['byte_order_mark'],True)
        entries=source['chunks']
        self.assertEqual([row['content'] for row in entries],['synthetic A','','synthetic A','bare § symbol'])
        self.assertEqual(len({row['id'] for row in entries}),4)
        rebuilt=b'\xef\xbb\xbf'+b''.join(row['raw'].encode()+row['separator_after'].encode() for row in entries)
        self.assertEqual(rebuilt,self.raw)
        self.assertEqual(entries[1]['disposition'],'empty')
        self.assertEqual(entries[2]['exact_duplicate_occurrence'],entries[0]['id'])
        self.assertEqual(result['sources'][1]['status'],'missing')
        self.assertFalse(result['ownership_enabled'])
        self.assertEqual((self.sources/'MEMORY.md').read_bytes(),self.raw)
        self.assertEqual(self.fixture.memory.recall(fixture.OWNER,'synthetic A'),[])

    def test_windows_newlines_match_native_hermes_parsing_without_losing_bytes(self):
        raw=b'\xef\xbb\xbf  first\r\nline \r\n\xc2\xa7\r\n second \r'
        (self.sources/'MEMORY.md').write_bytes(raw)
        source=self.preview()['sources'][0]
        self.assertEqual([row['content'] for row in source['chunks']],['first\nline','second'])
        rebuilt=b'\xef\xbb\xbf'+b''.join(row['raw'].encode()+row['separator_after'].encode() for row in source['chunks'])
        self.assertEqual(rebuilt,raw)

    def test_snapshot_preserves_bytes_and_is_private_and_immutable(self):
        review=self.preview()
        saved=self.operation().prepare(self.snapshot,review['signature'],account='dashboard:owner')
        self.assertEqual(saved['state'],'review')
        self.assertEqual((self.snapshot/'sources/MEMORY.md').read_bytes(),self.raw)
        self.assertFalse((self.snapshot/'sources/USER.md').exists())
        for path in self.snapshot.rglob('*'):
            self.assertEqual(path.stat().st_mode & 0o077,0)
        with self.assertRaises(MemoryUnavailable):
            self.operation().prepare(self.snapshot,review['signature'],account='dashboard:owner')
        self.assertEqual(self.operation().inspect(self.snapshot,saved['snapshot_signature'],account='dashboard:owner')['review']['signature'],review['signature'])

    def test_changed_source_config_target_and_grant_invalidate_review(self):
        review=self.preview()
        path=self.sources/'MEMORY.md'
        path.write_bytes(self.raw+b'changed')
        with self.assertRaises(MemoryUnavailable):
            self.operation().prepare(self.snapshot,review['signature'],account='dashboard:owner')
        path.write_bytes(self.raw)
        review=self.preview()
        saved=self.fixture.memory.remember(fixture.OWNER,category='principal',content='RULE: synthetic target',title='',project='',request_id='target')
        self.assertEqual(saved['status'],'committed',saved)
        self.assertNotEqual(self.preview()['signature'],review['signature'])
        review=self.preview()
        (self.profile/'config.yaml').write_text('memory:\n  provider: builtin\n  memory_char_limit: 900\n')
        self.assertNotEqual(self.preview()['signature'],review['signature'])
        review=self.preview()
        self.configuration.update(lambda value:value.update(destinations={'chat:shared':{'visibility':'shared','participants':['owner','reader'],'read':['principal'],'write':[],'projects':['*'],'model_routes':['local']}}))
        newer=self.preview()
        self.assertNotEqual(newer['signature'],review['signature'])
        self.assertEqual(newer['readers']['destinations']['chat:shared']['participants'],['owner','reader'])

    def test_exact_native_duplicates_and_retired_claims_are_explicit(self):
        path=self.sources/'USER.md';path.write_text('PREFERENCE: synthetic preference\n§\nRULE: synthetic retired\n§\nSynthetic retired plus other context.')
        saved=self.fixture.memory.remember(fixture.OWNER,category='principal',content='PREFERENCE: synthetic preference',title='',project='',request_id='duplicate')
        retired=self.fixture.memory.remember(fixture.OWNER,category='principal',content='RULE: synthetic retired',title='',project='',request_id='retire')
        self.fixture.memory.forget(fixture.OWNER,retired['reference'],'forget')
        result=self.preview()
        entries=result['sources'][1]['chunks']
        self.assertEqual(entries[0]['exact_native_matches'],[saved['reference']])
        self.assertTrue(entries[1]['retired_claim'])
        self.assertTrue(entries[2]['retired_claim'])
        self.assertTrue(result['semantic_conflicts_incomplete'])

    def test_missing_read_error_invalid_encoding_and_symlink_have_distinct_outcomes(self):
        self.assertEqual(self.preview()['sources'][1]['status'],'missing')
        path=self.sources/'USER.md'
        path.write_bytes(b'\xff\xfe')
        result=self.preview()
        self.assertEqual(result['sources'][1]['status'],'invalid_encoding')
        self.assertFalse(result['ready_for_item_review'])
        path.unlink();path.mkdir()
        with self.assertRaises(MemoryUnavailable):self.preview()
        path.rmdir();path.symlink_to(self.sources/'MEMORY.md')
        with self.assertRaises(MemoryUnavailable):self.preview()

    def test_native_private_and_control_text_are_quarantined_without_loss(self):
        data=b'ordinary context\n\xc2\xa7\n<private>synthetic private text</private>\n\xc2\xa7\ncontrol\x00text'
        (self.sources/'MEMORY.md').write_bytes(data)
        review=self.preview()
        chunks=review['sources'][0]['chunks']
        self.assertEqual([row['disposition'] for row in chunks],['review','quarantined','quarantined'])
        saved=self.operation().prepare(self.snapshot,review['signature'],account='dashboard:owner')
        self.assertEqual((Path(saved['snapshot'])/'sources/MEMORY.md').read_bytes(),data)
        self.assertFalse(self.configuration.load()['ownership_enabled'])

    def item_plan(self):
        (self.sources/'MEMORY.md').write_text('Synthetic lab uses port 9123.')
        (self.sources/'USER.md').write_text('Prefer concise answers.')
        review=self.preview()
        saved=self.operation().prepare(self.snapshot,review['signature'],account='dashboard:owner')
        decisions=[]
        for source in review['sources']:
            chunk=source['chunks'][0]
            decisions.append({'id':chunk['id'],'action':'import','required':True,
                'category':'project' if source['path'].endswith('MEMORY.md') else 'principal',
                'content':chunk['content'],'title':'Synthetic imported routing','project':'lab'})
        plan=self.operation().plan(self.snapshot,saved['snapshot_signature'],decisions,account='dashboard:owner')
        return saved,plan

    def test_reviewed_import_publishes_exact_items_with_provenance_and_safe_retry(self):
        saved,plan=self.item_plan()
        self.assertEqual(plan['items'][1]['content'],'PREFERENCE: Prefer concise answers.')
        result=self.operation().apply(self.snapshot,saved['snapshot_signature'],plan['signature'],account='dashboard:owner')
        self.assertEqual(result['state'],'published',result)
        self.assertFalse(result['ownership_enabled'])
        self.assertTrue(result['required_items_verified'])
        self.assertEqual([row['receipt']['status'] for row in result['items']],['committed','committed'])
        for row in result['items']:
            receipt=row['receipt']
            self.assertEqual(receipt['writer'],'dashboard:owner')
            self.assertEqual(receipt['source']['kind'],'hermes-import')
            self.assertEqual(receipt['source']['original_author'],'unknown')
            self.assertEqual(self.fixture.memory.get(fixture.OWNER,receipt['reference'])['content'],row['content'])
        again=self.operation().apply(self.snapshot,saved['snapshot_signature'],plan['signature'],account='dashboard:owner')
        self.assertEqual(again,result)
        self.assertEqual(len(self.fixture.memory.recall(fixture.OWNER,'synthetic')),1)
        self.assertEqual((self.sources/'MEMORY.md').read_text(),'Synthetic lab uses port 9123.')
        self.assertFalse(self.configuration.load()['ownership_enabled'])

    def test_apply_refuses_later_target_and_source_changes_before_publication(self):
        saved,plan=self.item_plan()
        self.fixture.memory.remember(fixture.OWNER,category='principal',content='RULE: Later owner fact',title='',project='',request_id='later')
        result=self.operation().apply(self.snapshot,saved['snapshot_signature'],plan['signature'],account='dashboard:owner')
        self.assertEqual(result['state'],'conflict',result)
        self.assertEqual(self.fixture.memory.recall(fixture.OWNER,'9123'),[])
        self.assertEqual(self.fixture.memory.recall(fixture.OWNER,'concise'),[])

    def test_real_process_exit_after_native_commit_resumes_without_duplicate_facts(self):
        import subprocess,sys
        saved,plan=self.item_plan()
        settings={'configuration':str(self.configuration.path),'snapshot':str(self.snapshot),
            'snapshot_signature':saved['snapshot_signature'],'plan_signature':plan['signature']}
        code='''import json,os,sys
from pathlib import Path
from lifeos_hook_bridge.memory_service import MemoryConfiguration
from lifeos_hook_bridge.memory_import import MemoryImport
settings=json.loads(sys.stdin.read())
def trace(frame,event,argument):
 if event=='return' and frame.f_code.co_name=='remember' and frame.f_code.co_filename.endswith('/memory_access.py'):
  os._exit(73)
 return trace
sys.settrace(trace)
MemoryImport(MemoryConfiguration(Path(settings['configuration']))).apply(Path(settings['snapshot']),settings['snapshot_signature'],settings['plan_signature'],account='dashboard:owner')
'''
        child=subprocess.run([sys.executable,'-c',code],input=json.dumps(settings),text=True,capture_output=True,env=os.environ.copy(),timeout=30)
        self.assertEqual(child.returncode,73,child.stdout+child.stderr)
        self.assertEqual(child.stdout+child.stderr,'')
        self.assertFalse((self.snapshot/'publication.json').exists())
        result=self.operation().apply(self.snapshot,saved['snapshot_signature'],plan['signature'],account='dashboard:owner')
        self.assertEqual(result['state'],'published',result)
        self.assertTrue(result['required_items_verified'])
        self.assertEqual(len(self.fixture.memory.recall(fixture.OWNER,'9123')),1)
        self.assertEqual(len(self.fixture.memory.recall(fixture.OWNER,'concise')),1)

    def test_real_process_exit_before_hot_commit_recovers_bytes_permissions_and_retry(self):
        import subprocess,sys
        saved,plan=self.item_plan()
        target=self.fixture.root/'LIFEOS/USER/PRINCIPAL/PRINCIPAL_MEMORY.md'
        original=target.read_bytes();mode=target.stat().st_mode & 0o777
        settings={'configuration':str(self.configuration.path),'snapshot':str(self.snapshot),
            'snapshot_signature':saved['snapshot_signature'],'plan_signature':plan['signature']}
        code='''import json,os,sys
from pathlib import Path
from lifeos_hook_bridge.memory_service import MemoryConfiguration
from lifeos_hook_bridge.memory_import import MemoryImport
settings=json.loads(sys.stdin.read())
def trace(frame,event,argument):
 if event=='return' and frame.f_code.co_name=='save_fact' and frame.f_code.co_filename.endswith('/memory_access.py') and frame.f_locals.get('category')=='principal':
  os._exit(73)
 return trace
sys.settrace(trace)
MemoryImport(MemoryConfiguration(Path(settings['configuration']))).apply(Path(settings['snapshot']),settings['snapshot_signature'],settings['plan_signature'],account='dashboard:owner')
'''
        child=subprocess.run([sys.executable,'-c',code],input=json.dumps(settings),text=True,capture_output=True,env=os.environ.copy(),timeout=30)
        self.assertEqual(child.returncode,73,child.stdout+child.stderr)
        self.assertEqual(child.stdout+child.stderr,'')
        self.assertNotEqual(target.read_bytes(),original)
        with self.fixture.memory._transaction():pass
        self.assertEqual(target.read_bytes(),original)
        self.assertEqual(target.stat().st_mode & 0o777,mode)
        result=self.operation().apply(self.snapshot,saved['snapshot_signature'],plan['signature'],account='dashboard:owner')
        self.assertEqual(result['state'],'published',result)
        self.assertEqual(len(self.fixture.memory.recall(fixture.OWNER,'9123')),1)
        self.assertEqual(len(self.fixture.memory.recall(fixture.OWNER,'concise')),1)

    def test_capacity_and_required_pending_items_do_not_change_ownership(self):
        saved,plan=self.item_plan()
        self.snapshot=self.fixture.home/'private-review-pending'
        review=self.preview()
        saved=self.operation().prepare(self.snapshot,review['signature'],account='dashboard:owner')
        pending=[]
        for item in plan['items']:
            pending.append({'id':item['id'],'action':'pending','required':True,'reason':'Owner keeps this item pending.'})
        held=self.operation().plan(self.snapshot,saved['snapshot_signature'],pending,account='dashboard:owner')
        result=self.operation().apply(self.snapshot,saved['snapshot_signature'],held['signature'],account='dashboard:owner')
        self.assertEqual(result['state'],'partial')
        self.assertFalse(result['required_items_verified'])
        self.assertEqual(self.fixture.memory.recall(fixture.OWNER,'9123'),[])
        self.assertFalse(self.configuration.load()['ownership_enabled'])

    def test_native_hot_capacity_refuses_the_whole_plan_without_eviction(self):
        entries=['RULE: synthetic capacity '+str(index) for index in range(48)]
        hot=self.fixture.memory.read_hot(fixture.OWNER,'principal')
        receipt=self.fixture.memory.native_set(fixture.OWNER,'principal',entries,'capacity',hot['revision'])
        self.assertTrue(receipt['ok'],receipt)
        self.assertEqual(receipt['receipt']['status'],'committed',receipt)
        (self.sources/'MEMORY.md').write_text('')
        (self.sources/'USER.md').write_text('One additional preference.')
        review=self.preview()
        saved=self.operation().prepare(self.snapshot,review['signature'],account='dashboard:owner')
        item=review['sources'][1]['chunks'][0]
        with self.assertRaisesRegex(ValueError,'capacity'):
            self.operation().plan(self.snapshot,saved['snapshot_signature'],[{'id':item['id'],'action':'import','required':True,
                'category':'principal','content':item['content'],'title':'','project':''}],account='dashboard:owner')
        self.assertEqual(self.fixture.memory.read_hot(fixture.OWNER,'principal')['entries'],entries)
        self.assertFalse((self.snapshot/'plan.json').exists())

    def test_every_nonempty_occurrence_requires_one_explicit_decision(self):
        saved,plan=self.item_plan()
        with self.assertRaises(ValueError):self.operation().plan(self.snapshot,saved['snapshot_signature'],[],account='dashboard:owner')
        with self.assertRaises(ValueError):self.operation().plan(self.snapshot,saved['snapshot_signature'],[plan['items'][0]],account='dashboard:owner')

    def test_owner_binding_and_builtin_provider_are_required(self):
        for account in (None,'dashboard:other','chat:owner'):
            with self.subTest(account=account):
                with self.assertRaises(PermissionError):self.operation().preview(account=account)
        (self.profile/'config.yaml').write_text('memory:\n  provider: external\n')
        with self.assertRaises(MemoryUnavailable):self.preview()

    def test_snapshot_tampering_and_live_tree_destination_are_rejected(self):
        review=self.preview()
        for destination in (self.profile/'review',self.fixture.root/'review',self.fixture.home/'.config/LIFEOS/USER/review'):
            with self.subTest(destination=destination):
                with self.assertRaises(MemoryUnavailable):
                    self.operation().prepare(destination,review['signature'],account='dashboard:owner')
        saved=self.operation().prepare(self.snapshot,review['signature'],account='dashboard:owner')
        (self.snapshot/'sources/MEMORY.md').write_bytes(b'tampered')
        with self.assertRaises(MemoryUnavailable):
            self.operation().inspect(self.snapshot,saved['snapshot_signature'],account='dashboard:owner')

    def test_snapshot_metadata_must_account_for_the_preserved_bytes(self):
        import hashlib
        from lifeos_hook_bridge.memory_import import _encoded
        review=self.preview()
        self.operation().prepare(self.snapshot,review['signature'],account='dashboard:owner')
        path=self.snapshot/'manifest.json'
        original=json.loads(path.read_bytes())
        for change in ('review_signature','source_digest','chunk_text','missing_source','boolean_size'):
            with self.subTest(change=change):
                document=json.loads(json.dumps(original))
                if change=='review_signature':document['review']['signature']='0'*64
                elif change=='source_digest':document['review']['sources'][0]['digest']='0'*64
                elif change=='chunk_text':document['review']['sources'][0]['chunks'][0]['content']='Different approved text.'
                elif change=='missing_source':document['review']['sources'][0]['status']='missing'
                else:document['files'][0]['size']=True
                if change!='review_signature':
                    checked=dict(document['review']);checked.pop('signature')
                    document['review']['signature']=hashlib.sha256(_encoded(checked)).hexdigest()
                data=_encoded(document);path.write_bytes(data)
                with self.assertRaises(MemoryUnavailable):
                    self.operation().inspect(self.snapshot,hashlib.sha256(data).hexdigest(),account='dashboard:owner')

    def test_source_change_after_last_commit_keeps_the_result_in_conflict(self):
        import subprocess,sys
        saved,plan=self.item_plan()
        settings={'configuration':str(self.configuration.path),'snapshot':str(self.snapshot),
            'source':str(self.sources/'USER.md'),'snapshot_signature':saved['snapshot_signature'],'plan_signature':plan['signature']}
        code='''import json,sys
from pathlib import Path
from lifeos_hook_bridge.memory_service import MemoryConfiguration
from lifeos_hook_bridge.memory_import import MemoryImport
settings=json.loads(sys.stdin.read())
def trace(frame,event,argument):
 if event=='return' and frame.f_code.co_name=='remember' and frame.f_code.co_filename.endswith('/memory_access.py') and frame.f_locals.get('category')=='principal':
  Path(settings['source']).write_text('Later source change.')
 return trace
sys.settrace(trace)
result=MemoryImport(MemoryConfiguration(Path(settings['configuration']))).apply(Path(settings['snapshot']),settings['snapshot_signature'],settings['plan_signature'],account='dashboard:owner')
print(json.dumps({'state':result['state'],'ownership_switch':result['ownership_switch']}))
'''
        child=subprocess.run([sys.executable,'-c',code],input=json.dumps(settings),text=True,capture_output=True,env=os.environ.copy(),timeout=30)
        self.assertEqual(child.returncode,0,child.stdout+child.stderr)
        self.assertEqual(child.stderr,'')
        self.assertEqual(json.loads(child.stdout),{'state':'conflict','ownership_switch':False})
        self.assertEqual(len(self.fixture.memory.recall(fixture.OWNER,'9123')),1)
        self.assertEqual(len(self.fixture.memory.recall(fixture.OWNER,'concise')),1)


if __name__=='__main__':
    unittest.main()
