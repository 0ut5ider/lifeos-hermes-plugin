# ABOUTME: Exercises actual LocalIntelligence owner-child cancellation during an authenticated model request.
# ABOUTME: Keeps concurrent refreshes within one job and checks full Pulse shutdown without fabricated responses.
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import shlex
import signal
import sys
import threading
import unittest
import httpx
from lifeos_hook_bridge.memory_context import route_identity
import test_memory_local_refresh_jobs as fixture
import test_memory_conduit_jobs as lifetime


class MemoryLocalRefreshLifetimeTests(unittest.TestCase):
    native_module = 'local-intelligence.ts'
    module_configuration_name = 'local'
    status_route = '/api/local-intelligence'
    setUp = fixture.MemoryLocalRefreshJobRelayTests.setUp
    create_fixture = fixture.MemoryLocalRefreshJobRelayTests.create_fixture
    native_module_name = fixture.MemoryLocalRefreshJobRelayTests.native_module_name
    stop_dashboard = fixture.MemoryLocalRefreshJobRelayTests.stop_dashboard
    stop_pulse = fixture.MemoryLocalRefreshJobRelayTests.stop_pulse
    login = fixture.MemoryLocalRefreshJobRelayTests.login
    descendants = lifetime.MemoryConduitJobRelayTests.descendants
    alive = lifetime.MemoryConduitJobRelayTests.alive
    launch_lifetime_process = lifetime.MemoryConduitJobRelayTests.launch_lifetime_process

    def held_research(self):
        received = threading.Event()
        release = threading.Event()
        requests = []
        class Gateway(BaseHTTPRequestHandler):
            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                if self.path == '/v1/chat/completions':
                    requests.append(body)
                    received.set()
                    release.wait(100)
                data = json.dumps({'error': {'message': 'Synthetic withheld research credential',
                    'type': 'authentication_error', 'code': 'invalid_api_key'}}).encode()
                try:
                    self.send_response(401)
                    self.send_header('Content-Type', 'application/json')
                    self.send_header('Content-Length', str(len(data)))
                    self.end_headers()
                    self.wfile.write(data)
                except (BrokenPipeError, ConnectionResetError): pass
            def log_message(self, *_): pass
        gateway = ThreadingHTTPServer(('127.0.0.1', 0), Gateway)
        threading.Thread(target=gateway.serve_forever, daemon=True).start()
        self.addCleanup(gateway.server_close)
        self.addCleanup(gateway.shutdown)
        self.addCleanup(release.set)
        model = {'provider': 'custom', 'default': 'synthetic-held-model',
            'base_url': f'http://127.0.0.1:{gateway.server_port}/v1', 'api_mode': 'chat_completions',
            'api_key': 'synthetic-rejected-key', 'streaming': False, 'context_length': 131072}
        profile = self.fixture.profile
        selected = json.loads((profile / 'config.yaml').read_text())
        selected['model'] = model
        (profile / 'config.yaml').write_text(json.dumps(selected))
        route = {key: model[key] for key in ('provider','base_url','api_mode')}
        route['model'] = model['default']
        self.fixture.configuration.update(lambda value:
            value['destinations']['terminal:' + str(profile)].update(model_routes=[route_identity(**route)]))
        launcher = self.fixture.home / '.local/bin/hermes'
        launcher.parent.mkdir(parents=True, exist_ok=True)
        launcher.write_text('#!/bin/sh\nexec ' + shlex.quote(sys.executable) + ' -m hermes_cli.main "$@"\n')
        launcher.chmod(0o700)
        identity = self.root / 'LIFEOS/USER/PRINCIPAL/PRINCIPAL_IDENTITY.md'
        identity.write_text('- **Hometown:** SyntheticCity, TX (ZIP 78701, Synthetic County)\n')
        environment = self.fixture.home / 'local-model.env'
        environment.write_text('')
        environment.chmod(0o600)
        return environment, received, requests

    def lifetime(self, *, daemon):
        environment, received, requests = self.held_research()
        self.launch_lifetime_process(environment, daemon=daemon)
        children = set()
        try:
            with httpx.Client(timeout=30) as client:
                self.login(client)
                if daemon:
                    responses = [client.post(self.native + '/api/local-intelligence/refresh')]
                else:
                    with ThreadPoolExecutor(max_workers=3) as workers:
                        responses = list(workers.map(lambda _: httpx.post(self.native + '/api/local-intelligence/refresh',
                            cookies=client.cookies, timeout=30), range(3)))
                for response in responses: self.assertEqual(response.status_code, 202, response.text)
                self.assertEqual(len({response.json()['run_id'] for response in responses}), 1)
                self.assertTrue(received.wait(25), 'The actual native fill does not reach the held request')
                self.assertEqual(len(requests), 1)
                self.assertEqual({tool['function']['name'] for tool in requests[0]['tools']}, {'web_search','web_extract'})
                children = self.descendants(self.process.pid) - {self.process.pid}
                self.assertGreaterEqual(len(children), 3, children)
                if daemon:
                    self.process.send_signal(signal.SIGTERM)
                    self.process.wait(timeout=70)
                else:
                    response = client.post(self.native + '/test-stop')
                    self.assertEqual((response.status_code, response.text), (200, 'stopped'))
            self.assertEqual([pid for pid in children if self.alive(pid)], [])
            self.assertFalse((self.root / 'LIFEOS/USER/CUSTOMIZATIONS/SKILLS/LocalIntelligence/latest.json').exists())
            logs = list((self.root / 'LIFEOS/USER/CUSTOMIZATIONS/SKILLS/LocalIntelligence/runs').glob('*.log'))
            self.assertEqual(len(logs), 1)
            self.assertEqual(logs[0].read_text(), '')
            self.assertEqual(logs[0].stat().st_mode & 0o777, 0o600)
        finally:
            for pid in children:
                if self.alive(pid):
                    try: os.kill(pid, signal.SIGKILL)
                    except ProcessLookupError: pass

    def test_module_stop_ends_actual_held_research_and_serializes_refreshes(self):
        self.lifetime(daemon=False)

    def test_native_pulse_shutdown_ends_actual_local_research_children(self):
        self.lifetime(daemon=True)
