# ABOUTME: Exercises native source health through the real authenticated dashboard relay.
# ABOUTME: Requires current source counts and admission without priming ambient caches.
import json
import os
from pathlib import Path
import select
import subprocess
import time
import unittest

import httpx
import test_memory_freshness_relay as relay_fixture


class MemoryFreshnessHealthTests(unittest.TestCase):
    def setUp(self):
        self.fixture = relay_fixture.MemoryFreshnessRelayTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.fixture.stop_pulse()
        self.root = self.fixture.root
        program = self.fixture.fixture.home / 'source-health-relay.ts'
        program.write_text('import {start,handleRequest} from ' + json.dumps(str(self.fixture.module)) + ';\n'
            'await start();const server=Bun.serve({hostname:"127.0.0.1",port:0,async fetch(request){return await '
            'handleRequest(request,new URL(request.url).pathname) ?? new Response("not found",{status:404});}});\n'
            'console.log("SYNTHETIC_PORT="+server.port);\n')
        process = subprocess.Popen(['bun', '--no-install', str(program)], env=self.fixture.environment,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.fixture.process = process
        deadline = time.monotonic() + 10
        while True:
            self.assertTrue(select.select([process.stdout], [], [], max(0, deadline-time.monotonic()))[0])
            line = process.stdout.readline()
            if line.startswith('SYNTHETIC_PORT='):
                self.native = 'http://127.0.0.1:' + line.strip().split('=', 1)[1]
                break
            self.assertTrue(line, 'Native health listener exits before its port declaration')
        self.route = '/api/telos/health'

    def test_unauthenticated_health_requires_current_credentials(self):
        response = httpx.get(self.native + self.route, timeout=30)
        self.assertEqual(response.status_code, 401, response.text)
        self.assertEqual(response.headers.get('cache-control'), 'no-store')

    def test_owner_health_uses_current_sources_without_ambient_cache(self):
        with httpx.Client(timeout=30) as client:
            self.fixture.login(client)
            telos = client.get(self.native + '/api/telos/freshness').json()
            context = client.get(self.native + '/api/freshness').json()
            response = client.get(self.native + self.route)
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(response.headers.get('cache-control'), 'no-store')
            body = response.json()
            self.assertEqual(body['status'], 'healthy')
            self.assertEqual(body['details']['telos_sections_total'], telos['totalSections'])
            self.assertEqual(body['details']['telos_sections_stale'], len(telos['staleSections']))
            self.assertEqual(body['details']['context_files_total'], context['total'])
            self.assertEqual(body['details']['context_files_stale'], context['stale_count'])
            self.assertIsNotNone(body['details']['telos_file_updated'])
            self.assertIsNotNone(body['details']['last_read_at'])
            self.assertNotIn('Synthetic HTTP freshness mission', response.text)

    def test_revocation_refuses_previously_successful_health(self):
        with httpx.Client(timeout=30) as client:
            self.fixture.login(client)
            self.assertEqual(client.get(self.native + self.route).status_code, 200)
            self.fixture.fixture.configuration.update(lambda value: value['accounts'].pop('dashboard:basic:synthetic-owner'))
            response = client.get(self.native + self.route)
            self.assertEqual(response.status_code, 403, response.text)
            self.assertNotIn('telos_sections_total', response.text)

    def test_health_queries_writes_and_foreign_origin_refuse(self):
        with httpx.Client(timeout=30) as client:
            self.fixture.login(client)
            for method, suffix, headers, status in [('POST','',{},405), ('GET','?root=foreign',{},400),
                                                  ('GET','',{'Origin':'https://foreign.invalid'},403)]:
                with self.subTest(method=method, suffix=suffix):
                    response = client.request(method, self.native+self.route+suffix, headers=headers)
                    self.assertEqual(response.status_code, status, response.text)
                    self.assertEqual(response.headers.get('cache-control'), 'no-store')
