# ABOUTME: Tests unified health through the actual native Pulse daemon and Hermes authentication.
# ABOUTME: Keeps every scheduled action disabled and uses synthetic private runtime metadata.
import asyncio
import json
import os
from pathlib import Path
import re
import socket
import subprocess
import threading
import time
import unittest

import httpx
import uvicorn
import test_memory_pulse_auth as auth_fixture

JOB = 'SyntheticPulseJob'


class MemoryPulseHealthTests(unittest.TestCase):
    def setUp(self):
        self.fixture = auth_fixture.MemoryPulseAuthTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.root = self.fixture.fixture.root
        self.source = Path(os.environ['LIFEOS_MEMORY_SOURCE'])
        self.listener = socket.socket()
        self.listener.bind(('127.0.0.1', 0))
        self.dashboard = 'http://127.0.0.1:' + str(self.listener.getsockname()[1])
        self.delivery_has_access = False
        self.delay_admission = 0
        self.delay_delivery = 0
        self.delivery_observed = False
        self.revoke_delivery = False
        self.application_errors = []
        async def observe_delivery(scope, receive, send):
            if scope.get('type') == 'http' and scope.get('path') == '/api/plugins/lifeos-hook-bridge/memory/pulse_runtime':
                if scope.get('method') == 'POST':
                    self.delivery_observed = True
                    cookie = next((value.decode('latin1') for name, value in scope.get('headers', []) if name == b'cookie'), '')
                    self.delivery_has_access = any(pair.strip().startswith('hermes_session_at=') for pair in cookie.split(';'))
                    if self.revoke_delivery: self.fixture.configuration.update(lambda config: config['accounts'].clear())
                    if self.delay_delivery: await asyncio.sleep(self.delay_delivery)
                elif self.delay_admission: await asyncio.sleep(self.delay_admission)
            try: await self.fixture.app(scope, receive, send)
            except Exception as error:
                self.application_errors.append(type(error).__name__)
                raise
        self.server = uvicorn.Server(uvicorn.Config(observe_delivery, log_level='error', lifespan='off'))
        self.thread = threading.Thread(target=self.server.run, kwargs={'sockets': [self.listener]}, daemon=True)
        self.thread.start()
        self.addCleanup(self.stop_dashboard)
        deadline = time.monotonic() + 10
        while not self.server.started:
            self.assertTrue(self.thread.is_alive())
            if time.monotonic() >= deadline: self.fail('The authenticated health dashboard does not start')
            time.sleep(0.01)
        self.fixture.configuration.update(lambda config: config.update(pulse_http={
            'dashboard_base_url': self.dashboard, 'dashboard_browser_url': self.dashboard}))
        connector = self.root / 'LIFEOS/USER/CONFIG/memory-access.json'
        config = json.loads(connector.read_text())
        config['command'][-1] = str(self.fixture.configuration.path)
        connector.write_text(json.dumps(config))
        self.marker = self.root / 'LIFEOS/USER/CONFIG/memory-http.json'
        self.marker.write_text(json.dumps({'version': 1, 'managed': True}))
        self.marker.chmod(0o600)
        self.pulse = self.root / 'LIFEOS/PULSE'
        self.assertTrue(self.pulse.is_symlink())
        self.pulse.unlink()
        self.pulse.mkdir()
        for entry in (self.source / 'LIFEOS/PULSE').iterdir():
            if entry.name not in {'PULSE.toml', 'state', 'logs'}:
                (self.pulse / entry.name).symlink_to(entry, target_is_directory=entry.is_dir())
        (self.pulse / 'state').mkdir()
        self.build = self.fixture.home / 'synthetic-dashboard'
        self.build.mkdir()
        (self.build / 'index.html').write_text('<!doctype html><title>Synthetic health fixture</title>')
        self.performance = False
        self.observability = False
        self.enabled = False
        self.failures = 100
        self.job = JOB
        self.log = self.fixture.home / 'actual-pulse-health.log'
        self.process = None
        self.addCleanup(self.stop_pulse)
        self.start_pulse()

    def stop_dashboard(self):
        self.server.should_exit = True
        self.thread.join(timeout=10)
        self.listener.close()
        self.assertFalse(self.thread.is_alive())
        self.assertEqual(self.application_errors, [], 'The actual dashboard application raises an unhandled exception')

    def login(self, client):
        result = client.post(self.dashboard + '/auth/password-login', json={'provider': 'basic',
            'username': 'synthetic-owner', 'password': 'synthetic-password'})
        self.assertEqual(result.status_code, 200, result.text)

    def start_pulse(self):
        declaration = (self.source / 'LIFEOS/PULSE/lib/modules.ts').read_text().split('export const MODULE_DEFAULTS')[1].split('}')[0]
        names = re.findall(r'\b(\w+): (?:true|false)', declaration)
        with socket.socket() as listener:
            listener.bind(('127.0.0.1', 0))
            port = listener.getsockname()[1]
        self.native = 'http://127.0.0.1:' + str(port)
        self.configuration = self.pulse / 'PULSE.toml'
        self.configuration.write_text('port = ' + str(port) + '\n[hooks]\nenabled = true\n[observability]\n'
            + 'enabled = ' + str(self.observability).lower() + '\ndashboard_dir = ' + json.dumps(str(self.build)) + '\n[modules]\n'
            + ''.join(name + ' = ' + str(name == 'performance' and self.performance).lower() + '\n' for name in names) + '\n[[job]]\nname = ' + json.dumps(self.job)
            + '\nschedule = "0 0 1 1 *"\ntype = "script"\ncommand = "false"\noutput = "log"\nenabled = '
            + str(self.enabled).lower() + '\n')
        self.state = self.pulse / 'state/state.json'
        self.state.write_text(json.dumps({'startedAt': int(time.time() * 1000), 'jobs': {
            self.job: {'lastRun': int(time.time() * 1000), 'lastResult': 'error', 'consecutiveFailures': self.failures}}}))
        environment = dict(os.environ, HOME=str(self.fixture.home), LIFEOS_DIR=str(self.root / 'LIFEOS'), BUN_CONFIG_NO_AUTO_INSTALL='1')
        for name in ('LIFEOS_MEMORY_CONTEXT', 'LIFEOS_MEMORY_INTERNAL', 'CLAUDE_CONFIG_DIR', 'LIFEOS_CONFIG_DIR', 'SIRI_API_KEY'):
            environment.pop(name, None)
        with self.log.open('a') as stream:
            self.process = subprocess.Popen(['bun', '--no-install', str(self.source / 'LIFEOS/PULSE/pulse.ts')],
                env=environment, stdout=stream, stderr=subprocess.STDOUT)
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            self.assertIsNone(self.process.poll(), self.log.read_text())
            try:
                response = httpx.get(self.native + '/api/pulse/health', timeout=2)
                if response.status_code in {200, 401, 503}: return
            except httpx.TransportError: pass
            time.sleep(0.05)
        self.fail('The actual Pulse health listener does not start: ' + self.log.read_text())

    def stop_pulse(self):
        if self.process is not None and self.process.poll() is None:
            self.process.terminate()
            try: self.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=10)
        if self.process is not None:
            output = self.log.read_text()
            self.assertNotIn('LifeOS Pulse crashed', output)
            self.assertNotIn('Running job', output)

    def test_original_unmanaged_health_has_truthful_native_asset_and_failure_status(self):
        self.stop_pulse()
        self.marker.unlink()
        (self.root / 'LIFEOS/USER/CONFIG/memory-access.json').unlink()
        self.start_pulse()
        response = httpx.get(self.native + '/api/pulse/health')
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertEqual(body['status'], 'ok')
        self.assertEqual(body['subsystems']['cron']['jobs'][0]['name'], JOB)
        self.assertEqual(body['subsystems']['cron']['jobs'][0]['failures'], 100)
        self.assertEqual(body['subsystems']['hooks']['stats']['requests'], 0)
        self.stop_pulse()
        self.enabled = True
        self.start_pulse()
        response = httpx.get(self.native + '/api/pulse/health')
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()['status'], 'degraded')
        self.assertTrue(any(JOB in reason for reason in response.json()['reasons']))
        (self.build / 'index.html').unlink()
        response = httpx.get(self.native + '/healthz')
        self.assertEqual(response.status_code, 503, response.text)
        self.assertEqual(response.json()['subsystems']['dashboard']['status'], 'missing')

    def test_anonymous_unified_health_refuses_personal_runtime_metadata(self):
        for path in ('/api/pulse/health', '/healthz'):
            with self.subTest(path=path):
                response = httpx.get(self.native + path)
                self.assertEqual(response.status_code, 401, response.text[:250])
                self.assertEqual(response.headers.get('cache-control'), 'no-store')
                self.assertNotIn(JOB, response.text)

    def test_current_owner_receives_native_health_with_no_store_and_current_revocation(self):
        with httpx.Client(timeout=30) as client:
            self.login(client)
            for path in ('/api/pulse/health', '/healthz'):
                response = client.get(self.native + path)
                self.assertEqual(response.status_code, 200, response.text[:250])
                self.assertEqual(response.headers.get('cache-control'), 'no-store')
                self.assertEqual(response.json()['subsystems']['cron']['jobs'][0]['name'], JOB)
            self.fixture.configuration.update(lambda config: config['accounts'].clear())
            self.assertEqual(client.get(self.native + '/healthz').status_code, 403)

    def test_private_job_label_refuses_owner_delivery(self):
        self.stop_pulse()
        self.job = '<private>SyntheticPulseHiddenJob</private>'
        self.start_pulse()
        with httpx.Client(timeout=30) as client:
            self.login(client)
            response = client.get(self.native + '/api/pulse/health')
            self.assertEqual(response.status_code, 503, response.text[:250])
            self.assertNotIn('SyntheticPulseHiddenJob', response.text)

    def test_selected_native_subsystem_shapes_and_policy_admission_characterization(self):
        from datetime import datetime, timezone
        from lifeos_hook_bridge.memory_access import NativeMemory
        from lifeos_hook_bridge.memory_pulse_health import admit
        from test_memory_native import OWNER
        self.stop_pulse()
        self.marker.unlink()
        (self.root / 'LIFEOS/USER/CONFIG/memory-access.json').unlink()
        self.performance = True
        self.observability = True
        self.start_pulse()
        response = httpx.get(self.native + '/api/pulse/health')
        self.assertEqual(response.status_code, 200, response.text[:250])
        body = response.json()
        self.assertEqual(set(body['subsystems']), {'cron', 'hooks', 'dashboard', 'performance', 'observability'})
        self.assertTrue(body['subsystems']['performance']['enabled'])
        self.assertIsInstance(body['subsystems']['performance']['startedAt'], str)
        self.assertTrue(body['subsystems']['observability']['enabled'])
        self.assertIsInstance(body['subsystems']['observability']['startedAt'], str)
        observation = {'status': response.status_code, 'body': body, 'observed_at': datetime.now(timezone.utc).isoformat()}
        self.assertEqual(admit(NativeMemory(self.root), OWNER, observation), {'status': response.status_code, 'body': body})


    def test_managed_missing_dashboard_keeps_native_admitted_http_503_body(self):
        (self.build / 'index.html').unlink()
        with httpx.Client(timeout=30) as client:
            self.login(client)
            response = client.get(self.native + '/healthz')
            self.assertEqual(response.status_code, 503, response.text[:250])
            self.assertEqual(response.headers.get('cache-control'), 'no-store')
            self.assertEqual(response.json()['status'], 'degraded')
            self.assertEqual(response.json()['subsystems']['dashboard']['status'], 'missing')
            self.assertTrue(any('dashboard build missing' in reason for reason in response.json()['reasons']))

    def test_methods_selectors_origin_invalid_bearer_and_connector_loss_refuse(self):
        with httpx.Client(timeout=30) as client:
            self.login(client)
            for method, target, headers, code in (
                    ('POST', '/healthz', {}, 405), ('GET', '/healthz?source=other', {}, 400),
                    ('GET', '/healthz', {'Origin': 'https://untrusted.invalid'}, 403),
                    ('GET', '/healthz', {'Authorization': 'Bearer invalid'}, 401)):
                with self.subTest(method=method, target=target, headers=headers):
                    response = client.request(method, self.native + target, headers=headers)
                    self.assertEqual(response.status_code, code, response.text[:250])
                    self.assertEqual(response.headers.get('cache-control'), 'no-store')
                    self.assertNotIn(JOB, response.text)
            (self.root / 'LIFEOS/USER/CONFIG/memory-access.json').unlink()
            response = client.get(self.native + '/healthz')
            self.assertEqual(response.status_code, 503, response.text[:250])
            self.assertNotIn(JOB, response.text)

    def test_actual_authentication_refresh_reaches_delivery_and_returns_session_cookies(self):
        with httpx.Client(timeout=30) as client:
            self.login(client)
            client.cookies.delete('hermes_session_at')
            response = client.get(self.native + '/api/pulse/health')
            self.assertEqual(response.status_code, 200, response.text[:250])
            self.assertTrue(self.delivery_observed)
            self.assertTrue(self.delivery_has_access)
            self.assertIsNotNone(client.cookies.get('hermes_session_at'))
            self.assertTrue(any(cookie.startswith('hermes_session_at=') for cookie in response.headers.get_list('set-cookie')))

    def test_private_refusal_still_returns_the_actual_refreshed_session(self):
        self.stop_pulse()
        self.job = '<private>SyntheticPulseRefreshHidden</private>'
        self.start_pulse()
        with httpx.Client(timeout=30) as client:
            self.login(client)
            client.cookies.delete('hermes_session_at')
            response = client.get(self.native + '/api/pulse/health')
            self.assertEqual(response.status_code, 503, response.text[:250])
            self.assertNotIn('SyntheticPulseRefreshHidden', response.text)
            self.assertIsNotNone(client.cookies.get('hermes_session_at'))

    def test_actual_native_formatting_cannot_use_preflight_after_owner_revocation(self):
        with httpx.Client(timeout=30) as client:
            self.login(client)
            self.revoke_delivery = True
            response = client.get(self.native + '/api/pulse/health')
            self.assertTrue(self.delivery_observed)
            self.assertEqual(response.status_code, 403, response.text[:250])
            self.assertNotIn(JOB, response.text)

    def test_actual_retirement_refuses_a_cached_job_label(self):
        from test_memory_native import OWNER
        memory = self.fixture.fixture.fixture.fixture.fixture.memory
        saved = memory.remember(OWNER, category='principal', content='RULE: ' + JOB, title='', project='', request_id='pulse-job-save')
        self.assertEqual(saved['status'], 'committed')
        self.assertEqual(memory.forget(OWNER, saved['reference'], 'pulse-job-forget')['status'], 'committed')
        with httpx.Client(timeout=30) as client:
            self.login(client)
            response = client.get(self.native + '/api/pulse/health')
            self.assertEqual(response.status_code, 503, response.text[:250])
            self.assertNotIn(JOB, response.text)

    def test_authenticated_delivery_rejects_invalid_stale_large_and_unclassified_observations(self):
        from copy import deepcopy
        from datetime import datetime, timezone
        endpoint = self.dashboard + '/api/plugins/lifeos-hook-bridge/memory/pulse_runtime'
        self.assertEqual(httpx.get(endpoint).status_code, 401)
        self.assertEqual(httpx.post(endpoint, json={}).status_code, 401)
        with httpx.Client(timeout=30) as client:
            self.login(client)
            native = client.get(self.native + '/api/pulse/health')
            self.assertEqual(native.status_code, 200, native.text[:250])
            observed = {'status': 200, 'body': native.json(), 'observed_at': datetime.now(timezone.utc).isoformat()}
            valid = client.post(endpoint, json=observed)
            self.assertEqual(valid.status_code, 200, valid.text[:250])
            self.assertEqual(valid.json(), native.json())
            self.assertIsNotNone(valid.headers.get('x-lifeos-memory-installation'))
            invalid = [None, [], {}, {**observed, 'status': False}, {**observed, 'status': []},
                {**observed, 'observed_at': '2000-01-01T00:00:00Z'}]
            wrong = deepcopy(observed); wrong['body']['status'] = []; invalid.append(wrong)
            wrong = deepcopy(observed); wrong['body']['subsystems']['cron']['jobs'][0]['result'] = []; invalid.append(wrong)
            wrong = deepcopy(observed); wrong['body']['subsystems']['voice'] = {}; invalid.append(wrong)
            wrong = deepcopy(observed); wrong['body']['subsystems']['hooks']['stats']['requests'] = True; invalid.append(wrong)
            for observation in invalid:
                with self.subTest(observation=observation):
                    response = client.post(endpoint, json=observation)
                    self.assertEqual(response.status_code, 400, response.text[:250])
                    self.assertEqual(response.headers.get('cache-control'), 'no-store')
                    self.assertNotIn(JOB, response.text)
            response = client.post(endpoint, content=b'x' * 65537)
            self.assertEqual(response.status_code, 400, response.text[:250])
            escaped = json.dumps(observed).replace(JOB, r'\u003cprivate\u003eSyntheticPulseEscapedHidden\u003c/private\u003e')
            response = client.post(endpoint, content=escaped, headers={'Content-Type': 'application/json'})
            self.assertEqual(response.status_code, 503, response.text[:250])
            self.assertNotIn('SyntheticPulseEscapedHidden', response.text)
            self.assertNotIn('x-lifeos-memory-installation', response.headers)

    def test_whole_health_request_refuses_slow_phases_before_native_idle_disconnect(self):
        self.delay_admission = 24
        self.delay_delivery = 24
        with httpx.Client(timeout=65) as client:
            self.login(client)
            client.cookies.delete('hermes_session_at')
            started = time.monotonic()
            try: response = client.get(self.native + '/api/pulse/health')
            except httpx.TransportError as error:
                print(json.dumps({'health_elapsed_seconds': time.monotonic() - started, 'transport_error': type(error).__name__}))
                raise
            elapsed = time.monotonic() - started
            print(json.dumps({'health_elapsed_seconds': elapsed, 'status': response.status_code}))
            self.assertEqual(response.status_code, 503, response.text[:250])
            self.assertEqual(response.headers.get('cache-control'), 'no-store')
            self.assertNotIn(JOB, response.text)
            self.assertLess(elapsed, 43)
            self.assertIsNotNone(client.cookies.get('hermes_session_at'))
            self.assertTrue(any(cookie.startswith('hermes_session_at=') for cookie in response.headers.get_list('set-cookie')))


if __name__ == '__main__': unittest.main()
