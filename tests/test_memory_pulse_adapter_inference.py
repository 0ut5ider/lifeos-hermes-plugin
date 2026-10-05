# ABOUTME: Runs the native PULSE adapter through the actual child inference program.
# ABOUTME: Captures local HTTP requests and checks source, route, and publication authority.
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
from lifeos_hook_bridge.memory_runtime import MemoryRuntime
import test_memory_pulse_adapter as adapter_fixture


class MemoryPulseAdapterInferenceTests(unittest.TestCase):
    def setUp(self):
        self.fixture = adapter_fixture.MemoryPulseAdapterTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.fixture.source.write_text('# Synthetic collection\nA synthetic book.\n')
        self.received = []
        self.on_request = lambda: None
        owner = self

        class Gateway(BaseHTTPRequestHandler):
            def do_POST(self):
                request = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                owner.received.append({'path': self.path, 'body': request})
                owner.on_request()
                page = {'kind': 'collection', 'title': 'Synthetic generated collection', 'category': 'taste',
                    'items': [{'name': 'A synthetic book', 'private': False}]}
                body = json.dumps({'type': 'message', 'model': 'synthetic-flashnext',
                    'content': [{'type': 'text', 'text': json.dumps(page)}], 'stop_reason': 'end_turn',
                    'usage': {'output_tokens': 42}}).encode()
                self.send_response(200)
                self.send_header('Content-Length', str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *_):
                pass

        self.server = ThreadingHTTPServer(('127.0.0.1', 0), Gateway)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)
        self.child = {'provider': 'lifeos-local-gateway', 'model': 'synthetic-flashnext',
            'base_url': f'http://127.0.0.1:{self.server.server_port}', 'api_mode': 'anthropic'}
        self.parent = {'provider': 'synthetic', 'model': 'synthetic-parent',
            'base_url': 'http://127.0.0.1/v1', 'api_mode': 'chat_completions'}
        self.configuration = self.fixture.fixture.configuration
        def configure(value):
            value['ownership_enabled'] = True
            value['destinations']['chat-a:200']['model_routes'] = [route_identity(**self.parent), route_identity(**self.child)]
        self.configuration.update(configure)
        self.runtime = MemoryRuntime(self.configuration.path)
        self.runtime.admit({'HERMES_SESSION_PLATFORM': 'chat-a', 'HERMES_SESSION_USER_ID': '100',
            'HERMES_SESSION_CHAT_ID': '200', 'HERMES_SESSION_CHAT_TYPE': 'dm',
            'HERMES_SESSION_ID': 'native-session'}, **self.parent, is_first_turn=True)
        self.addCleanup(self.runtime.clear)
        self.model_environment = self.fixture.fixture.fixture.home / 'model.env'
        mapping = {'haiku': {'model': self.child['model'], 'effort': 'low'}}
        self.model_environment.write_text('ANTHROPIC_BASE_URL=' + self.child['base_url'] + '\n'
            'ANTHROPIC_AUTH_TOKEN=synthetic-token\nLIFEOS_CHILD_INFERENCE_DIRECT=1\n'
            "LIFEOS_MODEL_TIER_MAP='" + json.dumps(mapping) + "'\n")
        self.model_environment.chmod(0o600)

    def call(self):
        root = Path(__file__).resolve().parents[1]
        environment = {**os.environ, 'HOME': str(self.fixture.fixture.fixture.home),
            'HERMES_HOME': str(self.configuration.path.parent),
            'LIFEOS_MEMORY_CONFIGURATION': str(self.configuration.path),
            'LIFEOS_MEMORY_CONTEXT': json.dumps(asdict(self.runtime.context())),
            'LIFEOS_MEMORY_SESSION': 'native-session', 'LIFEOS_CHILD_PROVIDER': '',
            'LIFEOS_HOOK_MODEL_ENV': str(self.model_environment), 'BUN_CONFIG_NO_AUTO_INSTALL': '1',
            'PATH': os.pathsep.join([str(root / 'lifeos_hook_bridge/bin'), str(Path(sys.executable).parent),
                                   str(self.fixture.bin), '/usr/bin', '/bin'])}
        environment.pop('LIFEOS_MEMORY_INTERNAL', None)
        return subprocess.run(['bun', '--no-install', str(self.fixture.root / 'LIFEOS/PULSE/Tools/AdapterCli.ts'),
            'synthetic'], env=environment, capture_output=True, text=True, timeout=40)

    def test_actual_inference_builds_native_page_and_then_uses_cache(self):
        result = self.call()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, '')
        self.assertEqual(json.loads(result.stdout)['status'], 'success')
        self.assertEqual(len(self.received), 1)
        request = self.received[0]
        self.assertEqual(request['path'], '/v1/messages')
        self.assertEqual(request['body']['model'], 'synthetic-flashnext')
        self.assertEqual(request['body']['output_config'], {'effort': 'low'})
        self.assertIn('A synthetic book.', request['body']['messages'][0]['content'])
        page = json.loads((self.fixture.data / 'synthetic.json').read_text())
        self.assertEqual(page['data']['title'], 'Synthetic generated collection')
        self.assertEqual(page['_meta']['sourceHashes'], json.loads((self.fixture.data / 'synthetic.meta.json').read_text())['sourceHashes'])
        cached = self.call()
        self.assertEqual(cached.returncode, 0, cached.stderr)
        self.assertEqual(cached.stderr, '')
        self.assertEqual(json.loads(cached.stdout)['status'], 'cached')
        self.assertEqual(len(self.received), 1)

    def test_unapproved_child_route_never_reaches_http(self):
        self.configuration.update(lambda value: value['destinations']['chat-a:200']['model_routes'].remove(route_identity(**self.child)))
        result = self.call()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.received, [])
        self.assertFalse((self.fixture.data / 'synthetic.json').exists())

    def test_private_source_never_reaches_http(self):
        self.fixture.source.write_text('<private>Synthetic hidden collection.</private>\n')
        result = self.call()
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(result.stderr, '')
        self.assertEqual(json.loads(result.stdout)['status'], 'no-sources')
        self.assertEqual(self.received, [])

    def test_source_change_during_http_refuses_page_publication(self):
        self.on_request = lambda: self.fixture.source.write_text('Synthetic later source.\n')
        result = self.call()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('The native memory service returned an invalid result', result.stderr)
        self.assertEqual(len(self.received), 1)
        self.assertFalse((self.fixture.data / 'synthetic.json').exists())

    def test_revocation_during_http_refuses_page_publication(self):
        self.on_request = lambda: self.configuration.update(lambda value: value['accounts'].pop('chat-a:100'))
        result = self.call()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(len(self.received), 1)
        self.assertFalse((self.fixture.data / 'synthetic.json').exists())
