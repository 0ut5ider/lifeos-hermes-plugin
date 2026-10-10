# ABOUTME: Exercises native research admission through the actual Hermes parser and web-only agent.
# ABOUTME: Uses a real authentication refusal and never creates a successful model response.
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import unittest
from lifeos_hook_bridge.memory_context import route_identity
import test_memory_owner_job_command as fixture


class ChildResearchAuthenticationTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixture.MemoryOwnerJobCommandTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.requests = []
        requests = self.requests
        class Gateway(BaseHTTPRequestHandler):
            def do_POST(self):
                raw = self.rfile.read(int(self.headers.get('Content-Length', '0')))
                body = json.loads(raw) if raw else {}
                requests.append({'path': self.path, 'body': body})
                status = 401 if self.headers.get('Authorization') != 'Bearer accepted-synthetic-key' else 503
                data = json.dumps({'error': {'message': 'Synthetic rejected research credential',
                    'type': 'authentication_error', 'code': 'invalid_api_key'}}).encode()
                self.send_response(status)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(data)))
                self.end_headers()
                self.wfile.write(data)
            def log_message(self, *_): pass
        self.gateway = ThreadingHTTPServer(('127.0.0.1', 0), Gateway)
        threading.Thread(target=self.gateway.serve_forever, daemon=True).start()
        self.addCleanup(self.gateway.server_close)
        self.addCleanup(self.gateway.shutdown)
        self.route = {'provider': 'custom', 'model': 'synthetic-research-model',
            'base_url': f'http://127.0.0.1:{self.gateway.server_port}/v1', 'api_mode': 'chat_completions'}
        profile = self.fixture.fixture.home
        selected = json.loads((profile / 'config.yaml').read_text())
        selected['model'] = {**self.route, 'default': self.route['model'], 'api_key': 'rejected-synthetic-key',
            'streaming': False, 'context_length': 131072}
        (profile / 'config.yaml').write_text(json.dumps(selected))
        self.fixture.configuration.update(lambda value:
            value['destinations']['terminal:' + str(profile)].update(model_routes=[route_identity(**self.route)]))
        root = self.fixture.native.root
        (root / 'skills').mkdir(exist_ok=True)
        (root / 'skills/LocalIntelligence').symlink_to(Path(os.environ['LIFEOS_MEMORY_SOURCE']) / 'skills/LocalIntelligence')
        (root / 'LIFEOS/PULSE').symlink_to(Path(os.environ['LIFEOS_MEMORY_SOURCE']) / 'LIFEOS/PULSE')
        identity = root / 'LIFEOS/USER/PRINCIPAL/PRINCIPAL_IDENTITY.md'
        identity.write_text('- **Hometown:** SyntheticCity, TX (ZIP 78701, Synthetic County)\n')
        launcher = self.fixture.native.home / '.local/bin/hermes'
        launcher.parent.mkdir(parents=True, exist_ok=True)
        import shlex
        launcher.write_text('#!/bin/sh\nexec ' + shlex.quote(sys.executable) + ' -m hermes_cli.main "$@"\n')
        launcher.chmod(0o700)

    def call(self):
        return self.fixture.call('local-intelligence')

    def test_admitted_research_reaches_real_authentication_refusal_with_only_web_tools(self):
        result = self.call()
        if result.returncode:
            states = json.loads((self.fixture.configuration.path.parent / 'lifeos-memory-contexts.json').read_text())
            record = {'command_exit': result.returncode, 'command_output': result.stdout,
                'sessions': {key: {'context_session': value['context']['session_id'],
                    'user_input_present': value.get('user_input') is not None} for key, value in states.items()}}
            directory = Path(__file__).resolve().parents[1] / 'docs/verification/2026-10-08-remaining-reader-audit'
            (directory / 'child-research-parent-observation.json').write_text(json.dumps(record, indent=2) + '\n')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(json.loads(result.stdout)['status'], 'completed')
        states = json.loads((self.fixture.configuration.path.parent / 'lifeos-memory-contexts.json').read_text())
        parents = [value for key, value in states.items() if key.startswith('owner-job-')]
        children = [value for key, value in states.items() if key.startswith('owner-research-')]
        self.assertEqual(len(parents), 1)
        self.assertEqual(len(children), 1)
        self.assertIsNone(parents[0]['user_input'])
        self.assertIsNotNone(children[0]['user_input'])
        for key in ('transport', 'author', 'destination', 'visibility', 'participants', 'model_route'):
            self.assertEqual(parents[0]['context'][key], children[0]['context'][key])
        digest = json.loads((self.fixture.native.root / 'LIFEOS/USER/CUSTOMIZATIONS/SKILLS/LocalIntelligence/latest.json').read_text())
        self.assertTrue(any('claude-fill:' in error for error in digest['meta']['errors']))
        requests = [request for request in self.requests if request['path'] == '/v1/chat/completions']
        self.assertEqual(len(requests), 1, result.stderr)
        names = {item['function']['name'] for item in requests[0]['body']['tools']}
        self.assertEqual(names, {'web_search', 'web_extract'})
        self.assertEqual(requests[0]['body']['reasoning_effort'], 'medium')
        self.assertNotIn('rejected-synthetic-key', result.stdout + result.stderr)

    def test_revoked_owner_refuses_research_before_any_model_request(self):
        self.fixture.configuration.update(lambda value: value['accounts'].pop('terminal:' + str(os.getuid())))
        result = self.call()
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertEqual(self.requests, [])
        self.assertNotIn('Synthetic Hermes lasting memory marker', result.stdout)
