# ABOUTME: Captures actual local child model requests under governed LifeOS memory admission.
# ABOUTME: Proves unapproved routes and invalidated history never reach the test gateway.
from dataclasses import asdict
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

PROGRAM = Path(__file__).parents[1] / 'lifeos_hook_bridge/bin/claude_direct.py'


class MemoryChildTests(unittest.TestCase):
    def test_actual_child_gateway_refuses_forgotten_system_and_generated_user_content(self):
        fixture = runtime_fixture.MemoryRuntimeTests(); fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        received = []
        class Gateway(BaseHTTPRequestHandler):
            def do_POST(self):
                received.append(json.loads(self.rfile.read(int(self.headers['Content-Length']))))
                body = json.dumps({'type':'message','content':[{'type':'text','text':'CHILD-OK'}]}).encode()
                self.send_response(200); self.send_header('Content-Length',str(len(body))); self.end_headers(); self.wfile.write(body)
            def log_message(self, *_):
                pass
        server = ThreadingHTTPServer(('127.0.0.1', 0), Gateway)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close); self.addCleanup(server.shutdown)
        base_url = f'http://127.0.0.1:{server.server_port}'
        child = dict(provider='lifeos-local-gateway', model='child-model', base_url=base_url, api_mode='anthropic')
        fixture.configuration['destinations']['chat-a:200']['model_routes'].append(route_identity(**child))
        MemoryConfiguration(fixture.path).save(fixture.configuration)
        marker = 'Synthetic forgotten direct child marker'
        saved = fixture.fixture.remember('RULE: ' + marker, 'child-retired', 'principal')
        fixture.fixture.memory.forget(__import__('test_memory_native').OWNER, saved['reference'], 'child-retired-forget')
        fixture.admit(session='fresh-child-after-forget')
        environment = {**os.environ, 'HOME':str(fixture.fixture.home), 'HERMES_HOME':str(fixture.home),
                       'ANTHROPIC_BASE_URL':base_url, 'ANTHROPIC_AUTH_TOKEN':'synthetic-token', 'LIFEOS_CHILD_PROVIDER':'',
                       'LIFEOS_MEMORY_CONTEXT':json.dumps(asdict(fixture.runtime.context()))}
        for system, content in ((marker, 'Synthetic generated request'), ('Synthetic current system', marker)):
            with self.subTest(system=system, content=content):
                result = subprocess.run([sys.executable, str(PROGRAM), '--print', '--model', 'child-model',
                    '--output-format', 'json', '--system-prompt', system], input=content, text=True,
                    capture_output=True, env=environment, timeout=10)
                self.assertNotEqual(result.returncode, 0, result.stdout)
                self.assertIn('removed or superseded claim', result.stderr)
                self.assertEqual(received, [])

    def test_actual_gateway_checks_approved_route_and_invalidated_memory(self):
        fixture = runtime_fixture.MemoryRuntimeTests(); fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        received = []
        class Gateway(BaseHTTPRequestHandler):
            def do_POST(self):
                received.append(json.loads(self.rfile.read(int(self.headers['Content-Length']))))
                body = json.dumps({'type':'message','content':[{'type':'text','text':'CHILD-OK'}]}).encode()
                self.send_response(200); self.send_header('Content-Length',str(len(body))); self.end_headers(); self.wfile.write(body)
            def log_message(self, *_):
                pass
        server = ThreadingHTTPServer(('127.0.0.1',0),Gateway)
        threading.Thread(target=server.serve_forever,daemon=True).start()
        self.addCleanup(server.server_close); self.addCleanup(server.shutdown)
        base_url = f'http://127.0.0.1:{server.server_port}'
        child = dict(provider='lifeos-local-gateway',model='child-model',base_url=base_url,api_mode='anthropic')
        grant = fixture.configuration['destinations']['chat-a:200']
        grant['model_routes'].append(route_identity(**child))
        MemoryConfiguration(fixture.path).save(fixture.configuration)
        saved = fixture.fixture.remember('Synthetic admitted child fact', 'child-fact')
        fixture.admit()
        environment = {**os.environ, 'HOME':str(fixture.fixture.home),'HERMES_HOME':str(fixture.home),
                       'ANTHROPIC_BASE_URL':base_url,'ANTHROPIC_AUTH_TOKEN':'synthetic-token','LIFEOS_CHILD_PROVIDER':'',
                       'LIFEOS_MEMORY_CONTEXT':json.dumps(asdict(fixture.runtime.context()))}
        command = [sys.executable,str(PROGRAM),'--print','--model','child-model',
                   '--output-format','json','--system-prompt','Synthetic private child context']
        def run(**changes):
            return subprocess.run(command,input='Synthetic child request',text=True,capture_output=True,
                                  env=dict(environment, **changes),timeout=10)
        allowed = run()
        self.assertEqual(allowed.returncode,0,allowed.stderr)
        self.assertEqual(json.loads(allowed.stdout)['result'],'CHILD-OK')
        self.assertEqual(received[0]['system'],'Synthetic private child context')
        unapproved = run(ANTHROPIC_BASE_URL=base_url+'/unapproved')
        self.assertNotEqual(unapproved.returncode,0,unapproved.stdout)
        self.assertEqual(len(received),1)
        fixture.fixture.memory.forget(__import__('test_memory_native').OWNER,saved['reference'],'child-forget')
        invalidated = run()
        self.assertNotEqual(invalidated.returncode,0,invalidated.stdout)
        self.assertIn('invalidated memory context',invalidated.stderr)
        self.assertEqual(len(received),1)
        MemoryConfiguration(fixture.path).update(lambda value:value.update(ownership_enabled=False))
        environment.pop('LIFEOS_MEMORY_CONTEXT')
        environment['LIFEOS_MEMORY_SESSION'] = 'session'
        disabled = run()
        self.assertNotEqual(disabled.returncode,0,disabled.stdout)
        self.assertIn('ownership changed',disabled.stderr)
        fixture.path.unlink()
        removed = run()
        self.assertNotEqual(removed.returncode,0,removed.stdout)
        self.assertEqual(len(received),1)


if __name__ == '__main__':
    unittest.main()
