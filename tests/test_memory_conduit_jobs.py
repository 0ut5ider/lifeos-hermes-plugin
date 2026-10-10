# ABOUTME: Exercises authenticated Conduit job preparation and selected native owner commands.
# ABOUTME: Requires fixed configuration revisions and denies stale or disabled job authority.
import json
import importlib
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import socket
import signal
import threading
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import unittest

import httpx

from lifeos_hook_bridge.memory_owner_jobs import OwnerJobs
from lifeos_hook_bridge.memory_policy import MemoryPolicy
from lifeos_hook_bridge.memory_preferences import MemoryPreferences
from lifeos_hook_bridge.memory_service import MemoryConfiguration
from lifeos_hook_bridge.memory_context import route_identity
import test_memory_conduit as conduit_fixture
import test_memory_owner_jobs as job_fixture
import test_memory_owner_job_command as command_fixture
import test_memory_pulse_auth as auth_fixture
import lifeos_hook_bridge.memory_owner_jobs as owner_jobs


class MemoryConduitJobRestrictionTests(unittest.TestCase):
    def setUp(self):
        self.fixture = job_fixture.MemoryOwnerJobsTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.configuration = self.fixture.configuration
        self.root = Path(self.configuration.load()['root'])

    def test_current_revision_runs_native_consolidation(self):
        revision = MemoryPolicy(self.configuration.load()).revision
        result = self.fixture.jobs.run('memory-consolidation', route=self.fixture.route,
            mapping=self.fixture.mapping, expected_revision=revision)
        self.assertEqual(result['status'], 'completed', result)

    def test_stale_or_malformed_revision_refuses_before_native_effect(self):
        revision = MemoryPolicy(self.configuration.load()).revision
        self.configuration.update(lambda value: value.update(synthetic_job_revision='later'))
        for expected in (revision, '', 'invalid', True):
            with self.subTest(expected=expected), self.assertRaises((ValueError, RuntimeError)):
                self.fixture.jobs.run('memory-consolidation', route=self.fixture.route,
                    mapping=self.fixture.mapping, expected_revision=expected)
        self.assertEqual(self.fixture.fixture.notes(), [])

    def test_child_configuration_revision_is_a_restriction(self):
        revision = MemoryPolicy(self.configuration.load()).revision
        self.configuration.update(lambda value: value.update(synthetic_job_revision='later'))
        program = ('from pathlib import Path;from lifeos_hook_bridge.memory_service import MemoryConfiguration;'
            'configuration=MemoryConfiguration(Path(' + repr(str(self.configuration.path)) + '));'
            '\ntry: configuration.load();print("accepted")\nexcept RuntimeError: print("refused")\n')
        for expected in (revision, 'invalid'):
            result = subprocess.run([sys.executable, '-c', program], capture_output=True, text=True,
                env={**os.environ, 'LIFEOS_MEMORY_CONFIGURATION_REVISION': expected}, timeout=10)
            self.assertEqual((result.returncode, result.stdout, result.stderr), (0, 'refused\n', ''))

    def test_inherited_revision_restriction_survives_into_actual_native_child(self):
        revision = MemoryPolicy(self.configuration.load()).revision
        original = owner_jobs._command
        previous = os.environ.get('LIFEOS_MEMORY_CONFIGURATION_REVISION')
        seen = []
        def observed(arguments, environment, timeout):
            seen.append(environment.get('LIFEOS_MEMORY_CONFIGURATION_REVISION'))
            return original(arguments, environment, timeout)
        owner_jobs._command = observed
        os.environ['LIFEOS_MEMORY_CONFIGURATION_REVISION'] = revision
        try:
            result = self.fixture.jobs.run('memory-consolidation', route=self.fixture.route, mapping=self.fixture.mapping)
            self.assertEqual(result['status'], 'completed', result)
        finally:
            owner_jobs._command = original
            if previous is None: os.environ.pop('LIFEOS_MEMORY_CONFIGURATION_REVISION', None)
            else: os.environ['LIFEOS_MEMORY_CONFIGURATION_REVISION'] = previous
        self.assertEqual(seen, [revision, revision])


