# ABOUTME: Exercises native Algorithm summary job initiation through real dashboard authentication.
# ABOUTME: Requires the selected owner grant and preserves native generation response fields.
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import importlib
import json
import signal
import time
import os
from lifeos_hook_bridge.memory_policy import MemoryPolicy
import shutil
import unittest
import httpx
import test_memory_conduit_jobs as job_fixture


class MemoryAlgorithmJobAuthenticationTests(unittest.TestCase):
    endpoint = '/api/plugins/lifeos-hook-bridge/memory/algorithm_job'
    def setUp(self):
        job_fixture.MemoryConduitJobAuthenticationTests.setUp(self)
        pulse = self.root / 'LIFEOS/PULSE'
        if not pulse.exists():
            pulse.symlink_to(Path(os.environ['LIFEOS_MEMORY_SOURCE']) / 'LIFEOS/PULSE')
        hooks = self.root / 'hooks'
        if hooks.is_symlink():
            public = hooks.resolve()
            hooks.unlink()
            shutil.copytree(public, hooks)
        elif not hooks.exists():
            shutil.copytree(Path(os.environ['LIFEOS_MEMORY_SOURCE']) / 'hooks', hooks)
        algorithm = self.root / 'LIFEOS/ALGORITHM'
        algorithm.mkdir(exist_ok=True)
        (algorithm / 'LATEST').write_text('3.2.1\n')
        (algorithm / 'v3.2.1.md').write_text('# Synthetic Algorithm 3.2.1\n')
        (algorithm / 'changelog.md').write_text('# Synthetic history\n')
    activate = job_fixture.MemoryConduitJobAuthenticationTests.activate
    test_anonymous_job_preparation_requires_real_authentication = job_fixture.MemoryConduitJobAuthenticationTests.test_anonymous_job_preparation_requires_real_authentication
    def test_owner_receives_current_revision_and_native_chain_hash_without_source_text(self):
        self.activate()
        self.fixture.login()
        response = self.fixture.client.post(self.endpoint)
        self.assertEqual(response.status_code, 200, response.text)
        value = response.json()
        self.assertEqual(set(value), {'configuration_revision', 'chain_hash'})
        self.assertEqual(value['configuration_revision'], MemoryPolicy(self.configuration.load()).revision)
        self.assertRegex(value['chain_hash'], '^[0-9a-f]{64}$')
        self.assertEqual(response.headers.get('cache-control'), 'no-store')
        self.assertIn('x-lifeos-memory-installation', response.headers)
        self.configuration.update(lambda value: value['accounts'].pop('dashboard:basic:synthetic-owner'))
        self.assertEqual(self.fixture.client.post(self.endpoint).status_code, 403)
    test_disabled_read_only_and_unbound_terminal_jobs_refuse_preparation = job_fixture.MemoryConduitJobAuthenticationTests.test_disabled_read_only_and_unbound_terminal_jobs_refuse_preparation

    def test_preparation_refuses_caller_arguments(self):
        self.activate()
        self.fixture.login()
        for endpoint, body in [(self.endpoint + '?force=true', None), (self.endpoint, '{}'),
                (self.endpoint, '{"chain_hash":"caller-value"}')]:
            with self.subTest(endpoint=endpoint, body=body):
                response = self.fixture.client.post(endpoint, content=body)
                self.assertEqual(response.status_code, 400, response.text)
                self.assertEqual(response.headers.get('cache-control'), 'no-store')


