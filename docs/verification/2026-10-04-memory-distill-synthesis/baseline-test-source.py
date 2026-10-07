# ABOUTME: Runs actual native distill synthesis through the shipped child inference path.
# ABOUTME: Captures synthetic HTTP requests and checks digest publication after source and authority changes.
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
import test_memory_native as native_fixture
import test_memory_pulse_adapter_inference as inference_fixture


class MemoryDistillSynthesisTests(unittest.TestCase):
    def setUp(self):
        self.fixture = inference_fixture.MemoryPulseAdapterInferenceTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.root = self.fixture.fixture.root
        self.native = self.fixture.fixture.fixture.fixture.memory
        self.saved = self.native.remember(native_fixture.OWNER, category='project', title='Synthetic distill research',
            content='Synthetic current distill synthesis marker', project='lab', request_id='distill-synthesis')
        self.assertEqual(self.saved['status'], 'committed')
        self.note = next((self.root / 'LIFEOS/MEMORY/KNOWLEDGE/Research').glob('*.md'))
        self.relative = 'KNOWLEDGE/Research/' + self.note.name
        self.received = []
        self.on_request = lambda: None
        owner = self

        class Gateway(BaseHTTPRequestHandler):
            def do_POST(self):
                owner.received.append(json.loads(self.rfile.read(int(self.headers['Content-Length']))))
                owner.on_request()
                result = {'items': [{'lane': 'health', 'title': 'Synthetic archive observation',
                    'pitch': 'Synthetic current archive observation.', 'why_now': 'Synthetic current note.',
                    'sources': [owner.relative]}]}
                body = json.dumps({'type': 'message', 'model': 'synthetic-flashnext',
                    'content': [{'type': 'text', 'text': json.dumps(result)}], 'stop_reason': 'end_turn',
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
        self.child = {**self.fixture.child, 'base_url': f'http://127.0.0.1:{self.server.server_port}'}
        self.fixture.configuration.update(lambda value: value['destinations']['chat-a:200'].update(
            model_routes=[route_identity(**self.fixture.parent), route_identity(**self.child)]))
        self.fixture.runtime.state_path.unlink()
        self.fixture.runtime.admit({'HERMES_SESSION_PLATFORM': 'chat-a', 'HERMES_SESSION_USER_ID': '100',
            'HERMES_SESSION_CHAT_ID': '200', 'HERMES_SESSION_CHAT_TYPE': 'dm',
            'HERMES_SESSION_ID': 'native-session'}, **self.fixture.parent, is_first_turn=True)
        self.fixture.model_environment.write_text('ANTHROPIC_BASE_URL=' + self.child['base_url'] + '\n'
            'ANTHROPIC_AUTH_TOKEN=synthetic-token\nLIFEOS_CHILD_INFERENCE_DIRECT=1\n'
            "LIFEOS_MODEL_TIER_MAP='" + json.dumps({'opus': {'model': 'synthetic-flashnext', 'effort': 'high'}}) + "'\n")
        self.digests = self.root / 'LIFEOS/MEMORY/DIGESTS'
        self.state = self.root / 'LIFEOS/MEMORY/STATE/distill.json'

    def call(self, *, dry=False):
        root = Path(__file__).resolve().parents[1]
        adapter = self.fixture.fixture
        environment = {**os.environ, 'HOME': str(adapter.fixture.fixture.home),
            'HERMES_HOME': str(self.fixture.configuration.path.parent),
            'LIFEOS_MEMORY_CONFIGURATION': str(self.fixture.configuration.path),
            'LIFEOS_MEMORY_CONTEXT': json.dumps(asdict(self.fixture.runtime.context())),
            'LIFEOS_MEMORY_SESSION': 'native-session', 'LIFEOS_CHILD_PROVIDER': '',
            'LIFEOS_HOOK_MODEL_ENV': str(self.fixture.model_environment), 'BUN_CONFIG_NO_AUTO_INSTALL': '1',
            'PATH': os.pathsep.join([str(root / 'lifeos_hook_bridge/bin'), str(Path(sys.executable).parent),
                                   str(adapter.bin), '/usr/bin', '/bin'])}
        environment.pop('LIFEOS_MEMORY_INTERNAL', None)
        environment.pop('LIFEOS_DIR', None)
        return subprocess.run(['bun', '--no-install', str(self.root / 'LIFEOS/TOOLS/KnowledgeDistill.ts'),
            'run', '--headless', *(['--dry-run'] if dry else [])], env=environment, capture_output=True,
            text=True, timeout=40)

    def test_actual_owner_synthesis_publishes_private_digest_and_state(self):
        result = self.call()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, '')
        outcome = json.loads(result.stdout)
        self.assertEqual(len(self.received), 1)
        self.assertEqual(self.received[0]['model'], 'synthetic-flashnext')
        self.assertEqual(self.received[0]['output_config'], {'effort': 'high'})
        self.assertIn('Synthetic current distill synthesis marker', self.received[0]['messages'][0]['content'])
        digest = Path(outcome['digest'])
        self.assertEqual(digest.parent, self.digests)
        self.assertIn('Synthetic current archive observation.', digest.read_text())
        self.assertEqual(digest.stat().st_mode & 0o777, 0o600)
        self.assertEqual(self.state.stat().st_mode & 0o777, 0o600)

    def test_private_unregistered_note_never_enters_actual_request(self):
        unknown = self.note.with_name('synthetic-private-unregistered.md')
        unknown.write_text('---\ntitle: Synthetic hidden note\ncreated: 2026-10-04\n---\n'
            '<private>Synthetic hidden synthesis marker.</private>\n')
        result = self.call(dry=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, '')
        self.assertEqual(len(self.received), 1)
        self.assertNotIn('Synthetic hidden synthesis marker', json.dumps(self.received))
        self.assertFalse(self.digests.exists())
        self.assertFalse(self.state.exists())

    def test_source_change_during_http_refuses_digest_and_state(self):
        self.on_request = lambda: self.note.write_text(self.note.read_text() + '\nSynthetic later source edit.\n')
        result = self.call()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(len(self.received), 1)
        self.assertFalse(self.digests.exists())
        self.assertFalse(self.state.exists())

    def test_revocation_during_http_refuses_digest_and_state(self):
        self.on_request = lambda: self.fixture.configuration.update(lambda value: value['accounts'].pop('chat-a:100'))
        result = self.call()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(len(self.received), 1)
        self.assertFalse(self.digests.exists())
        self.assertFalse(self.state.exists())