class MemoryConduitJobCommandTests(unittest.TestCase):
    def setUp(self):
        self.fixture = command_fixture.MemoryOwnerJobCommandTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.root = self.fixture.native.root
        pulse = self.root / 'LIFEOS/PULSE'
        if not pulse.exists(): pulse.symlink_to(Path(os.environ['LIFEOS_MEMORY_SOURCE']) / 'LIFEOS/PULSE', target_is_directory=True)

    def test_actual_selected_profile_command_runs_idle_conduit_without_inference(self):
        result = self.fixture.call('conduit-insight')
        self.assertEqual((result.returncode, result.stderr), (0, ''), result.stdout)
        self.assertEqual(json.loads(result.stdout)['status'], 'completed')
        insights = list((self.root / 'LIFEOS/USER/CONDUIT/insights').glob('*.json'))
        self.assertEqual(len(insights), 1)
        self.assertEqual(json.loads(insights[0].read_text())['model'], '(none)')
        self.assertEqual(insights[0].stat().st_mode & 0o777, 0o600)
        self.assertEqual(self.fixture.fixture.fixture.received, [])


class MemoryConduitJobAuthenticationTests(unittest.TestCase):
    endpoint = '/api/plugins/lifeos-hook-bridge/memory/conduit_job'

    def setUp(self):
        self.fixture = auth_fixture.MemoryPulseAuthTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.configuration = self.fixture.configuration
        self.root = Path(self.configuration.load()['root'])

    def activate(self):
        config = self.configuration.load()
        owner = config['principal']
        def configure(value):
            value['ownership_enabled'] = True
            value['accounts'][f'terminal:{os.getuid()}'] = owner
            value['destinations']['terminal:' + str(self.configuration.path.parent)] = {
                'visibility': 'private', 'participants': [owner], 'read': ['principal', 'assistant', 'project'],
                'write': ['principal', 'assistant', 'project'], 'projects': ['*'], 'model_routes': ['local']}
        self.configuration.update(configure)

    def test_anonymous_job_preparation_requires_real_authentication(self):
        response = self.fixture.client.post(self.endpoint)
        self.assertEqual(response.status_code, 401, response.text)
        self.assertEqual(response.headers.get('cache-control'), 'no-store')
        self.assertFalse((self.root / 'LIFEOS/USER/CONDUIT').exists())


    def test_owner_receives_only_a_current_configuration_restriction(self):
        self.activate()
        self.fixture.login()
        response = self.fixture.client.post(self.endpoint)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json(), {'configuration_revision': MemoryPolicy(self.configuration.load()).revision})
        self.assertEqual(response.headers.get('cache-control'), 'no-store')
        self.assertIn('x-lifeos-memory-installation', response.headers)
        self.assertFalse((self.root / 'LIFEOS/USER/CONDUIT').exists())
        self.configuration.update(lambda value: value['accounts'].pop('dashboard:basic:synthetic-owner'))
        self.assertEqual(self.fixture.client.post(self.endpoint).status_code, 403)

    def test_disabled_read_only_and_unbound_terminal_jobs_refuse_preparation(self):
        self.fixture.login()
        self.assertEqual(self.fixture.client.post(self.endpoint).status_code, 503)
        self.activate()
        self.configuration.update(lambda value: value['destinations']['terminal:' + str(self.configuration.path.parent)].update(write=[]))
        self.assertEqual(self.fixture.client.post(self.endpoint).status_code, 503)
        self.configuration.update(lambda value: value['accounts'].pop(f'terminal:{os.getuid()}'))
        self.assertEqual(self.fixture.client.post(self.endpoint).status_code, 503)
        self.assertFalse((self.root / 'LIFEOS/USER/CONDUIT').exists())