class MemoryAlgorithmJobRelayTests(unittest.TestCase):
    native_module = 'algorithm-tab.ts'
    create_fixture = job_fixture.MemoryConduitJobRelayTests.create_fixture
    native_module_name = job_fixture.MemoryConduitJobRelayTests.native_module_name
    stop_dashboard = job_fixture.MemoryConduitJobRelayTests.stop_dashboard
    stop_pulse = job_fixture.MemoryConduitJobRelayTests.stop_pulse
    login = job_fixture.MemoryConduitJobRelayTests.login
    descendants = job_fixture.MemoryConduitJobRelayTests.descendants
    alive = job_fixture.MemoryConduitJobRelayTests.alive
    held_inference = job_fixture.MemoryConduitJobRelayTests.held_inference
    launch_lifetime_process = job_fixture.MemoryConduitJobRelayTests.launch_lifetime_process
    status_route = '/api/algorithm-tab'
    module_configuration_name = 'algorithm'

    def setUp(self):
        job_fixture.MemoryConduitJobRelayTests.setUp(self)
        hooks = self.root / 'hooks'
        public = hooks.resolve()
        hooks.unlink()
        shutil.copytree(public, hooks)
        algorithm = self.root / 'LIFEOS/ALGORITHM'
        algorithm.mkdir()
        (algorithm / 'LATEST').write_text('3.2.1\n')
        (algorithm / 'v3.2.1.md').write_text('# The Algorithm 3.2.1\n\nSynthetic doctrine explanation.\n')
        (algorithm / 'changelog.md').write_text('# Synthetic algorithm history\n')

    def test_authenticated_native_forced_regeneration_starts_selected_owner_job(self):
        with httpx.Client(timeout=40) as client:
            self.login(client)
            response = client.post(self.native + '/api/algorithm-tab/summary/regenerate')
            self.assertEqual(response.status_code, 202, response.text)
            self.assertEqual(response.json(), {'ok': True, 'started': True})

    def test_current_stale_overview_starts_native_owner_regeneration(self):
        with httpx.Client(timeout=40) as client:
            self.login(client)
            response = client.get(self.native + '/api/algorithm-tab')
            self.assertEqual(response.status_code, 200, response.text)
            self.assertIsNone(response.json()['summary'])
            self.assertTrue(response.json()['generating'])

    def test_unbound_local_writer_preserves_read_without_generation(self):
        self.fixture.configuration.update(lambda value: value['accounts'].pop(f'terminal:{os.getuid()}'))
        with httpx.Client(timeout=40) as client:
            self.login(client)
            response = client.get(self.native + '/api/algorithm-tab')
            self.assertEqual(response.status_code, 200, response.text)
            self.assertFalse(response.json()['generating'])

    def test_anonymous_generation_refuses_without_private_cache(self):
        response = httpx.post(self.native + '/api/algorithm-tab/summary/regenerate')
        self.assertEqual(response.status_code, 401, response.text)
        self.assertFalse((self.root / 'LIFEOS/MEMORY/STATE/algorithm-tab-summary.json').exists())

    def test_route_origin_and_method_refuse_before_generation(self):
        with httpx.Client(timeout=40) as client:
            self.login(client)
            for method, path, headers, expected in [('GET', '/api/algorithm-tab/summary/regenerate', {}, 405),
                    ('POST', '/api/algorithm-tab/summary/regenerate?force=true', {}, 400),
                    ('POST', '/api/algorithm-tab/summary/regenerate', {'origin': 'https://synthetic-other.invalid'}, 403)]:
                response = client.request(method, self.native + path, headers=headers)
                self.assertEqual(response.status_code, expected, response.text)
        self.assertFalse((self.root / 'LIFEOS/MEMORY/STATE/algorithm-tab-summary.json').exists())

    def test_owner_revocation_during_preparation_withholds_prior_view(self):
        module = importlib.import_module('lifeos_memory_settings.memory_preferences')
        original = module.MemoryPreferences.algorithm_job_response
        seen = []
        def revoke(preferences, **keywords):
            result = original(preferences, **keywords)
            seen.append(result)
            preferences.configuration.update(lambda value: value['accounts'].pop('dashboard:basic:synthetic-owner'))
            return result
        module.MemoryPreferences.algorithm_job_response = revoke
        try:
            with httpx.Client(timeout=40) as client:
                self.login(client)
                response = client.get(self.native + '/api/algorithm-tab')
                self.assertEqual(response.status_code, 403, response.text)
                self.assertNotIn('Synthetic doctrine explanation', response.text)
                deadline = time.monotonic() + 15
                while self.descendants(self.process.pid) != {self.process.pid} and time.monotonic() < deadline:
                    time.sleep(0.05)
                self.assertEqual(self.descendants(self.process.pid), {self.process.pid})
        finally:
            module.MemoryPreferences.algorithm_job_response = original
        self.assertEqual(len(seen), 1)
        self.assertFalse((self.root / 'LIFEOS/MEMORY/STATE/algorithm-tab-summary.json').exists())

    def lifetime(self, *, daemon):
        environment, received, requests = self.held_inference()
        self.launch_lifetime_process(environment, daemon=daemon)
        children = set()
        try:
            with httpx.Client(timeout=40) as client:
                self.login(client)
                if daemon:
                    responses = [client.post(self.native + '/api/algorithm-tab/summary/regenerate')]
                else:
                    with ThreadPoolExecutor(max_workers=3) as workers:
                        responses = list(workers.map(lambda _: httpx.get(self.native + '/api/algorithm-tab',
                            cookies=client.cookies, timeout=40), range(3)))
                for response in responses:
                    self.assertEqual(response.status_code, 202 if daemon else 200, response.text)
                    if not daemon:
                        self.assertTrue(response.json()['generating'])
                self.assertTrue(received.wait(25), 'The actual summary child does not reach inference')
                self.assertEqual(len(requests), 1)
                self.assertEqual(requests[0]['model'], 'synthetic-flashnext')
                children = self.descendants(self.process.pid) - {self.process.pid}
                self.assertGreaterEqual(len(children), 3, children)
                if daemon:
                    self.process.send_signal(signal.SIGTERM)
                    self.process.wait(timeout=70)
                else:
                    response = client.post(self.native + '/test-stop')
                    self.assertEqual((response.status_code, response.text), (200, 'stopped'))
            self.assertEqual([pid for pid in children if self.alive(pid)], [])
            self.assertFalse((self.root / 'LIFEOS/MEMORY/STATE/algorithm-tab-summary.json').exists())
        finally:
            for pid in children:
                if self.alive(pid):
                    try:
                        os.kill(pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass

    def test_simultaneous_stale_reads_start_one_job_and_module_stop_ends_children(self):
        self.lifetime(daemon=False)

    def test_native_pulse_shutdown_ends_actual_summary_children(self):
        self.lifetime(daemon=True)
