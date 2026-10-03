# ABOUTME: Captures actual model requests for primary, auxiliary, and compression memory paths.
# ABOUTME: Verifies admitted markers, route denial, author changes, and invalidated conversations.
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import unittest

from lifeos_hook_bridge.memory_context import route_identity
from lifeos_hook_bridge.memory_service import MemoryConfiguration
import test_memory_runtime as runtime_fixture
import test_memory_native as native_fixture


HOST = Path(os.environ.get('LIFEOS_HERMES_SOURCE',str(Path.home()/'.cache/lifeos-plugin-memory/source-gate-20260930-retained-sources-fixed/hermes')))
PROGRAM = Path(__file__).with_name('memory_model_calls.py')


class MemoryModelCallTests(unittest.TestCase):
    def setUp(self):
        self.fixture = runtime_fixture.MemoryRuntimeTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.received = []
        received = self.received
        class Gateway(BaseHTTPRequestHandler):
            def do_POST(self):
                request = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                received.append({'path':self.path,'body':request})
                body = json.dumps({'id':'synthetic-completion','object':'chat.completion','created':1,
                    'model':'synthetic-model','choices':[{'index':0,'message':{'role':'assistant','content':'SYNTHETIC-MODEL-OK'},
                    'finish_reason':'stop'}],'usage':{'prompt_tokens':10,'completion_tokens':5,'total_tokens':15}}).encode()
                if request.get('stream'):
                    chunks = [{'id':'synthetic-completion','object':'chat.completion.chunk','created':1,
                               'model':'synthetic-model','choices':[{'index':0,'delta':{'role':'assistant','content':'SYNTHETIC-MODEL-OK'},'finish_reason':None}]},
                              {'id':'synthetic-completion','object':'chat.completion.chunk','created':1,
                               'model':'synthetic-model','choices':[{'index':0,'delta':{},'finish_reason':'stop'}]}]
                    body = (''.join('data: '+json.dumps(chunk)+'\n\n' for chunk in chunks)+'data: [DONE]\n\n').encode()
                self.send_response(200)
                self.send_header('Content-Type','text/event-stream' if request.get('stream') else 'application/json')
                self.send_header('Content-Length',str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            def log_message(self, *_):
                pass
        self.server = ThreadingHTTPServer(('127.0.0.1',0),Gateway)
        threading.Thread(target=self.server.serve_forever,daemon=True).start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)
        self.route = dict(provider='custom',model='synthetic-model',base_url=f'http://127.0.0.1:{self.server.server_port}/v1',api_mode='chat_completions')
        self.fixture.configuration['destinations']['chat-a:200']['model_routes'] = [route_identity(**self.route)]
        MemoryConfiguration(self.fixture.path).save(self.fixture.configuration)
        self.host_config = {'plugins':{'enabled':[]},'model':dict(self.route,default='synthetic-model',api_key='synthetic-key'),
                            'auxiliary':{'compression':dict(self.route,api_key='synthetic-key')}}

    def run_call(self, operation, *, route=None, first=True, author='100', refresh_after_load=False, request_variant=''):
        route = route or self.route
        self.host_config['auxiliary']['compression'] = dict(route,api_key='synthetic-key')
        (self.fixture.home/'config.yaml').write_text(json.dumps(self.host_config))
        environment = {key:os.environ[key] for key in ('PATH','LANG','TZ') if key in os.environ}
        environment.update(HOME=str(self.fixture.fixture.home),HERMES_HOME=str(self.fixture.home),
                           LIFEOS_HERMES_SOURCE=str(HOST),LIFEOS_DIR=str(self.fixture.fixture.root/'LIFEOS'),
                           BUN_CONFIG_NO_AUTO_INSTALL='1')
        settings = dict(operation=operation,route=route,parent_route=self.route,first=first,
                        author=author,marker='Synthetic admitted private model marker',refresh_after_load=refresh_after_load,
                        request_variant=request_variant)
        return subprocess.run([sys.executable,str(PROGRAM)],input=json.dumps(settings),env=environment,
                              capture_output=True,text=True,timeout=30)

    def test_actual_primary_and_auxiliary_requests_keep_approved_private_markers(self):
        for operation in ('primary','sync','async','compression'):
            with self.subTest(operation=operation):
                result = self.run_call(operation)
                self.assertEqual(result.returncode,0,result.stderr)
                self.assertIn('SYNTHETIC-MODEL-OK',json.loads(result.stdout)['result'])
                self.assertIn('Synthetic admitted private model marker',json.dumps(self.received[-1]['body']))
        self.assertEqual(len(self.received),4)

    def test_actual_primary_and_auxiliary_requests_reject_unapproved_routes(self):
        for operation in ('primary','sync','async','compression'):
            with self.subTest(operation=operation):
                result = self.run_call(operation,route=dict(self.route,base_url=self.route['base_url']+'/unapproved'))
                self.assertIn('no approved memory grant',result.stderr)
                if operation == 'compression':
                    self.assertIsNone(json.loads(result.stdout)['result'])
                else:
                    self.assertNotEqual(result.returncode,0)
        self.assertEqual(self.received,[])

    def test_actual_model_paths_reject_current_author_changes(self):
        for operation in ('primary','sync','async','compression'):
            with self.subTest(operation=operation):
                result = self.run_call(operation,author='other')
                self.assertIn('current author or destination differs',result.stderr)
        self.assertEqual(self.received,[])

    def test_actual_model_paths_cannot_resume_forgotten_context(self):
        saved = self.fixture.fixture.remember('Synthetic obsolete model fact','model-fact')
        first = self.run_call('primary')
        self.assertEqual(first.returncode,0,first.stderr)
        self.fixture.fixture.memory.forget(native_fixture.OWNER,saved['reference'],'model-forget')
        for operation in ('primary','sync','async','compression'):
            with self.subTest(operation=operation):
                result = self.run_call(operation,first=False)
                self.assertNotEqual(result.returncode,0)
                self.assertIn('current facts changed',result.stderr)
        self.assertEqual(len(self.received),1)

    def test_actual_host_soul_loader_cannot_send_a_cached_removed_claim(self):
        marker = 'Synthetic removed cached model marker'
        saved = self.fixture.fixture.remember('RULE: '+marker,'cached-model','principal')
        (self.fixture.home/'SOUL.md').write_text('# Synthetic LifeOS\n\n'+marker+'\n')
        self.fixture.fixture.memory.forget(native_fixture.OWNER,saved['reference'],'cached-model-forget')
        for operation in ('primary','sync','async','compression'):
            with self.subTest(operation=operation):
                (self.fixture.home/'SOUL.md').write_text('# Synthetic LifeOS\n\n'+marker+'\n')
                result = self.run_call(operation,refresh_after_load=True)
                if operation == 'compression':
                    self.assertIsNone(json.loads(result.stdout)['result'])
                    self.assertIn('compression prompt',result.stderr)
                else:
                    self.assertNotEqual(result.returncode,0)
                    self.assertIn('model system prompt',result.stderr)
        self.assertEqual(self.received,[])

    def test_sdk_shapes_and_extra_body_cannot_send_a_retired_system_claim(self):
        marker = 'Synthetic removed cached model marker'
        saved = self.fixture.fixture.remember('RULE: '+marker,'cached-shape','principal')
        self.fixture.fixture.memory.forget(native_fixture.OWNER,saved['reference'],'shape-forget')
        for variant in ('tuple-messages','tuple-blocks','generator-messages','extra-body'):
            with self.subTest(variant=variant):
                (self.fixture.home/'SOUL.md').write_text('# Synthetic LifeOS\n\n'+marker+'\n')
                result = self.run_call('primary',refresh_after_load=True,request_variant=variant)
                self.assertNotEqual(result.returncode,0)
                self.assertIn('materialized' if variant=='generator-messages' else 'model system prompt',result.stderr)
        self.assertEqual(self.received,[])

    def test_materialized_sdk_shapes_keep_allowed_messages(self):
        for variant in ('tuple-messages','tuple-blocks','extra-body'):
            with self.subTest(variant=variant):
                result = self.run_call('primary',request_variant=variant)
                self.assertEqual(result.returncode,0,result.stderr)
                self.assertEqual(result.stderr,'')
                self.assertEqual(json.loads(result.stdout)['result'],'SYNTHETIC-MODEL-OK')
                self.assertIn('Synthetic admitted private model marker',json.dumps(self.received[-1]['body']))
        self.assertEqual(len(self.received),3)

    def test_sdk_extra_body_cannot_send_to_an_unapproved_model(self):
        result = self.run_call('primary',request_variant='extra-model')
        self.assertNotEqual(result.returncode,0)
        self.assertIn('no approved memory grant',result.stderr)
        self.assertEqual(self.received,[])


if __name__ == '__main__':
    unittest.main()
