# ABOUTME: Exercises PULSE freshness against actual authenticated dashboard HTTP routes.
# ABOUTME: Checks cached preview retirement, owner revocation, and request-bound credentials.
import json
import os
from pathlib import Path
import select
import socket
import subprocess
import threading
import time
import unittest

import httpx
import uvicorn

import test_memory_pulse_auth as auth_fixture
import test_memory_pulse_relay as relay_fixture
from test_memory_native import OWNER


class MemoryFreshnessRelayTests(unittest.TestCase):
    routes = ('/api/telos/freshness', '/api/telos/freshness/stale', '/api/telos/freshness/summary',
              '/api/freshness', '/api/freshness/summary')
    login = relay_fixture.MemoryPulseRelayTests.login
    stop_dashboard = relay_fixture.MemoryPulseRelayTests.stop_dashboard
    stop_pulse = relay_fixture.MemoryPulseRelayTests.stop_pulse

    def setUp(self):
        self.fixture = auth_fixture.MemoryPulseAuthTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.root = self.fixture.fixture.root
        self.memory = self.fixture.fixture.fixture.fixture.fixture.memory
        self.telos = self.root / 'LIFEOS/USER/TELOS/TELOS.md'
        self.telos.parent.mkdir(parents=True, exist_ok=True)
        self.telos.write_text('---\nlast_updated: 2020-01-01\nlast_reviewed: 2020-01-01\n---\n'
            '# Synthetic TELOS\n## Mission\nSynthetic HTTP freshness mission\n')
        self.listener = socket.socket()
        self.listener.bind(('127.0.0.1', 0))
        self.dashboard = f'http://127.0.0.1:{self.listener.getsockname()[1]}'
        self.server = uvicorn.Server(uvicorn.Config(self.fixture.app, log_level='error', lifespan='off'))
        self.thread = threading.Thread(target=self.server.run, kwargs={'sockets': [self.listener]}, daemon=True)
        self.thread.start()
        self.addCleanup(self.stop_dashboard)
        deadline = time.monotonic() + 10
        while not self.server.started:
            if not self.thread.is_alive() or time.monotonic() > deadline:
                self.fail('The authenticated freshness dashboard did not start')
            time.sleep(0.01)
        self.fixture.configuration.update(lambda c: c.update(pulse_http={'dashboard_base_url': self.dashboard}))
        connector = self.root / 'LIFEOS/USER/CONFIG/memory-access.json'
        settings = json.loads(connector.read_text())
        settings['command'][-1] = str(self.fixture.configuration.path)
        connector.write_text(json.dumps(settings))
        self.marker = self.root / 'LIFEOS/USER/CONFIG/memory-http.json'
        self.marker.write_text('{"version":1,"managed":true}')
        self.marker.chmod(0o600)
        self.module = self.root / 'LIFEOS/PULSE/modules/telos.ts'
        program = self.fixture.home / 'freshness-relay.ts'
        program.write_text('import {handleRequest} from ' + json.dumps(str(self.module)) + ';\n'
            'const server=Bun.serve({hostname:"127.0.0.1",port:0,async fetch(request){return await '
            'handleRequest(request,new URL(request.url).pathname) ?? new Response("not found",{status:404});}});\n'
            'console.log(server.port);\n')
        self.environment = dict(os.environ, HOME=str(self.fixture.home),
            LIFEOS_DIR=str(self.root / 'LIFEOS'), BUN_CONFIG_NO_AUTO_INSTALL='1',
            LIFEOS_MEMORY_INTERNAL='1', LIFEOS_MEMORY_CONTEXT=json.dumps({'principal': 'owner', 'author': '100'}))
        self.process = subprocess.Popen(['bun', '--no-install', str(program)], env=self.environment,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.addCleanup(self.stop_pulse)
        self.assertTrue(select.select([self.process.stdout], [], [], 10)[0], 'The native freshness listener did not start')
        self.native = f'http://127.0.0.1:{int(self.process.stdout.readline())}'

    def test_anonymous_reads_cannot_borrow_ambient_owner_or_internal_flag(self):
        for route in self.routes:
            with self.subTest(route=route):
                response = httpx.get(self.native + route, headers={'X-LifeOS-Owner': 'owner'})
                self.assertEqual(response.status_code, 401, response.text)
                self.assertEqual(response.headers.get('cache-control'), 'no-store')
                self.assertNotIn('Synthetic HTTP freshness', response.text)

    def test_owner_preserves_all_native_http_payload_shapes(self):
        with httpx.Client(timeout=30) as client:
            self.login(client)
            for route in self.routes:
                with self.subTest(route=route):
                    response = client.get(self.native + route)
                    self.assertEqual(response.status_code, 200, response.text)
                    self.assertEqual(response.headers.get('cache-control'), 'no-store')
                    self.assertNotIn('etag', response.headers)
                    candidate = response.json()
                    control = Path(os.environ['LIFEOS_FRESHNESS_CONTROL_SOURCE']) / 'LIFEOS/PULSE/modules/telos.ts'
                    program = 'import {handleRequest} from ' + json.dumps(str(control)) + ';\n' \
                        + 'const r=await handleRequest(new Request(process.argv[1]),new URL(process.argv[1]).pathname);console.log(await r.text());'
                    result = subprocess.run(['bun', '--no-install', '-e', program, 'http://localhost' + route],
                        env=self.environment,
                        capture_output=True, text=True, timeout=30)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual(result.stderr, '')
                    native = json.loads(result.stdout)
                    candidate.pop('generated_at', None); native.pop('generated_at', None)
                    self.assertEqual(candidate, native)

    def test_forgotten_preview_leaves_the_existing_owner_connection_immediately(self):
        with httpx.Client(timeout=30) as client:
            self.login(client)
            response = client.get(self.native + self.routes[0])
            self.assertIn('Synthetic HTTP freshness mission', response.text)
            reference = self.memory.remember(OWNER, category='principal',
                content='RULE: Synthetic HTTP freshness mission', title='', project='', request_id='http-freshness')['reference']
            self.memory.forget(OWNER, reference, 'http-freshness-forget')
            before = self.telos.read_bytes()
            response = client.get(self.native + self.routes[0])
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(response.json()['sections'], [])
            self.assertNotIn('Synthetic HTTP freshness mission', response.text)
            self.assertEqual(self.telos.read_bytes(), before)

    def test_revocation_and_missing_connector_refuse_without_process_cache(self):
        with httpx.Client(timeout=30) as client:
            self.login(client)
            self.assertEqual(client.get(self.native + self.routes[0]).status_code, 200)
            self.fixture.configuration.update(lambda c: c['accounts'].pop('dashboard:basic:synthetic-owner'))
            response = client.get(self.native + self.routes[0])
            self.assertEqual(response.status_code, 403, response.text)
            self.assertNotIn('Synthetic HTTP freshness', response.text)
            (self.root / 'LIFEOS/USER/CONFIG/memory-access.json').unlink()
            response = client.get(self.native + self.routes[0])
            self.assertEqual(response.status_code, 503, response.text)
            self.assertNotIn('Synthetic HTTP freshness', response.text)

    def test_queries_writes_and_foreign_origins_refuse_before_delivery(self):
        with httpx.Client(timeout=30) as client:
            self.login(client)
            for route in self.routes:
                for method, suffix, headers, status in [('POST', '', {}, 405),
                        ('GET', '?root=foreign', {}, 400), ('GET', '', {'Origin': 'https://foreign.invalid'}, 403)]:
                    with self.subTest(route=route, method=method, suffix=suffix):
                        response = client.request(method, self.native + route + suffix, headers=headers)
                        self.assertEqual(response.status_code, status, response.text)
                        self.assertEqual(response.headers.get('cache-control'), 'no-store')
                        self.assertNotIn('Synthetic HTTP freshness', response.text)

    def test_backend_shutdown_refuses_even_after_a_successful_owner_read(self):
        with httpx.Client(timeout=30) as client:
            self.login(client)
            self.assertEqual(client.get(self.native + self.routes[0]).status_code, 200)
            self.server.should_exit = True
            self.thread.join(timeout=10)
            response = client.get(self.native + self.routes[0])
            self.assertEqual(response.status_code, 503, response.text)
            self.assertNotIn('Synthetic HTTP freshness', response.text)

    def test_invalid_bearer_cannot_borrow_valid_owner_cookies(self):
        with httpx.Client(timeout=30) as client:
            self.login(client)
            response = client.get(self.native + self.routes[0], headers={'Authorization': 'Bearer invalid-synthetic'})
            self.assertEqual(response.status_code, 401, response.text)
            self.assertNotIn('Synthetic HTTP freshness', response.text)

    def test_start_and_invalidate_do_not_prime_unadmitted_file_cache(self):
        cache = self.root / 'LIFEOS/USER/CACHE/freshness.json'
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text('{"synthetic_cache":"preserved"}')
        before = cache.read_bytes()
        program = 'import {start,invalidate,health} from ' + json.dumps(str(self.module)) + ';\n' \
            + 'await start(); invalidate();console.log("SYNTHETIC_HEALTH="+JSON.stringify(health()));'
        result = subprocess.run(['bun', '--no-install', '-e', program], env=self.environment,
            capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, '')
        self.assertEqual(cache.read_bytes(), before)
        last = next(line for line in result.stdout.splitlines() if line.startswith('SYNTHETIC_HEALTH='))
        body = json.loads(last.split('=', 1)[1])
        self.assertEqual(body['details']['telos_sections_total'], 0)
        self.assertEqual(body['details']['context_files_total'], 0)
        self.assertNotIn('Synthetic HTTP freshness', result.stdout)
