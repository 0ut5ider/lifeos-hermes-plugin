# ABOUTME: Exercises native Atlas insight job initiation through real owner authentication.
# ABOUTME: Requires the selected owner command and preserves native graph and cached response fields.
import json
import os
import importlib
import signal
import time
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import unittest
import httpx
import test_memory_conduit_jobs as job_fixture
import test_memory_atlas as atlas_fixture
from lifeos_hook_bridge.memory_policy import SessionContext
from lifeos_hook_bridge.memory_service import MemoryService


class MemoryAtlasJobAuthenticationTests(unittest.TestCase):
    endpoint = '/api/plugins/lifeos-hook-bridge/memory/atlas_job'
    setUp = job_fixture.MemoryConduitJobAuthenticationTests.setUp
    activate = job_fixture.MemoryConduitJobAuthenticationTests.activate
    test_anonymous_job_preparation_requires_real_authentication = job_fixture.MemoryConduitJobAuthenticationTests.test_anonymous_job_preparation_requires_real_authentication
    test_owner_receives_only_a_current_configuration_restriction = job_fixture.MemoryConduitJobAuthenticationTests.test_owner_receives_only_a_current_configuration_restriction
    test_disabled_read_only_and_unbound_terminal_jobs_refuse_preparation = job_fixture.MemoryConduitJobAuthenticationTests.test_disabled_read_only_and_unbound_terminal_jobs_refuse_preparation

    def test_preparation_refuses_caller_arguments(self):
        self.activate()
        self.fixture.login()
        for path, content in ((self.endpoint + '?job=other', None), (self.endpoint, '{}'),
                (self.endpoint, '{"configuration_revision":"caller-value"}')):
            with self.subTest(path=path, content=content):
                response = self.fixture.client.post(path, content=content)
                self.assertEqual(response.status_code, 400, response.text)
                self.assertEqual(response.headers.get('cache-control'), 'no-store')
        self.assertFalse((self.root / 'LIFEOS/MEMORY/STATE/atlas-insights.json').exists())


