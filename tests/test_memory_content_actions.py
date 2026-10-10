# ABOUTME: Exercises authenticated Content run requests and disposal through actual native HTTP.
# ABOUTME: Requires complete ledger admission, current owner authority, and safe source effects.
import json
import importlib
from concurrent.futures import ThreadPoolExecutor
import os
import sys
import subprocess
from lifeos_hook_bridge.memory_access import NativeMemory
from pathlib import Path
import unittest
import httpx
import test_memory_content as fixture


class MemoryContentActionTests(unittest.TestCase):
    native_module='content.ts'
    create_fixture=fixture.MemoryContentTests.create_fixture
    stop_dashboard=fixture.MemoryContentTests.stop_dashboard
    stop_pulse=fixture.MemoryContentTests.stop_pulse
    login=fixture.MemoryContentTests.login
    setUp=fixture.MemoryContentTests.setUp
    native_module_name=fixture.MemoryContentTests.native_module_name
    seed=fixture.MemoryContentTests.seed

    def test_owner_run_request_sets_native_flag_once_without_changing_existing_ledger_bytes(self):
        path,_=self.seed(count=1)
        before=path.read_bytes()
        with httpx.Client(timeout=45) as client:
            self.login(client)
            result=client.post(self.native+'/api/content/synthetic0/run')
            self.assertEqual(result.status_code,200,result.text)
            self.assertEqual(result.json(),{'ok':True,'id':'synthetic0','requested_run':'regular'})
            saved=path.read_bytes()
            self.assertTrue(saved.startswith(before))
            self.assertEqual(path.stat().st_mode & 0o777,0o600)
            board=client.get(self.native+'/api/content')
            self.assertEqual(board.status_code,200,board.text)
            self.assertEqual(board.json()['items'][0]['requested_run'],'regular')
            repeated=client.post(self.native+'/api/content/synthetic0/run')
            self.assertEqual(repeated.status_code,200,repeated.text)
            self.assertEqual(repeated.json(),{'ok':True,'id':'synthetic0','already':True})
            self.assertEqual(path.read_bytes(),saved)

    def test_anonymous_actions_refuse_before_ledger_or_source_changes(self):
        path,_=self.seed(count=1)
        before=path.read_bytes()
        self.assertEqual(httpx.post(self.native+'/api/content/synthetic0/run').status_code,401)
        self.assertEqual(httpx.delete(self.native+'/api/content/synthetic0').status_code,401)
        self.assertEqual(path.read_bytes(),before)

    def instrument_plan(self,callback):
        self.fixture.login()
        self.fixture.client.get('/api/plugins/lifeos-hook-bridge/memory/pulse/state')
        module=importlib.import_module('lifeos_memory_settings.memory_access')
        original=module.NativeMemory._native
        seen=[]
        def native(memory,action,**values):
            result=original(memory,action,**values)
            if action=='content_run_plan':
                seen.append(result['status'])
                callback()
            return result
        module.NativeMemory._native=native
        self.addCleanup(setattr,module.NativeMemory,'_native',original)
        return seen

    def test_owner_missing_run_request_keeps_the_complete_ledger(self):
        path,_=self.seed(count=1)
        before=path.read_bytes()
        with httpx.Client(timeout=45) as client:
            self.login(client)
            result=client.post(self.native+'/api/content/missing1/run')
            self.assertEqual(result.status_code,404,result.text)
            self.assertEqual(result.json(),{'error':'no item missing1'})
        self.assertEqual(path.read_bytes(),before)

    def test_excluded_event_refuses_run_before_ledger_append(self):
        path,_=self.seed(marker='<private>Synthetic excluded Content item</private>',count=1)
        before=path.read_bytes()
        with httpx.Client(timeout=45) as client:
            self.login(client)
            result=client.post(self.native+'/api/content/synthetic0/run')
            self.assertEqual(result.status_code,503,result.text)
            self.assertNotIn('Synthetic excluded',result.text)
        self.assertEqual(path.read_bytes(),before)

    def test_source_change_after_actual_plan_keeps_later_ledger_bytes(self):
        path,_=self.seed(count=1)
        later=path.read_bytes()+json.dumps({'v':1,'ts':'2026-10-09T12:00:01Z','id':'synthetic0',
            'op':'upsert','src':'synthetic','fields':{'title':'Synthetic later owner Content title.'}}).encode()+b'\n'
        seen=self.instrument_plan(lambda:path.write_bytes(later))
        with httpx.Client(timeout=45) as client:
            self.login(client)
            result=client.post(self.native+'/api/content/synthetic0/run')
            self.assertEqual(result.status_code,503,result.text)
        self.assertEqual(seen,[200])
        self.assertEqual(path.read_bytes(),later)

    def test_owner_revocation_after_actual_plan_refuses_append(self):
        path,_=self.seed(count=1)
        before=path.read_bytes()
        seen=self.instrument_plan(lambda:self.fixture.configuration.update(lambda value:value['accounts'].pop('dashboard:basic:synthetic-owner')))
        with httpx.Client(timeout=45) as client:
            self.login(client)
            result=client.post(self.native+'/api/content/synthetic0/run')
            self.assertEqual(result.status_code,403,result.text)
        self.assertEqual(seen,[200])
        self.assertEqual(path.read_bytes(),before)

    def test_simultaneous_owner_run_requests_append_one_event_and_each_return_current_native_status(self):
        path,_=self.seed(count=1)
        before=path.read_bytes()
        with httpx.Client(timeout=45) as client:
            self.login(client)
            with ThreadPoolExecutor(max_workers=3) as pool:
                responses=list(pool.map(lambda _:client.post(self.native+'/api/content/synthetic0/run'),range(3)))
            self.assertEqual([response.status_code for response in responses],[200,200,200],
                [response.text for response in responses])
        rows=[json.loads(line) for line in path.read_text().splitlines()]
        self.assertEqual(len(rows),2)
        self.assertTrue(path.read_bytes().startswith(before))
        self.assertEqual(sum(response.json().get('requested_run')=='regular' for response in responses),1)
        self.assertEqual(sum(response.json().get('already') is True for response in responses),2)

    def test_unknown_prototype_named_item_refuses_without_creating_a_card(self):
        path,_=self.seed(count=1)
        before=path.read_bytes()
        with httpx.Client(timeout=45) as client:
            self.login(client)
            result=client.post(self.native+'/api/content/constructor/run')
            self.assertEqual(result.status_code,404,result.text)
        self.assertEqual(path.read_bytes(),before)

    def test_current_repeat_response_withholds_later_source_change_during_validation(self):
        path,rows=self.seed(count=1)
        rows[0]['fields']['requested_run']='regular'
        path.write_text(json.dumps(rows[0])+'\n')
        later=dict(rows[0])
        later['fields']=dict(rows[0]['fields'])
        later['fields'].pop('requested_run')
        data=(json.dumps(later)+'\n').encode()
        self.fixture.login()
        self.fixture.client.get('/api/plugins/lifeos-hook-bridge/memory/pulse/state')
        module=importlib.import_module('lifeos_memory_settings.memory_access')
        original=module.NativeMemory._native
        phase=[]
        def native(memory,action,**values):
            result=original(memory,action,**values)
            if action=='content_run_plan':phase.append('prepared')
            elif phase==['prepared'] and action=='validate_source_batch':
                path.write_bytes(data)
                phase.append('later-source')
            return result
        module.NativeMemory._native=native
        self.addCleanup(setattr,module.NativeMemory,'_native',original)
        with httpx.Client(timeout=45) as client:
            self.login(client)
            result=client.post(self.native+'/api/content/synthetic0/run')
            self.assertEqual(result.status_code,503,result.text)
        self.assertEqual(phase,['prepared','later-source'])
        self.assertEqual(path.read_bytes(),data)

    def test_actual_interrupted_append_restores_the_original_ledger_and_mode(self):
        path,_=self.seed(count=1)
        path.chmod(0o640)
        before=path.read_bytes()
        result=subprocess.run([sys.executable,str(Path(__file__).with_name('memory_content_action_process.py')),
            str(self.fixture.configuration.path),str(self.root)],capture_output=True,text=True,timeout=35,
            env=dict(os.environ,HOME=str(self.fixture.home),HERMES_HOME=str(self.fixture.profile)))
        self.assertEqual((result.returncode,result.stdout,result.stderr),(73,'',''))
        self.assertNotEqual(path.read_bytes(),before)
        with NativeMemory(self.root)._transaction():pass
        self.assertEqual(path.read_bytes(),before)
        self.assertEqual(path.stat().st_mode & 0o777,0o640)

    def test_later_owner_append_after_commit_withholds_the_prior_response(self):
        path,_=self.seed(count=1)
        self.fixture.login()
        self.fixture.client.get('/api/plugins/lifeos-hook-bridge/memory/pulse/state')
        module=importlib.import_module('lifeos_memory_settings.memory_access')
        original=module.NativeMemory._operation
        observed=[]
        def operation(memory,*args,**values):
            result=original(memory,*args,**values)
            if len(args)>2 and args[2].get('operation')=='content_run' and result['status']=='committed':
                with path.open('ab') as output:
                    output.write(json.dumps({'v':1,'ts':'2026-10-09T12:00:01Z','id':'synthetic0',
                        'op':'upsert','src':'synthetic','fields':{'title':'Synthetic later owner append.'}}).encode()+b'\n')
                observed.append(path.read_bytes())
            return result
        module.NativeMemory._operation=operation
        self.addCleanup(setattr,module.NativeMemory,'_operation',original)
        with httpx.Client(timeout=45) as client:
            self.login(client)
            result=client.post(self.native+'/api/content/synthetic0/run')
            self.assertEqual(result.status_code,503,result.text)
        self.assertEqual(observed,[path.read_bytes()])
        self.assertIn(b'Synthetic later owner append.',path.read_bytes())

    def test_unterminated_ledger_refuses_append_without_discarding_the_current_item(self):
        path,_=self.seed(count=1)
        path.write_bytes(path.read_bytes().rstrip(b'\n'))
        before=path.read_bytes()
        with httpx.Client(timeout=45) as client:
            self.login(client)
            result=client.post(self.native+'/api/content/synthetic0/run')
            self.assertEqual(result.status_code,503,result.text)
        self.assertEqual(path.read_bytes(),before)

    def test_large_complete_ledger_keeps_every_prior_byte_when_requesting_the_last_item(self):
        path,_=self.seed(count=1200)
        before=path.read_bytes()
        with httpx.Client(timeout=45) as client:
            self.login(client)
            result=client.post(self.native+'/api/content/synthetic1199/run')
            self.assertEqual(result.status_code,200,result.text)
            self.assertEqual(result.json(),{'ok':True,'id':'synthetic1199','requested_run':'regular'})
        self.assertTrue(path.read_bytes().startswith(before))
        rows=[json.loads(line) for line in path.read_text().splitlines()]
        self.assertEqual(len(rows),1201)
        self.assertEqual(rows[-1]['id'],'synthetic1199')
        self.assertEqual(rows[-1]['fields']['requested_run'],'regular')

    def test_retired_item_refuses_run_before_an_event_can_reintroduce_it(self):
        from test_memory_native import OWNER
        memory=self.fixture.fixture.fixture.fixture.fixture.memory
        saved=memory.remember(OWNER,category='principal',content='RULE: SyntheticContentRunRetired0',
            title='',project='',request_id='content-run-retired-save')
        memory.forget(OWNER,saved['reference'],'content-run-retired-forget')
        path,_=self.seed(marker='SyntheticContentRunRetired',count=1)
        before=path.read_bytes()
        with httpx.Client(timeout=45) as client:
            self.login(client)
            result=client.post(self.native+'/api/content/synthetic0/run')
            self.assertEqual(result.status_code,503,result.text)
            self.assertNotIn('SyntheticContentRunRetired',result.text)
        self.assertEqual(path.read_bytes(),before)
