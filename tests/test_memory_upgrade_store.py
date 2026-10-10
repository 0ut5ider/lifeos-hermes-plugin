# ABOUTME: Calls the actual native upgrade store with current owner contexts and synthetic records.
# ABOUTME: Characterizes list, creation, transitions, expiry, refusal, and retained source policy.
from dataclasses import asdict
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import unittest

import test_memory_hypothesis_helpers as helpers
from test_memory_native import OWNER
from lifeos_hook_bridge.memory_service import MemoryService
from lifeos_hook_bridge.memory_access import MemoryUnavailable


class MemoryUpgradeStoreTests(unittest.TestCase):
    def setUp(self):
        self.fixture=helpers.MemoryHypothesisHelpersTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.owner=self.fixture.fixture
        self.root=self.fixture.root
        self.store=self.root/'LIFEOS/MEMORY/UPGRADES'
        self.owner.configuration.update(lambda value:value['destinations']['chat-a:200'].update(proposals=['create','approve']))

    def seed(self,*,status='recommended',expired=False,claim='SyntheticUpgradeCurrentMarker'):
        path=self.store/'records/synthetic-upgrade.md'
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text('---\nid: synthetic-upgrade\nslug: synthetic-upgrade\nstatus: '+status+'\nsource: manual\n'
            'created: 2026-10-08T00:00:00.000Z\nexpires: '+('2026-01-01' if expired else '2027-01-01')+'T00:00:00.000Z\n'
            'confidence: 0.7\ntarget_surface: context\nsession_id: synthetic-seed\nledger_id: \nevidence:\n'
            '  - "synthetic-evidence"\n---\n\n## Claim\n\n'+claim+'\n\n## Current State\n\nSynthetic current state\n\n'
            '## Recommendation\n\nSynthetic recommendation\n\n## Notes\n\n- Synthetic seed note\n')
        return path

    def snapshot(self):
        return {path.relative_to(self.store).as_posix():path.read_text() for path in self.store.rglob('*') if path.is_file()}

    def reset(self,contents):
        self.store.mkdir(parents=True,exist_ok=True)
        for path in self.store.iterdir():
            if path.is_dir():shutil.rmtree(path)
            else:path.unlink()
        for name,content in contents.items():
            path=self.store/name
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_text(content)

    def call(self,action,arguments=None,*,context=True,original=False):
        source=Path(os.environ['LIFEOS_UPGRADE_CONTROL_SOURCE']) if original else self.root
        module=source/'LIFEOS/TOOLS/Upgrades.ts'
        arguments=arguments or {}
        values={
            'list':'listUpgrades('+json.dumps(arguments.get('filter'))+')',
            'get':'getUpgrade('+json.dumps(arguments.get('id','synthetic-upgrade'))+')',
            'add':'addUpgrade('+json.dumps(arguments.get('input',{'claim':'Synthetic new upgrade claim',
                'source':'manual','session_id':self.owner.context.session_id}))+')',
            'status':'setStatus('+json.dumps(arguments.get('id','synthetic-upgrade'))+','+
                json.dumps(arguments.get('status','accepted'))+','+json.dumps(arguments.get('opts',{'note':'Synthetic review note'}))+')',
            'expire':'expireSweep()',
        }
        script='import {listUpgrades,getUpgrade,addUpgrade,setStatus,expireSweep} from '+json.dumps(str(module))+';'+\
            'console.log(JSON.stringify('+values[action]+'));'
        environment=dict(os.environ,HOME=str(self.owner.fixture.home),LIFEOS_DIR=str(self.root/'LIFEOS'),
            BUN_CONFIG_NO_AUTO_INSTALL='1')
        environment.pop('LIFEOS_MEMORY_INTERNAL',None)
        environment.pop('LIFEOS_MEMORY_CONTEXT',None)
        if context:environment['LIFEOS_MEMORY_CONTEXT']=json.dumps(asdict(self.owner.context))
        return subprocess.run(['bun','--no-install','-e',script],env=environment,capture_output=True,text=True,timeout=40)

    def normalize(self,values):
        replace=lambda text:re.sub(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z','SyntheticInstant',
            re.sub(r'\d{8}-\d{6}_','SyntheticId_',text))
        return {replace(name):replace(content) for name,content in values.items()}

    def test_list_and_get_preserve_all_original_fields(self):
        self.seed()
        for action in ('list','get'):
            expected=self.call(action,original=True)
            actual=self.call(action)
            self.assertEqual(expected.returncode,0,expected.stderr)
            self.assertEqual(actual.returncode,0,actual.stderr)
            self.assertEqual(actual.stderr,'')
            self.assertEqual(json.loads(actual.stdout),json.loads(expected.stdout))

    def test_native_add_status_and_expiry_preserve_selected_file_effects(self):
        self.seed(expired=True)
        before=self.snapshot()
        for action in ('add','status','expire'):
            with self.subTest(action=action):
                self.reset(before)
                expected=self.call(action,original=True)
                self.assertEqual(expected.returncode,0,expected.stderr)
                effects=self.snapshot()
                self.reset(before)
                actual=self.call(action)
                self.assertEqual(actual.returncode,0,actual.stderr)
                self.assertEqual(actual.stderr,'')
                if action=='add':
                    self.assertTrue(json.loads(actual.stdout)['created'])
                    self.assertTrue(json.loads(expected.stdout)['created'])
                else:self.assertEqual(json.loads(actual.stdout),json.loads(expected.stdout))
                self.assertEqual(self.normalize(self.snapshot()),self.normalize(effects))

    def test_unbound_native_store_cannot_read_or_mutate(self):
        self.seed(expired=True)
        before=self.snapshot()
        for action in ('list','get','add','status','expire'):
            with self.subTest(action=action):
                self.reset(before)
                result=self.call(action,context=False)
                self.assertNotEqual(result.returncode,0,result.stdout)
                self.assertEqual(self.snapshot(),before)

    def test_revoked_native_store_cannot_read_or_mutate(self):
        self.seed(expired=True)
        before=self.snapshot()
        self.owner.configuration.update(lambda value:value['accounts'].clear())
        for action in ('list','get','add','status','expire'):
            with self.subTest(action=action):
                self.reset(before)
                result=self.call(action)
                self.assertNotEqual(result.returncode,0,result.stdout)
                self.assertEqual(self.snapshot(),before)

    def test_read_only_owner_keeps_reads_and_cannot_mutate(self):
        self.seed(expired=True)
        before=self.snapshot()
        self.owner.configuration.update(lambda value:value['destinations']['chat-a:200'].update(write=[]))
        for action in ('list','get'):
            result=self.call(action)
            self.assertEqual(result.returncode,0,result.stderr)
        for action in ('add','status','expire'):
            with self.subTest(action=action):
                self.reset(before)
                result=self.call(action)
                self.assertNotEqual(result.returncode,0,result.stdout)
                self.assertEqual(self.snapshot(),before)

    def test_forgotten_record_remains_retained_and_leaves_native_views(self):
        marker='SyntheticUpgradeForgottenMarker'
        saved=self.owner.fixture.memory.remember(OWNER,category='principal',content='RULE: '+marker,
            title='',project='',request_id='synthetic-upgrade-retained')
        self.assertEqual(saved['status'],'committed',saved)
        path=self.seed(claim=marker)
        self.owner.fixture.memory.forget(OWNER,saved['reference'],'synthetic-upgrade-retire')
        result=self.call('list')
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(json.loads(result.stdout),[])
        result=self.call('get')
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertIsNone(json.loads(result.stdout))
        self.assertTrue(path.exists())

    def test_private_creation_never_changes_record_or_state(self):
        self.seed()
        before=self.snapshot()
        result=self.call('add',{'input':{'claim':'<private>Synthetic private upgrade</private>','source':'manual'}})
        self.assertNotEqual(result.returncode,0,result.stdout)
        self.assertEqual(self.snapshot(),before)

    def test_original_terminal_status_refuses_an_illegal_transition_without_writing(self):
        self.seed(status='verified')
        before=self.snapshot()
        result=self.call('status',original=True)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(json.loads(result.stdout),{'ok':False,'reason':'illegal_transition_verified_to_accepted'})
        self.assertEqual(self.snapshot(),before)

    def test_invalid_expiry_preserves_original_skip_without_publication(self):
        path=self.seed()
        path.write_text(path.read_text().replace('2027-01-01T00:00:00.000Z','synthetic-invalid-expiry'))
        before=self.snapshot()
        for original in (True,False):
            with self.subTest(original=original):
                self.reset(before)
                result=self.call('expire',original=original)
                self.assertEqual(result.returncode,0,result.stderr)
                self.assertEqual(json.loads(result.stdout),0)
                self.assertEqual(self.snapshot(),before)

    def probe(self,mode):
        return subprocess.run([sys.executable,str(Path(__file__).with_name('memory_upgrade_store_process.py')),
            str(self.owner.configuration.path),json.dumps(asdict(self.owner.context)),mode],
            capture_output=True,text=True,timeout=40,
            env=dict(os.environ,PYTHONPATH=str(Path(__file__).resolve().parents[1])))

    def test_source_and_authority_change_after_real_planning_withhold_publication(self):
        for mode in ('source','authority'):
            with self.subTest(mode=mode):
                self.seed()
                result=self.probe(mode)
                self.assertEqual(result.returncode,0,result.stderr)
                parsed=json.loads(result.stdout)
                self.assertTrue(parsed['rendered'])
                self.assertTrue(parsed['withheld'],parsed)
                self.assertEqual(len(list((self.store/'records').glob('*.md'))),1)
                self.assertFalse((self.store/'.state.json').exists())

    def test_later_record_and_state_survive_real_planning_conflicts(self):
        self.seed()
        before=self.snapshot()
        for mode in ('record','state'):
            with self.subTest(mode=mode):
                self.reset(before)
                result=self.probe(mode)
                self.assertEqual(result.returncode,0,result.stderr)
                parsed=json.loads(result.stdout)
                self.assertTrue(parsed['rendered'])
                self.assertTrue(parsed['withheld'],parsed)
                self.assertTrue(any('later' in content for content in self.snapshot().values()))

    def test_each_interrupted_upgrade_publication_recovers_original_store(self):
        self.seed(expired=True)
        before=self.snapshot()
        for mode in ('interrupt-add-record','interrupt-add-state','interrupt-status-record','interrupt-expiry-record'):
            with self.subTest(mode=mode):
                self.reset(before)
                result=self.probe(mode)
                self.assertEqual(result.returncode,73,result.stderr)
                self.owner.fixture.memory.read_hot(OWNER,'principal')
                self.assertEqual(self.snapshot(),before)

    def test_recovery_preserves_a_later_edit_to_an_interrupted_record(self):
        self.seed()
        result=self.probe('interrupt-add-record')
        self.assertEqual(result.returncode,73,result.stderr)
        path=next(path for path in (self.store/'records').glob('*.md') if path.name!='synthetic-upgrade.md')
        path.write_text('Synthetic later interrupted record edit')
        before=self.snapshot()
        with self.assertRaisesRegex(MemoryUnavailable,'later'):
            self.owner.fixture.memory.read_hot(OWNER,'principal')
        self.assertEqual(self.snapshot(),before)

    def test_authority_revocation_between_record_and_state_recovers_store(self):
        self.seed()
        before=self.snapshot()
        result=self.probe('revoke-after-record')
        self.assertEqual(result.returncode,0,result.stderr)
        parsed=json.loads(result.stdout)
        self.assertTrue(parsed['withheld'],parsed)
        self.owner.fixture.memory.read_hot(OWNER,'principal')
        self.assertEqual(self.snapshot(),before)

    def test_completed_retry_reuses_receipt_and_preserves_later_edits(self):
        self.seed()
        service=MemoryService(self.owner.configuration)
        request={'action':'status','arguments':{'id':'synthetic-upgrade','status':'accepted','opts':{'note':'Synthetic retry note'}},
            'request_id':'synthetic-upgrade-retry'}
        first=service.native(self.owner.context,'upgrade_store',request)
        self.assertTrue(first['ok'],first)
        path=self.store/'records/synthetic-upgrade.md'
        path.write_text(path.read_text()+'\nSynthetic later edit\n')
        before=self.snapshot()
        second=service.native(self.owner.context,'upgrade_store',request)
        self.assertEqual(second,first)
        self.assertEqual(self.snapshot(),before)

    def test_concurrent_creations_preserve_one_record_and_native_dedup_state(self):
        self.seed()
        service=MemoryService(self.owner.configuration)
        def create(index):
            return service.native(self.owner.context,'upgrade_store',{'action':'add',
                'arguments':{'input':{'claim':'Synthetic concurrent upgrade claim','source':'manual'}},
                'request_id':'synthetic-upgrade-concurrent-'+str(index)})
        with ThreadPoolExecutor(max_workers=4) as pool:results=list(pool.map(create,range(4)))
        created=[value for value in results if value.get('ok') and value['result'].get('created')]
        self.assertEqual(len(created),1,results)
        files=list((self.store/'records').glob('*.md'))
        self.assertEqual(len(files),2)
        state=json.loads((self.store/'.state.json').read_text())
        self.assertEqual(len(state['claim_hashes']),1)
        self.assertEqual(next(iter(state['claim_hashes'].values()))['id'],created[0]['result']['id'])

    def test_native_creation_uses_authenticated_session_and_private_files(self):
        self.seed()
        result=self.call('add',{'input':{'claim':'Synthetic attributed upgrade claim','source':'manual',
            'session_id':'synthetic-forged-session'}})
        self.assertEqual(result.returncode,0,result.stderr)
        record=self.store/'records'/(json.loads(result.stdout)['id']+'.md')
        self.assertIn('session_id: '+self.owner.context.session_id,record.read_text())
        self.assertNotIn('synthetic-forged-session',record.read_text())
        for path in (record,self.store/'.state.json'):
            self.assertEqual(path.stat().st_mode&0o777,0o600)

    def test_malformed_state_remains_for_explicit_recovery(self):
        self.seed()
        (self.store/'.state.json').write_text('synthetic malformed state')
        before=self.snapshot()
        original=self.call('add',original=True)
        self.assertEqual(original.returncode,0,original.stderr)
        self.assertTrue(json.loads(original.stdout)['created'])
        self.assertNotEqual(self.snapshot()['.state.json'],before['.state.json'])
        self.reset(before)
        actual=self.call('add')
        self.assertNotEqual(actual.returncode,0,actual.stdout)
        self.assertEqual(self.snapshot(),before)

    def test_invalid_request_fields_refuse_without_native_publication(self):
        self.seed()
        before=self.snapshot()
        service=MemoryService(self.owner.configuration)
        for action,arguments in (('get',{'id':'../other'}),('status',{'id':'synthetic-upgrade','status':{},'opts':None}),
                ('add',{'input':{'claim':'Synthetic invalid upgrade claim','source':{}}}),
                ('add',{'input':{'claim':'Synthetic invalid upgrade claim','source':'manual','path':'/other'}})):
            with self.subTest(action=action,arguments=arguments):
                result=service.native(self.owner.context,'upgrade_store',{'action':action,'arguments':arguments,
                    'request_id':'synthetic-invalid-upgrade'})
                self.assertFalse(result['ok'],result)
                self.assertEqual(self.snapshot(),before)

    def test_proposal_grants_are_required_for_upgrade_mutations(self):
        self.seed(expired=True)
        before=self.snapshot()
        self.owner.configuration.update(lambda value:value['destinations']['chat-a:200'].update(proposals=[]))
        for action in ('add','status','expire'):
            with self.subTest(action=action):
                result=self.call(action)
                self.assertNotEqual(result.returncode,0,result.stdout)
                self.assertEqual(self.snapshot(),before)

    def test_redirected_record_refuses_without_changing_external_content(self):
        path=self.seed()
        external=self.root.parent/'synthetic-external-upgrade.md'
        external.write_text(path.read_text())
        path.unlink()
        path.symlink_to(external)
        before=external.read_bytes()
        for action in ('list','get','status','expire'):
            with self.subTest(action=action):
                result=self.call(action)
                self.assertNotEqual(result.returncode,0,result.stdout)
                self.assertEqual(external.read_bytes(),before)

    def test_registered_fact_source_cannot_change_status(self):
        marker='RULE: Synthetic registered upgrade fact'
        saved=self.owner.fixture.memory.remember(OWNER,category='project',content=marker,
            title='Synthetic upgrade',project='synthetic',request_id='synthetic-upgrade-fact')
        self.assertEqual(saved['status'],'committed',saved)
        path=self.seed()
        path.write_text(path.read_text()+'\n'+marker+'\n')
        with self.owner.fixture.memory._transaction() as connection:
            connection.execute('UPDATE records SET path=?,position=? WHERE id=?',
                (path.relative_to(self.root).as_posix(),path.read_text().index(marker),saved['reference']['id']))
        self.assertEqual(self.owner.fixture.memory.get(OWNER,saved['reference'])['content'],marker)
        before=self.snapshot()
        result=self.call('status')
        self.assertNotEqual(result.returncode,0,result.stdout)
        self.assertEqual(self.snapshot(),before)
        self.assertEqual(self.owner.fixture.memory.get(OWNER,saved['reference'])['content'],marker)

    def test_standalone_store_preserves_native_unbound_mutations(self):
        self.seed(expired=True)
        (self.root/'LIFEOS/USER/CONFIG/memory-access.json').unlink()
        for action in ('list','get','add','status','expire'):
            result=self.call(action,context=False)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual(result.stderr,'')

    def test_all_native_status_transitions_match_results_and_file_effects(self):
        statuses=('recommended','accepted','applied','verified','rejected','expired')
        for start in statuses:
            for status in statuses:
                with self.subTest(start=start,status=status):
                    path=self.seed(status=start)
                    before=self.snapshot()
                    arguments={'status':status,'opts':{'note':'Synthetic transition note','ledger_id':'synthetic-ledger'}}
                    expected=self.call('status',arguments,original=True)
                    self.assertEqual(expected.returncode,0,expected.stderr)
                    effects=self.snapshot()
                    self.reset(before)
                    actual=self.call('status',arguments)
                    self.assertEqual(actual.returncode,0,actual.stderr)
                    self.assertEqual(actual.stderr,'')
                    self.assertEqual(json.loads(actual.stdout),json.loads(expected.stdout))
                    self.assertEqual(self.normalize(self.snapshot()),self.normalize(effects))