class MemoryAtlasJobRelayTests(unittest.TestCase):
    native_module = 'atlas.ts'
    create_fixture = job_fixture.MemoryConduitJobRelayTests.create_fixture
    native_module_name = job_fixture.MemoryConduitJobRelayTests.native_module_name
    stop_dashboard = job_fixture.MemoryConduitJobRelayTests.stop_dashboard
    stop_pulse = job_fixture.MemoryConduitJobRelayTests.stop_pulse
    login = job_fixture.MemoryConduitJobRelayTests.login
    seed_graph = atlas_fixture.MemoryAtlasTests.seed_graph
    descendants = job_fixture.MemoryConduitJobRelayTests.descendants
    alive = job_fixture.MemoryConduitJobRelayTests.alive
    launch_lifetime_process = job_fixture.MemoryConduitJobRelayTests.launch_lifetime_process

    def held_inference(self):
        environment, received, requests = job_fixture.MemoryConduitJobRelayTests.held_inference(self)
        content = environment.read_text().replace('"haiku":', '"opus":')
        environment.write_text(content)
        return environment, received, requests

    def setUp(self):
        job_fixture.MemoryConduitJobRelayTests.setUp(self)
        (self.root / 'LIFEOS/ATLAS').symlink_to(Path(os.environ['LIFEOS_MEMORY_SOURCE']) / 'LIFEOS/ATLAS')
        self.directory = self.fixture.home / '.local/state/lifeos/atlas'
        self.directory.mkdir(parents=True)

    def test_authenticated_native_regeneration_button_starts_selected_owner_job(self):
        self.seed_graph()
        with httpx.Client(timeout=30) as client:
            self.login(client)
            response = client.post(self.native + '/api/atlas/insights/regenerate')
            self.assertEqual(response.status_code, 202, response.text)
            self.assertEqual(response.json(), {'generating': True})

    def test_current_stale_insights_start_native_owner_regeneration(self):
        _, cache = self.seed_graph()
        value = json.loads(cache.read_text())
        value['hash'] = '0' * 16
        cache.write_text(json.dumps(value))
        with httpx.Client(timeout=30) as client:
            self.login(client)
            response = client.get(self.native + '/api/atlas/insights')
            self.assertEqual(response.status_code, 200, response.text)
            self.assertTrue(response.json()['stale'])
            self.assertTrue(response.json()['generating'])

    def test_absent_graph_retains_exact_native_unavailable_response(self):
        with httpx.Client(timeout=30) as client:
            self.login(client)
            response = client.get(self.native + '/api/atlas/insights')
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(response.json(), {'available': False, 'error': 'run an atlas sync first'})

    def test_unbound_local_writer_keeps_stale_reader_without_generation(self):
        _, cache = self.seed_graph()
        value = json.loads(cache.read_text())
        value['hash'] = '0' * 16
        cache.write_text(json.dumps(value))
        self.fixture.configuration.update(lambda value: value['accounts'].pop(f'terminal:{os.getuid()}'))
        with httpx.Client(timeout=30) as client:
            self.login(client)
            response = client.get(self.native + '/api/atlas/insights')
            self.assertEqual(response.status_code, 200, response.text)
            self.assertTrue(response.json()['stale'])
            self.assertFalse(response.json()['generating'])

    def test_current_cache_does_not_start_a_job(self):
        _, cache = self.seed_graph()
        before = cache.read_bytes()
        with httpx.Client(timeout=30) as client:
            self.login(client)
            response = client.get(self.native + '/api/atlas/insights')
            self.assertEqual(response.status_code, 200, response.text)
            self.assertFalse(response.json()['stale'])
            self.assertFalse(response.json()['generating'])
        self.assertEqual(cache.read_bytes(), before)
        self.assertEqual(self.descendants(self.process.pid), {self.process.pid})

    def test_owner_revocation_during_automatic_preparation_withholds_prior_response(self):
        _, cache = self.seed_graph()
        value = json.loads(cache.read_text())
        value['hash'] = '0' * 16
        cache.write_text(json.dumps(value))
        before = cache.read_bytes()
        module = importlib.import_module('lifeos_memory_settings.memory_preferences')
        original = module.MemoryPreferences.atlas_job_response
        seen = []
        def revoke(preferences, *arguments, **keywords):
            result = original(preferences, *arguments, **keywords)
            seen.append(result)
            preferences.configuration.update(lambda value: value['accounts'].pop('dashboard:basic:synthetic-owner'))
            return result
        module.MemoryPreferences.atlas_job_response = revoke
        try:
            with httpx.Client(timeout=30) as client:
                self.login(client)
                response = client.get(self.native + '/api/atlas/insights')
                self.assertEqual(response.status_code, 403, response.text)
                self.assertNotIn('SyntheticAtlasNarrative', response.text)
                deadline = time.monotonic() + 15
                while self.descendants(self.process.pid) != {self.process.pid} and time.monotonic() < deadline:
                    time.sleep(0.05)
                self.assertEqual(self.descendants(self.process.pid), {self.process.pid})
        finally: module.MemoryPreferences.atlas_job_response = original
        self.assertEqual(len(seen), 1)
        self.assertEqual(cache.read_bytes(), before)

    def lifetime(self, *, daemon):
        (self.root/'LIFEOS/USER/GEAR.md').write_text(
            '## Computing\n| **Laptop** | SyntheticAtlasHeldJob | daily |\n')
        configuration = self.fixture.configuration.load()
        destination = str(self.fixture.profile)
        grant = configuration['destinations']['terminal:'+destination]
        context = SessionContext('terminal',str(os.getuid()),destination,'private',
            (configuration['principal'],),grant['model_routes'][0],'synthetic-atlas-lifetime')
        service = MemoryService(self.fixture.configuration)
        synced = service.native(context,'atlas_sync',{'collectors':['gear','projects'],'scope':'full'})
        self.assertTrue(synced['ok'],synced)
        cache = self.root/'LIFEOS/MEMORY/STATE/atlas-insights.json'
        cache.parent.mkdir(parents=True,exist_ok=True)
        cache.write_text(json.dumps({'hash':'0'*16,'narrative':'SyntheticAtlasNarrative',
            'generated_at':datetime.now(timezone.utc).isoformat()}))
        cache.chmod(0o600)
        before = cache.read_bytes()
        environment, received, requests = self.held_inference()
        self.launch_lifetime_process(environment, daemon=daemon)
        children = set()
        try:
            with httpx.Client(timeout=30) as client:
                self.login(client)
                if daemon:
                    responses = [client.post(self.native + '/api/atlas/insights/regenerate')]
                else:
                    with ThreadPoolExecutor(max_workers=3) as workers:
                        responses = list(workers.map(lambda _: httpx.get(self.native + '/api/atlas/insights',
                            cookies=client.cookies, timeout=30), range(3)))
                for response in responses:
                    self.assertEqual(response.status_code, 202 if daemon else 200, response.text)
                    self.assertTrue(response.json()['generating'])
                self.assertTrue(received.wait(20), 'The actual Atlas child does not reach inference')
                self.assertEqual(len(requests), 1)
                children = self.descendants(self.process.pid) - {self.process.pid}
                self.assertGreaterEqual(len(children), 3, children)
                self.assertIn('device', json.dumps(requests))
                if daemon:
                    self.process.send_signal(signal.SIGTERM)
                    try: self.process.wait(timeout=70)
                    except job_fixture.subprocess.TimeoutExpired: self.fail('Pulse retains its Atlas job after shutdown')
                else:
                    response = client.post(self.native + '/test-stop')
                    self.assertEqual((response.status_code, response.text), (200, 'stopped'))
            self.assertEqual([pid for pid in children if self.alive(pid)], [])
            self.assertEqual(cache.read_bytes(), before)
        finally:
            for pid in children:
                if self.alive(pid):
                    try: os.kill(pid, signal.SIGKILL)
                    except ProcessLookupError: pass

    def test_simultaneous_stale_readers_start_one_job_and_module_stop_ends_children(self):
        self.lifetime(daemon=False)

    def test_native_pulse_shutdown_ends_actual_atlas_inference_children(self):
        self.lifetime(daemon=True)

    def test_anonymous_regeneration_preserves_current_native_cache(self):
        _, cache = self.seed_graph()
        before = cache.read_bytes()
        response = httpx.post(self.native + '/api/atlas/insights/regenerate')
        self.assertEqual(response.status_code, 401, response.text)
        self.assertEqual(cache.read_bytes(), before)


class MemoryAtlasJobCommandTests(unittest.TestCase):
    def setUp(self):
        self.fixture = job_fixture.MemoryConduitJobCommandTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        native = self.fixture.fixture.native
        (native.root / 'LIFEOS/ATLAS').symlink_to(Path(os.environ['LIFEOS_MEMORY_SOURCE']) / 'LIFEOS/ATLAS')

    def test_actual_selected_profile_command_initializes_empty_graph_without_inference(self):
        result = self.fixture.fixture.call('atlas-insights')
        self.assertEqual((result.returncode, result.stderr), (0, ''), result.stdout)
        body = json.loads(result.stdout)
        self.assertEqual(body['status'], 'completed')
        self.assertTrue((self.fixture.fixture.native.root.parent/'.local/state/lifeos/atlas/atlas.db').is_file())
        self.assertFalse((self.fixture.fixture.native.root / 'LIFEOS/MEMORY/STATE/atlas-insights.json').exists())
        self.assertEqual(self.fixture.fixture.fixture.fixture.received, [])
