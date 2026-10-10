# ABOUTME: Exercises the combined native upgrades queue through actual authenticated HTTP sessions.
# ABOUTME: Compares queue, expiry, and review effects while refusing unbound and stale callers.
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import unittest

import httpx
import test_memory_hypothesis_relay as queue_fixture
import test_memory_upgrade_store as store_fixture


class MemoryUpgradeRelayTests(unittest.TestCase):
    native_module='upgrades.ts'
    create_fixture=queue_fixture.MemoryHypothesisRelayTests.create_fixture
    native_module_name=queue_fixture.MemoryHypothesisRelayTests.native_module_name
    stop_dashboard=queue_fixture.MemoryHypothesisRelayTests.stop_dashboard
    stop_pulse=queue_fixture.MemoryHypothesisRelayTests.stop_pulse
    login=queue_fixture.MemoryHypothesisRelayTests.login
    seed_hypothesis=queue_fixture.MemoryHypothesisRelayTests.seed
    seed_upgrade=store_fixture.MemoryUpgradeStoreTests.seed

    def setUp(self):
        queue_fixture.MemoryHypothesisRelayTests.setUp(self)
        self.store=self.root/'LIFEOS/MEMORY/UPGRADES'

    def snapshot(self):
        return {path.relative_to(self.root/'LIFEOS/MEMORY').as_posix():path.read_text()
            for directory in (self.store,self.root/'LIFEOS/MEMORY/WISDOM/FRAMES')
            for path in directory.rglob('*') if path.is_file()}

    def reset(self,contents):
        for directory in (self.store,self.root/'LIFEOS/MEMORY/WISDOM/FRAMES'):
            directory.mkdir(parents=True,exist_ok=True)
            for path in directory.iterdir():
                if path.is_dir():shutil.rmtree(path)
                else:path.unlink()
        for relative,content in contents.items():
            path=self.root/'LIFEOS/MEMORY'/relative
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_text(content)

    def original(self,route,method='GET',note=None):
        control=Path(os.environ['LIFEOS_HARVEST_CONTROL_SOURCE'])
        options={'method':method}
        if method=='POST':options.update(headers={'content-type':'application/json'},body=json.dumps({'note':note}))
        script='import {handleRequest} from '+json.dumps(str(control/'LIFEOS/PULSE/modules/upgrades.ts'))+';'+\
            'const response=await handleRequest(new Request("http://127.0.0.1"+'+json.dumps(route)+','+json.dumps(options)+'),'+json.dumps(route)+');'+\
            'if(!response)throw new Error("Missing native response");console.log(JSON.stringify({status:response.status,body:await response.json()}));'
        result=subprocess.run(['bun','--no-install','-e',script],capture_output=True,text=True,timeout=40,
            env=dict(os.environ,HOME=str(self.fixture.home),LIFEOS_DIR=str(self.root/'LIFEOS'),LIFEOS_MEMORY_INTERNAL='1'))
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(result.stderr,'')
        return json.loads(result.stdout)

    def normalize(self,values):
        return {name:re.sub(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z','SyntheticInstant',text)
            for name,text in values.items()}

    def test_native_queue_and_detail_fields_match_original(self):
        self.seed_upgrade()
        self.seed_hypothesis()
        with httpx.Client(timeout=30) as client:
            self.login(client)
            for route in ('/api/upgrades','/api/upgrades/synthetic-upgrade',
                    '/api/upgrades/hyp:synthetic-hypothesis','/api/upgrades/missing-upgrade'):
                expected=self.original(route)
                response=client.get(self.native+route)
                self.assertEqual({'status':response.status_code,'body':response.json()},expected)

    def test_anonymous_index_cannot_publish_expiry(self):
        self.seed_upgrade(expired=True)
        before=self.snapshot()
        response=httpx.get(self.native+'/api/upgrades',timeout=30)
        with self.subTest(effect='publication'):self.assertEqual(self.snapshot(),before)
        with self.subTest(effect='response'):self.assertEqual(response.status_code,401,response.text)

    def test_anonymous_details_and_actions_cannot_borrow_ambient_owner(self):
        self.seed_upgrade()
        self.seed_hypothesis()
        before=self.snapshot()
        for method,route in (('GET','/api/upgrades/synthetic-upgrade'),('GET','/api/upgrades/hyp:synthetic-hypothesis'),
                ('POST','/api/upgrades/synthetic-upgrade/accept'),('POST','/api/upgrades/hyp:synthetic-hypothesis/reject')):
            with self.subTest(method=method,route=route):
                self.reset(before)
                response=httpx.request(method,self.native+route,headers={'X-LifeOS-Owner':'owner'},
                    json={} if method=='POST' else None,timeout=30)
                self.assertEqual(response.status_code,401,response.text)
                self.assertEqual(self.snapshot(),before)

    def test_owner_index_preserves_native_expiry_and_queue_effects(self):
        self.seed_upgrade(expired=True)
        self.seed_hypothesis()
        before=self.snapshot()
        expected=self.original('/api/upgrades')
        effects=self.snapshot()
        self.assertIn('status: expired',effects['UPGRADES/records/synthetic-upgrade.md'])
        self.reset(before)
        with httpx.Client(timeout=30) as client:
            self.login(client)
            response=client.get(self.native+'/api/upgrades')
            self.assertEqual({'status':response.status_code,'body':response.json()},expected)
            self.assertEqual(self.normalize(self.snapshot()),self.normalize(effects))
            self.assertEqual(response.headers.get('cache-control'),'no-store')

    def test_owner_record_and_hypothesis_actions_match_original_effects(self):
        self.seed_upgrade()
        self.seed_hypothesis()
        before=self.snapshot()
        with httpx.Client(timeout=30) as client:
            self.login(client)
            for identifier in ('synthetic-upgrade','hyp:synthetic-hypothesis'):
                for verb in ('accept','reject'):
                    with self.subTest(identifier=identifier,verb=verb):
                        self.reset(before)
                        route='/api/upgrades/'+identifier+'/'+verb
                        expected=self.original(route,'POST','Synthetic combined queue review')
                        effects=self.snapshot()
                        self.reset(before)
                        response=client.post(self.native+route,json={'note':'Synthetic combined queue review'})
                        self.assertEqual({'status':response.status_code,'body':response.json()},expected)
                        self.assertEqual(self.normalize(self.snapshot()),self.normalize(effects))
                        self.assertEqual(response.headers.get('cache-control'),'no-store')

    def test_revoked_owner_cannot_read_or_publish_expiry_or_reviews(self):
        self.seed_upgrade(expired=True)
        self.seed_hypothesis()
        before=self.snapshot()
        with httpx.Client(timeout=30) as client:
            self.login(client)
            self.fixture.configuration.update(lambda value:value['accounts'].clear())
            for method,route in (('GET','/api/upgrades'),('GET','/api/upgrades/hyp:synthetic-hypothesis'),
                    ('POST','/api/upgrades/synthetic-upgrade/accept'),('POST','/api/upgrades/hyp:synthetic-hypothesis/reject')):
                with self.subTest(method=method,route=route):
                    response=client.request(method,self.native+route,json={} if method=='POST' else None)
                    self.assertEqual(response.status_code,403,response.text)
                    self.assertEqual(self.snapshot(),before)

    def test_connector_loss_never_falls_back_to_raw_sources_or_expiry(self):
        self.seed_upgrade()
        self.seed_hypothesis()
        with httpx.Client(timeout=30) as client:
            self.login(client)
            self.assertEqual(client.get(self.native+'/api/upgrades').status_code,200)
            self.seed_upgrade(expired=True)
            before=self.snapshot()
            (self.root/'LIFEOS/USER/CONFIG/memory-access.json').unlink()
            for method,route in (('GET','/api/upgrades'),('POST','/api/upgrades/hyp:synthetic-hypothesis/accept')):
                response=client.request(method,self.native+route,json={} if method=='POST' else None)
                self.assertEqual(response.status_code,503,response.text)
                self.assertEqual(self.snapshot(),before)

    def test_current_record_hypothesis_and_account_are_rechecked_after_actual_render(self):
        import sys
        for mode in ('record','hypothesis','authority'):
            with self.subTest(mode=mode):
                self.seed_upgrade()
                self.seed_hypothesis()
                result=subprocess.run([sys.executable,str(Path(__file__).with_name('memory_upgrade_queue_process.py')),
                    str(self.fixture.configuration.path),mode],capture_output=True,text=True,timeout=40,
                    env=dict(os.environ,PYTHONPATH=str(Path(__file__).resolve().parents[1])))
                self.assertEqual(result.returncode,0,result.stderr)
                self.assertEqual(json.loads(result.stdout),{'rendered':True,'withheld':True})

    def test_retired_records_and_hypotheses_remain_on_disk_and_leave_queue(self):
        from test_memory_native import OWNER
        memory=self.fixture.fixture.fixture.fixture.fixture.memory
        paths=[]
        for name in ('Upgrade','Hypothesis'):
            marker='Synthetic'+name+'ForgottenMarker'
            saved=memory.remember(OWNER,category='principal',content='RULE: '+marker,title='',project='',
                request_id='synthetic-combined-retained-'+name)
            self.assertEqual(saved['status'],'committed',saved)
            paths.append(self.seed_upgrade(claim=marker) if name=='Upgrade' else self.seed_hypothesis(claim=marker))
            memory.forget(OWNER,saved['reference'],'synthetic-combined-forgotten-'+name)
        before=self.snapshot()
        with httpx.Client(timeout=30) as client:
            self.login(client)
            body=client.get(self.native+'/api/upgrades').json()
            self.assertEqual(body['stats']['pending'],0,body)
            for identifier in ('synthetic-upgrade','hyp:synthetic-hypothesis'):
                self.assertEqual(client.get(self.native+'/api/upgrades/'+identifier).status_code,404)
                self.assertEqual(client.post(self.native+'/api/upgrades/'+identifier+'/accept',json={}).status_code,404)
        self.assertEqual(self.snapshot(),before)
        self.assertTrue(all(path.exists() for path in paths))

    def test_private_records_and_hypotheses_never_enter_queue_or_review(self):
        paths=[self.seed_upgrade(claim='<private>Synthetic private upgrade</private>'),
            self.seed_hypothesis(claim='<private>Synthetic private hypothesis</private>')]
        before=self.snapshot()
        with httpx.Client(timeout=30) as client:
            self.login(client)
            response=client.get(self.native+'/api/upgrades')
            self.assertEqual(response.status_code,200,response.text)
            self.assertEqual(response.json()['recommended'],[])
            for identifier in ('synthetic-upgrade','hyp:synthetic-hypothesis'):
                self.assertEqual(client.post(self.native+'/api/upgrades/'+identifier+'/accept',json={}).status_code,404)
        self.assertEqual(self.snapshot(),before)
        self.assertTrue(all(path.exists() for path in paths))

    def test_cross_origin_and_invalid_bearer_cannot_use_valid_owner_cookies(self):
        self.seed_upgrade(expired=True)
        self.seed_hypothesis()
        before=self.snapshot()
        with httpx.Client(timeout=30) as client:
            self.login(client)
            for method,route in (('GET','/api/upgrades'),('POST','/api/upgrades/synthetic-upgrade/accept')):
                for headers,status in (({'Origin':'https://untrusted.invalid'},403),
                        ({'Authorization':'Bearer synthetic-invalid'},401)):
                    with self.subTest(method=method,headers=headers):
                        response=client.request(method,self.native+route,headers=headers,json={} if method=='POST' else None)
                        self.assertEqual(response.status_code,status,response.text)
                        self.assertEqual(self.snapshot(),before)

    def test_fixed_routes_and_bounded_body_cannot_select_another_source(self):
        self.seed_upgrade()
        self.seed_hypothesis()
        before=self.snapshot()
        with httpx.Client(timeout=30) as client:
            self.login(client)
            for route in ('/api/upgrades?owner=other','/api/upgrades/%2Fsecret','/api/upgrades/%25secret',
                    '/api/upgrades/hyp:../secret','/api/upgrades/missing/action'):
                with self.subTest(route=route):
                    response=client.get(self.native+route)
                    self.assertIn(response.status_code,(400,404),response.text)
            for payload in ({'note':{}},{'note':'x'*8193},{'owner':'other'},[],{'note':'x'*32768}):
                with self.subTest(payload_type=type(payload).__name__,length=len(str(payload))):
                    response=client.post(self.native+'/api/upgrades/synthetic-upgrade/accept',json=payload)
                    self.assertEqual(response.status_code,400,response.text)
            self.assertEqual(client.post(self.native+'/api/upgrades/synthetic-upgrade/accept?owner=other',json={}).status_code,400)
            self.assertEqual(client.put(self.native+'/api/upgrades').status_code,405)
        self.assertEqual(self.snapshot(),before)

    def test_missing_and_illegal_native_actions_preserve_responses_and_sources(self):
        self.seed_upgrade(status='verified')
        before=self.snapshot()
        with httpx.Client(timeout=30) as client:
            self.login(client)
            for identifier in ('missing-upgrade','hyp:missing-hypothesis','synthetic-upgrade'):
                for verb in ('accept','reject'):
                    with self.subTest(identifier=identifier,verb=verb):
                        route='/api/upgrades/'+identifier+'/'+verb
                        expected=self.original(route,'POST')
                        self.reset(before)
                        response=client.post(self.native+route,json={})
                        self.assertEqual({'status':response.status_code,'body':response.json()},expected)
                        self.assertEqual(self.snapshot(),before)

    def test_private_review_note_cannot_enter_upgrade_or_hypothesis_sources(self):
        self.seed_upgrade()
        self.seed_hypothesis()
        before=self.snapshot()
        with httpx.Client(timeout=30) as client:
            self.login(client)
            for identifier in ('synthetic-upgrade','hyp:synthetic-hypothesis'):
                response=client.post(self.native+'/api/upgrades/'+identifier+'/reject',
                    json={'note':'<private>Synthetic private review note</private>'})
                self.assertEqual(response.status_code,503,response.text)
                self.assertEqual(response.json(),{'error':'Authenticated memory is unavailable'})
                self.assertEqual(self.snapshot(),before)

    def test_missing_hypothesis_with_existing_directory_preserves_native_reason(self):
        self.seed_hypothesis()
        before=self.snapshot()
        with httpx.Client(timeout=30) as client:
            self.login(client)
            route='/api/upgrades/hyp:missing-hypothesis/reject'
            expected=self.original(route,'POST')
            response=client.post(self.native+route,json={})
            self.assertEqual({'status':response.status_code,'body':response.json()},expected)
        self.assertEqual(self.snapshot(),before)

    def test_healing_fixture_absence_retains_pending_note_and_native_failure(self):
        path=self.seed_hypothesis()
        path.write_text(path.read_text().replace('falsifier: Synthetic falsifier',
            'enforcement_surface: hook\nfalsifier: Synthetic falsifier')+\
            '\n## Proposed Healing Fixture (RED '+chr(0x2014)+' proves the gap is real)\n'+\
            'pending: `test/regression/pending/synthetic-fixture/`\n')
        before=self.snapshot()
        route='/api/upgrades/hyp:synthetic-hypothesis/accept'
        expected=self.original(route,'POST')
        self.assertEqual(expected['status'],409,expected)
        self.assertEqual(expected['body']['reason'],'patch_still_red',expected)
        self.assertEqual(self.snapshot(),before)
        with httpx.Client(timeout=30) as client:
            self.login(client)
            response=client.post(self.native+route,json={})
            self.assertEqual({'status':response.status_code,'body':response.json()},expected)
        self.assertEqual(self.snapshot(),before)

    def test_completed_review_retry_preserves_later_edits_and_native_receipt(self):
        import sys
        from lifeos_hook_bridge.memory_preferences import MemoryPreferences
        self.seed_upgrade()
        preferences=MemoryPreferences(self.fixture.configuration.path,self.root,Path(sys.executable),
            Path(__file__).resolve().parents[1]/'lifeos_hook_bridge/memory_rpc.py')
        arguments={'target':'/api/upgrades/synthetic-upgrade/accept','note':'Synthetic retry note',
            'request_id':'synthetic-combined-retry','account':'dashboard:basic:synthetic-owner'}
        first=preferences.review_upgrade(**arguments)
        path=self.store/'records/synthetic-upgrade.md'
        path.write_text(path.read_text()+'\nSynthetic later retained edit\n')
        before=self.snapshot()
        self.assertEqual(preferences.review_upgrade(**arguments),first)
        self.assertEqual(self.snapshot(),before)