class MemoryConduitJobRelayTests(unittest.TestCase):
    native_module = 'conduit.ts'
    create_fixture = conduit_fixture.MemoryConduitTests.create_fixture
    native_module_name = conduit_fixture.MemoryConduitTests.native_module_name
    stop_dashboard = conduit_fixture.MemoryConduitTests.stop_dashboard
    stop_pulse = conduit_fixture.MemoryConduitTests.stop_pulse
    login = conduit_fixture.MemoryConduitTests.login

    def setUp(self):
        previous = os.environ.get('PYTHONPATH')
        os.environ['PYTHONPATH'] = os.pathsep.join([os.environ['LIFEOS_HERMES_SOURCE'], previous or ''])
        try: conduit_fixture.MemoryConduitTests.setUp(self)
        finally:
            if previous is None: os.environ.pop('PYTHONPATH', None)
            else: os.environ['PYTHONPATH'] = previous
        profile = self.fixture.profile
        source = Path(__file__).resolve().parents[1] / 'lifeos_hook_bridge'
        shutil.copytree(source, profile / 'plugins/lifeos-hook-bridge', ignore=shutil.ignore_patterns('__pycache__'))
        route = {'provider': 'custom', 'model': 'synthetic-model', 'base_url': 'http://127.0.0.1:12345/v1',
                 'api_mode': 'chat_completions'}
        (profile / 'config.yaml').write_text(json.dumps({'plugins': {'enabled': ['lifeos-hook-bridge']},
            'model': {**route, 'default': 'synthetic-model', 'api_key': 'synthetic-key'},
            'memory': {'memory_enabled': False, 'user_profile_enabled': False}}))
        def configure(value):
            value['ownership_enabled'] = True
            value['accounts'][f'terminal:{os.getuid()}'] = value['principal']
            value['destinations']['terminal:' + str(profile)] = {'visibility': 'private',
                'participants': [value['principal']], 'read': ['principal', 'assistant', 'project'],
                'write': ['principal', 'assistant', 'project'], 'projects': ['*'], 'model_routes': [route_identity(**route)]}
        self.fixture.configuration.update(configure)

    def test_authenticated_native_button_runs_actual_idle_owner_job(self):
        directory = self.root / 'LIFEOS/USER/CONDUIT'
        response = httpx.post(self.native + '/api/conduit/insight/build')
        self.assertEqual(response.status_code, 401, response.text)
        self.assertFalse(directory.exists())
        with httpx.Client(timeout=30) as client:
            self.login(client)
            response = client.post(self.native + '/api/conduit/insight/build')
            self.assertEqual(response.status_code, 202, response.text)
            self.assertEqual(response.json(), {'building': True})
            self.assertEqual(response.headers.get('cache-control'), 'no-store')
            repeated = client.post(self.native + '/api/conduit/insight/build')
            self.assertEqual(repeated.status_code, 202, repeated.text)
            self.assertEqual(repeated.json(), {'building': True, 'alreadyRunning': True})
            deadline = time.monotonic() + 25
            while time.monotonic() < deadline:
                response = client.get(self.native + '/api/conduit/insight')
                self.assertIn(response.status_code, (200, 503), response.text)
                if response.status_code == 200 and not response.json()['building']: break
                time.sleep(0.1)
            self.assertEqual(response.status_code, 200, response.text)
            self.assertFalse(response.json()['building'])
        insights = list((directory / 'insights').glob('*.json'))
        self.assertEqual(len(insights), 1)
        self.assertEqual(json.loads(insights[0].read_text())['model'], '(none)')
        self.assertEqual(insights[0].stat().st_mode & 0o777, 0o600)

    def test_owner_revocation_after_actual_preparation_refuses_job_effects(self):
        self.fixture.login()
        response = self.fixture.client.post('/api/plugins/lifeos-hook-bridge/memory/conduit_job')
        self.assertEqual(response.status_code, 200, response.text)
        module = importlib.import_module('lifeos_memory_settings.memory_preferences')
        original = module.MemoryPreferences.conduit_job_response
        observed = []
        def revoke(preferences, *arguments, **keywords):
            result = original(preferences, *arguments, **keywords)
            observed.append(result)
            preferences.configuration.update(lambda value: value['accounts'].pop('dashboard:basic:synthetic-owner'))
            return result
        module.MemoryPreferences.conduit_job_response = revoke
        try:
            with httpx.Client(timeout=30) as client:
                self.login(client)
                response = client.post(self.native + '/api/conduit/insight/build')
                self.assertEqual(response.status_code, 202, response.text)
                self.assertEqual(client.get(self.native + '/api/conduit/insight').status_code, 403)
                # The selected Python process must finish its rejected configuration check.
                deadline = time.monotonic() + 15
                while self.descendants(self.process.pid) != {self.process.pid} and time.monotonic() < deadline:
                    time.sleep(0.05)
                self.assertEqual(self.descendants(self.process.pid), {self.process.pid})
        finally: module.MemoryPreferences.conduit_job_response = original
        self.assertEqual(len(observed), 1)
        self.assertFalse((self.root / 'LIFEOS/USER/CONDUIT').exists())

    def descendants(self, parent):
        parents = {}
        for path in Path('/proc').glob('[0-9]*/stat'):
            try:
                fields = path.read_text().rsplit(')', 1)[1].split()
                if fields[0] != 'Z': parents[int(path.parent.name)] = int(fields[1])
            except (FileNotFoundError, ProcessLookupError): pass
        found = {parent}
        while True:
            added = {pid for pid, owner in parents.items() if owner in found} - found
            if not added: return found
            found.update(added)

    def alive(self, pid):
        try: return Path('/proc', str(pid), 'stat').read_text().rsplit(')', 1)[1].split()[0] != 'Z'
        except FileNotFoundError: return False

    def held_inference(self):
        received = threading.Event()
        release = threading.Event()
        requests = []
        class Gateway(BaseHTTPRequestHandler):
            def do_POST(self):
                requests.append(json.loads(self.rfile.read(int(self.headers['Content-Length']))))
                received.set()
                release.wait(90)
                try:
                    self.send_response(401)
                    self.send_header('Content-Length', '0')
                    self.end_headers()
                except (BrokenPipeError, ConnectionResetError): pass
            def log_message(self, *_): pass
        gateway = ThreadingHTTPServer(('127.0.0.1', 0), Gateway)
        thread = threading.Thread(target=gateway.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(gateway.server_close)
        self.addCleanup(gateway.shutdown)
        self.addCleanup(release.set)
        child = {'provider': 'lifeos-local-gateway', 'model': 'synthetic-flashnext',
            'base_url': f'http://127.0.0.1:{gateway.server_port}', 'api_mode': 'anthropic'}
        def configure(value):
            value['destinations']['terminal:' + str(self.fixture.profile)]['model_routes'].append(route_identity(**child))
        self.fixture.configuration.update(configure)
        environment = self.fixture.home / 'conduit-model.env'
        environment.write_text('ANTHROPIC_BASE_URL=' + child['base_url'] + '\n'
            'ANTHROPIC_AUTH_TOKEN=synthetic-token\nLIFEOS_CHILD_INFERENCE_DIRECT=1\n'
            "LIFEOS_MODEL_TIER_MAP='" + json.dumps({'pin': 'none', 'haiku': {'model': child['model'], 'effort': 'low'}}) + "'\n")
        environment.chmod(0o600)
        date = datetime.now().strftime('%Y-%m-%d')
        events = self.root / 'LIFEOS/USER/CONDUIT/events' / (date + '.jsonl')
        events.parent.mkdir(parents=True)
        events.write_text(json.dumps({'ts': datetime.now(timezone.utc).isoformat(), 'type': 'app-focus',
            'source': 'synthetic', 'app': 'SyntheticConduitHeldJob', 'detail': {'intervalSec': 120}}) + '\n')
        return environment, received, requests

    def launch_lifetime_process(self, environment, *, daemon):
        self.stop_pulse()
        module_name = self.native_module.removesuffix('.ts')
        status_route = getattr(self, 'status_route', '/api/conduit/status' if module_name == 'conduit' else '/api/atlas')
        if daemon:
            pulse = self.root / 'LIFEOS/PULSE'
            source = Path(os.environ['LIFEOS_MEMORY_SOURCE']) / 'LIFEOS/PULSE'
            pulse.unlink()
            pulse.mkdir()
            for item in source.iterdir():
                if item.name not in ('PULSE.toml', 'PULSE.user.toml', 'state'):
                    (pulse / item.name).symlink_to(item, target_is_directory=item.is_dir())
            with socket.socket() as listener:
                listener.bind(('127.0.0.1', 0))
                port = listener.getsockname()[1]
            modules = subprocess.run(['bun', '--no-install', '-e', 'import {MODULE_DEFAULTS} from '
                + json.dumps(str(source / 'lib/modules.ts')) + ';console.log(JSON.stringify(Object.keys(MODULE_DEFAULTS)))'],
                capture_output=True, text=True, timeout=10)
            self.assertEqual((modules.returncode, modules.stderr), (0, ''))
            pulse.joinpath('PULSE.toml').write_text('port=' + str(port) + '\n[modules]\n'
                + ''.join(name + '=' + ('true' if name == getattr(self, 'module_configuration_name', module_name) else 'false') + '\n' for name in json.loads(modules.stdout))
                + '[hooks]\nenabled=false\n[observability]\nenabled=false\n')
            pulse.joinpath('state').mkdir()
            program = pulse / 'pulse.ts'
            self.native = f'http://127.0.0.1:{port}'
        else:
            program = self.fixture.home / 'conduit-lifetime.ts'
            module = self.root / 'LIFEOS/PULSE/modules' / self.native_module
            program.write_text('import {handleRequest,stop} from ' + json.dumps(str(module)) + ';'
                'import {memoryHTTPServerOptions} from ' + json.dumps(str(self.root / 'LIFEOS/TOOLS/lib/MemoryAccess.ts')) + ';'
                'const server=Bun.serve({hostname:"127.0.0.1",port:0,...memoryHTTPServerOptions(),async fetch(request){'
                'if(new URL(request.url).pathname==="/test-stop"){await stop();return new Response("stopped")};'
                'return await handleRequest(request,new URL(request.url).pathname)??new Response("absent",{status:404})}});'
                'console.log(server.port);')
        env = dict(os.environ, HOME=str(self.fixture.home), HERMES_HOME=str(self.fixture.profile),
            PYTHONPATH=os.pathsep.join([os.environ['LIFEOS_HERMES_SOURCE'], os.environ.get('PYTHONPATH', '')]),
            LIFEOS_HOOK_MODEL_ENV=str(environment), BUN_CONFIG_NO_AUTO_INSTALL='1')
        env['PATH'] = str(Path(sys.executable).parent) + os.pathsep + env['PATH']
        self.process = subprocess.Popen(['bun', '--no-install', str(program)], env=env,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if not daemon:
            self.native = 'http://127.0.0.1:' + self.process.stdout.readline().strip()
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            try:
                if httpx.get(self.native + status_route).status_code == 401: return
            except httpx.ConnectError: pass
            if self.process.poll() is not None: break
            time.sleep(0.05)
        self.fail('The actual Conduit lifetime listener did not start')

    def lifetime(self, *, daemon):
        environment, received, requests = self.held_inference()
        self.launch_lifetime_process(environment, daemon=daemon)
        children = set()
        try:
            with httpx.Client(timeout=30) as client:
                self.login(client)
                if daemon:
                    responses = [client.post(self.native + '/api/conduit/insight/build')]
                else:
                    with ThreadPoolExecutor(max_workers=3) as workers:
                        responses = list(workers.map(lambda _: httpx.post(self.native + '/api/conduit/insight/build',
                            cookies=client.cookies, timeout=30), range(3)))
                    self.assertEqual(sum(response.json() == {'building': True} for response in responses), 1)
                    self.assertEqual(sum(response.json() == {'building': True, 'alreadyRunning': True} for response in responses), 2)
                for response in responses: self.assertEqual(response.status_code, 202, response.text)
                self.assertTrue(received.wait(20), 'The actual native child did not reach inference')
                self.assertEqual(len(requests), 1)
                children = self.descendants(self.process.pid) - {self.process.pid}
                self.assertGreaterEqual(len(children), 3, children)
                self.assertIn('SyntheticConduitHeldJob', json.dumps(requests))
                if daemon:
                    self.process.send_signal(signal.SIGTERM)
                    try: self.process.wait(timeout=70)
                    except subprocess.TimeoutExpired: self.fail('Pulse retains its on-demand Conduit job after shutdown')
                else:
                    response = client.post(self.native + '/test-stop')
                    self.assertEqual((response.status_code, response.text), (200, 'stopped'))
            self.assertEqual([pid for pid in children if self.alive(pid)], [])
            self.assertFalse((self.root / 'LIFEOS/USER/CONDUIT/insights').exists())
        finally:
            # Dispose only the observed descendants of this test's native process.
            for pid in children:
                if self.alive(pid):
                    try: os.kill(pid, signal.SIGKILL)
                    except ProcessLookupError: pass

    def test_module_stop_ends_actual_held_inference_children(self):
        self.lifetime(daemon=False)

    def test_native_pulse_shutdown_ends_actual_held_inference_children(self):
        self.lifetime(daemon=True)

    def test_current_origin_account_and_method_refuse_before_start(self):
        with httpx.Client(timeout=30) as client:
            self.login(client)
            self.assertEqual(client.post(self.native + '/api/conduit/insight/build', headers={'Origin': 'http://wrong.invalid'}).status_code, 403)
            self.assertEqual(client.get(self.native + '/api/conduit/insight/build').status_code, 405)
            self.fixture.configuration.update(lambda value: value['accounts'].pop('dashboard:basic:synthetic-owner'))
            self.assertEqual(client.post(self.native + '/api/conduit/insight/build').status_code, 403)
        self.assertFalse((self.root / 'LIFEOS/USER/CONDUIT').exists())



if __name__ == '__main__': unittest.main()
