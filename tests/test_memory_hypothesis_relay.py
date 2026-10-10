# ABOUTME: Exercises the actual native hypothesis queue through authenticated Hermes HTTP sessions.
# ABOUTME: Checks native read fidelity, authority, source retirement, and connector loss.
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

import httpx
from test_memory_native import OWNER
import test_memory_pulse_relay as relay_fixture


class MemoryHypothesisRelayTests(unittest.TestCase):
    native_module='hypotheses.ts'
    setUp=relay_fixture.MemoryPulseRelayTests.setUp
    create_fixture=relay_fixture.MemoryPulseRelayTests.create_fixture
    native_module_name=relay_fixture.MemoryPulseRelayTests.native_module_name
    stop_dashboard=relay_fixture.MemoryPulseRelayTests.stop_dashboard
    stop_pulse=relay_fixture.MemoryPulseRelayTests.stop_pulse
    login=relay_fixture.MemoryPulseRelayTests.login

    def seed(self,claim='SyntheticHypothesisCurrentMarker'):
        path=self.root/'LIFEOS/MEMORY/WISDOM/FRAMES/_hypotheses/2026-10-08_synthetic-hypothesis.md'
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text('---\nslug: synthetic-hypothesis\nstatus: hypothesis\ntarget_frame: new\nconfidence: 0.7\n'
            'generated: 2026-10-08\nexpires: 2026-11-01\nevidence_signals:\n  - synthetic-signal\n'
            'falsifier: Synthetic falsifier\n---\n## Claim\n'+claim+'\n\n## Evidence\nSynthetic evidence\n\n'
            '## Suggested Action\nSynthetic action\n')
        return path

    def original(self,route):
        control=Path(os.environ.get('LIFEOS_HARVEST_CONTROL_SOURCE',str(Path.home()/
            '.cache/lifeos-daily-text-20261007/background-control-source/LifeOS/install')))
        script='import {handleRequest} from '+json.dumps(str(control/'LIFEOS/PULSE/modules/hypotheses.ts'))+';'+\
            'const response=await handleRequest(new Request("http://127.0.0.1"+'+json.dumps(route)+'),'+json.dumps(route)+');'+\
            'if(!response)throw new Error("Missing native response");console.log(await response.text());'
        result=subprocess.run(['bun','--no-install','-e',script],capture_output=True,text=True,timeout=40,
            env=dict(os.environ,HOME=str(self.fixture.home),LIFEOS_DIR=str(self.root/'LIFEOS')))
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(result.stderr,'')
        return json.loads(result.stdout)

    def test_native_queue_and_detail_fields_match_the_pinned_original(self):
        self.seed()
        with httpx.Client(timeout=20) as client:
            self.login(client)
            for route in ('/api/hypotheses','/api/hypotheses/synthetic-hypothesis'):
                response=client.get(self.native+route)
                self.assertEqual(response.status_code,200,response.text)
                self.assertEqual(response.json(),self.original(route))

    def test_anonymous_queue_and_detail_do_not_borrow_ambient_owner(self):
        self.seed()
        for route in ('/api/hypotheses','/api/hypotheses/synthetic-hypothesis'):
            response=httpx.get(self.native+route,headers={'X-LifeOS-Owner':'owner'},timeout=20)
            self.assertEqual(response.status_code,401,response.text)
            self.assertNotIn('SyntheticHypothesis',response.text)

    def test_authenticated_queue_and_detail_match_original_native_rendering(self):
        self.seed()
        with httpx.Client(timeout=20) as client:
            self.login(client)
            for route in ('/api/hypotheses','/api/hypotheses/synthetic-hypothesis'):
                response=client.get(self.native+route)
                self.assertEqual(response.status_code,200,response.text)
                self.assertEqual(response.json(),self.original(route))
                self.assertEqual(response.headers.get('cache-control'),'no-store')

    def test_live_account_revocation_withholds_queue_and_detail(self):
        self.seed()
        with httpx.Client(timeout=20) as client:
            self.login(client)
            self.assertEqual(client.get(self.native+'/api/hypotheses').status_code,200)
            self.fixture.configuration.update(lambda value:value['accounts'].pop('dashboard:basic:synthetic-owner'))
            for route in ('/api/hypotheses','/api/hypotheses/synthetic-hypothesis'):
                response=client.get(self.native+route)
                self.assertEqual(response.status_code,403,response.text)
                self.assertNotIn('SyntheticHypothesis',response.text)

    def test_forgotten_text_leaves_retained_note_and_disappears_from_queue(self):
        memory=self.fixture.fixture.fixture.fixture.fixture.memory
        saved=memory.remember(OWNER,category='principal',content='RULE: SyntheticHypothesisForgottenMarker',
            title='',project='',request_id='synthetic-hypothesis-retirement')
        path=self.seed('SyntheticHypothesisForgottenMarker')
        with httpx.Client(timeout=20) as client:
            self.login(client)
            self.assertEqual(client.get(self.native+'/api/hypotheses/synthetic-hypothesis').status_code,200)
            memory.forget(OWNER,saved['reference'],'synthetic-hypothesis-forget')
            self.assertEqual(client.get(self.native+'/api/hypotheses').json(),{'hypotheses':[]})
            self.assertEqual(client.get(self.native+'/api/hypotheses/synthetic-hypothesis').status_code,404)
        self.assertIn('SyntheticHypothesisForgottenMarker',path.read_text())

    def test_connector_loss_never_uses_raw_notes(self):
        self.seed()
        with httpx.Client(timeout=20) as client:
            self.login(client)
            self.assertEqual(client.get(self.native+'/api/hypotheses').status_code,200)
            (self.root/'LIFEOS/USER/CONFIG/memory-access.json').unlink()
            response=client.get(self.native+'/api/hypotheses')
            self.assertEqual(response.status_code,503,response.text)
            self.assertNotIn('SyntheticHypothesis',response.text)

    def test_authority_and_sources_change_after_actual_render_withhold_the_result(self):
        for mode in ('source','authority'):
            with self.subTest(mode=mode):
                self.seed()
                result=subprocess.run([sys.executable,str(Path(__file__).with_name('memory_hypothesis_queue_process.py')),
                    str(self.fixture.configuration.path),mode],capture_output=True,text=True,timeout=40,
                    env=dict(os.environ,PYTHONPATH=str(Path(__file__).resolve().parents[1])))
                self.assertEqual(result.returncode,0,result.stderr)
                self.assertEqual(json.loads(result.stdout),{'rendered':True,'withheld':True})

    def test_query_and_encoded_path_cannot_select_another_source(self):
        self.seed()
        with httpx.Client(timeout=20) as client:
            self.login(client)
            for route in ('/api/hypotheses?owner=other','/api/hypotheses/%2Fsecret',
                          '/api/hypotheses/%25secret','/api/hypotheses/missing/action'):
                response=client.get(self.native+route)
                self.assertIn(response.status_code,(400,404),response.text)
                self.assertNotIn('SyntheticHypothesis',response.text)

    def test_empty_and_nonpending_notes_preserve_native_queue_contents(self):
        with httpx.Client(timeout=20) as client:
            self.login(client)
            self.assertEqual(client.get(self.native+'/api/hypotheses').json(),{'hypotheses':[]})
            path=self.seed()
            path.write_text(path.read_text().replace('status: hypothesis','status: graduated'))
            self.assertEqual(client.get(self.native+'/api/hypotheses').json(),self.original('/api/hypotheses'))
            path.write_text('Synthetic malformed note without frontmatter')
            self.assertEqual(client.get(self.native+'/api/hypotheses').json(),self.original('/api/hypotheses'))

    def test_cross_origin_and_invalid_bearer_refuse_despite_valid_cookies(self):
        self.seed()
        with httpx.Client(timeout=20) as client:
            self.login(client)
            self.assertEqual(client.get(self.native+'/api/hypotheses',headers={'Origin':'https://untrusted.invalid'}).status_code,403)
            self.assertEqual(client.get(self.native+'/api/hypotheses',headers={'Authorization':'Bearer synthetic-invalid'}).status_code,401)
