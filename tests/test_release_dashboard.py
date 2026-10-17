# ABOUTME: Exercises release dashboard authorization through actual native session verification and HTTP requests.
# ABOUTME: Checks anonymous, unbound, revoked, and foreign-origin requests against a synthetic owner profile.
import json
import os
from pathlib import Path
import secrets
import shutil
import socket
import tempfile
from threading import Thread
import time
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from fastapi import FastAPI
import uvicorn
from hermes_cli.dashboard_auth.middleware import gated_auth_middleware
from hermes_cli.dashboard_auth.registry import register_global_provider, unregister_global_provider
from plugins.dashboard_auth.basic import BasicAuthProvider, hash_password
from optional.lifeos_release_manager.dashboard.plugin_api import router
from lifeos_hook_bridge.memory_service import MemoryConfiguration


class ReleaseDashboardTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.profile = Path(self.folder.name) / '.hermes'
        self.profile.mkdir(mode=0o700)
        previous = os.environ.get('HERMES_HOME')
        os.environ['HERMES_HOME'] = str(self.profile)
        def restore_environment():
            if previous is None:
                os.environ.pop('HERMES_HOME', None)
            else:
                os.environ['HERMES_HOME'] = previous
        self.addCleanup(restore_environment)
        shutil.copytree(Path(__file__).resolve().parents[1] / 'lifeos_hook_bridge',
            self.profile / 'plugins/lifeos-hook-bridge', ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
        self.configuration = MemoryConfiguration(self.profile / 'lifeos-memory.json')
        self.policy = {'version': 1, 'root': str(self.profile.parent / '.claude'), 'principal': 'synthetic-owner',
            'accounts': {'dashboard:basic:owner': 'synthetic-owner'}, 'destinations': {}, 'clients': {}}
        self.configuration.save(self.policy)
        secret = secrets.token_bytes(32)
        password_hash = hash_password('synthetic-password')
        provider = BasicAuthProvider(username='owner', password_hash=password_hash, secret=secret)
        register_global_provider(provider)
        self.addCleanup(unregister_global_provider, provider.name, provider)
        self.owner = provider.complete_password_login(username='owner', password='synthetic-password').access_token
        other = BasicAuthProvider(username='other', password_hash=password_hash, secret=secret)
        self.other = other.complete_password_login(username='other', password='synthetic-password').access_token
        app = FastAPI()
        app.state.auth_required = True
        app.middleware('http')(gated_auth_middleware)
        app.include_router(router, prefix='/api/plugins/lifeos-release-manager')
        @app.get('/health')
        async def health():
            return {'status': 'ok'}
        listener = socket.socket()
        listener.bind(('127.0.0.1', 0))
        self.addCleanup(listener.close)
        self.origin = 'http://127.0.0.1:' + str(listener.getsockname()[1])
        self.server = uvicorn.Server(uvicorn.Config(app, log_level='critical', access_log=False, lifespan='off', ws='none'))
        self.thread = Thread(target=self.server.run, kwargs={'sockets': [listener]})
        self.thread.start()
        def stop():
            self.server.should_exit = True
            self.thread.join(timeout=10)
            self.assertFalse(self.thread.is_alive())
        self.addCleanup(stop)
        deadline = time.monotonic() + 10
        while not self.server.started:
            if not self.thread.is_alive() or time.monotonic() > deadline:
                self.fail('The actual dashboard authorization server does not start')
            time.sleep(0.01)

    def request(self, token=None, *, path='/operations', method='GET', body=None, origin=None, timeout=10):
        headers = {}
        if token:
            headers['Authorization'] = 'Bearer ' + token
        if origin:
            headers['Origin'] = origin
        request = Request(self.origin + '/api/plugins/lifeos-release-manager' + path,
            data=body, method=method, headers=headers)
        try:
            with urlopen(request, timeout=timeout) as response:
                return response.status, json.loads(response.read())
        except HTTPError as error:
            with error:
                return error.code, json.loads(error.read())

    def test_native_sessions_enforce_owner_binding_and_current_revocation(self):
        self.assertEqual(self.request()[0], 401)
        self.assertEqual(self.request('forged-session')[0], 401)
        self.assertEqual(self.request(self.other)[0], 403)
        self.assertEqual(self.request(self.owner), (200, {'operations': []}))
        self.policy['accounts'] = {}
        self.configuration.save(self.policy)
        self.assertEqual(self.request(self.owner)[0], 403)

    def test_compatibility_requires_owner_and_reports_the_running_hermes(self):
        from optional.lifeos_release_manager.host_compatibility import running_source
        self.assertEqual(self.request(path='/compatibility')[0], 401)
        self.assertEqual(self.request(self.other, path='/compatibility')[0], 403)
        code, value = self.request(self.owner, path='/compatibility')
        self.assertEqual(code, 200)
        self.assertEqual(value['detected']['source'], str(running_source()))
        self.assertEqual(value['detected']['profile'], str(self.profile))
        self.assertIn(value['state'], ('compatible', 'unsupported_layout', 'unsupported_version', 'modified_source',
            'partially_patched', 'patched_without_record', 'shared_installation', 'dependency_conflict'))
        self.assertFalse((self.profile / '.lifeos-releases').exists())

    def test_malformed_host_record_is_reported_as_drift_with_its_reason(self):
        (self.profile / 'lifeos-host.json').write_text('{not json')
        (self.profile / 'lifeos-host.json').chmod(0o600)
        code, value = self.request(self.owner, path='/compatibility')
        self.assertEqual(code, 200)
        self.assertEqual(value['state'], 'host_drift')
        self.assertEqual(value['reasons'][0]['code'], 'invalid_host_record')
        self.assertIn('lifeos-host.json', value['reasons'][0]['message'])

    def test_mutations_reject_foreign_origin_and_client_supplied_fields(self):
        path = '/operations/' + ('a' * 32) + '/review'
        self.assertEqual(self.request(self.owner, path=path, method='POST', origin='https://other.invalid')[0], 403)
        self.assertEqual(self.request(self.owner, path=path, method='POST', body=b'{"account":"owner"}', origin=self.origin)[0], 400)
        self.assertFalse((self.profile / '.lifeos-releases').exists())

    def test_preparation_requires_owner_and_refuses_unrecognized_inputs(self):
        path = '/prepare'
        body = b'{"intent":"install","name":"Synthetic","assistant":"Test"}'
        self.assertEqual(self.request(path=path, method='POST', body=body)[0], 401)
        self.assertEqual(self.request(self.other, path=path, method='POST', body=body)[0], 403)
        self.assertEqual(self.request(self.owner, path=path, method='POST', body=body,
                                      origin='https://other.invalid')[0], 403)
        for payload in ({'intent': 'shell', 'command': 'touch unexpected'},
                        {'intent': []},
                        {'intent': 'install', 'version': True},
                        {'intent': 'update', 'profile': '/other/profile'},
                        {'intent': 'update', 'version': 'main'},
                        {'intent': 'install', 'name': '', 'assistant': 'Test'}):
            with self.subTest(payload=payload):
                self.assertEqual(self.request(self.owner, path=path, method='POST',
                    body=json.dumps(payload).encode(), origin=self.origin)[0], 400)
        self.assertFalse((self.profile / '.lifeos-releases').exists())

    def test_preparation_rejects_large_and_malformed_requests(self):
        for body in (b'{', b'[]', b'null', b'x' * 4097):
            with self.subTest(body=body[:20]):
                self.assertEqual(self.request(self.owner, path='/prepare', method='POST',
                    body=body, origin=self.origin)[0], 400)
        self.assertFalse((self.profile / '.lifeos-releases').exists())

    @unittest.skipUnless(os.environ.get('LIFEOS_MANAGED_FRESH_OPERATION'), 'An actual prepared fresh operation is required')
    def test_historical_fresh_review_refuses_without_blocking_the_dashboard(self):
        import fcntl
        job = Path(os.environ['LIFEOS_MANAGED_FRESH_OPERATION'])
        request = json.loads((job / 'request.json').read_bytes())
        previous_home = os.environ.get('HOME')
        os.environ['HOME'] = request['account_home']
        os.environ['HERMES_HOME'] = request['profile']
        self.addCleanup(lambda: os.environ.__setitem__('HOME', previous_home) if previous_home is not None else os.environ.pop('HOME', None))
        results = []
        def review():
            try:
                results.append(self.request(self.owner, path='/operations/' + job.name + '/review', method='POST', timeout=120))
            except Exception as error:
                results.append(error)
        thread = Thread(target=review)
        thread.start()
        try:
            deadline = time.monotonic() + 5
            with (job / 'operation.lock').open('rb') as lock:
                while time.monotonic() < deadline:
                    try:
                        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                        fcntl.flock(lock, fcntl.LOCK_UN)
                    except BlockingIOError:
                        break
                    time.sleep(0.01)
                else:
                    self.fail('The actual operation review does not acquire its lock')
            health = Request(self.origin + '/health', headers={'Authorization': 'Bearer ' + self.owner})
            with urlopen(health, timeout=0.75) as response:
                self.assertEqual(json.loads(response.read()), {'status': 'ok'})
        finally:
            thread.join(timeout=130)
            self.assertFalse(thread.is_alive())
        self.assertEqual(results[0][0], 409)
        self.assertIn('first installation', results[0][1]['detail'])
        self.assertFalse(Path(request['installed']).exists())


class InplaceReviewTests(unittest.TestCase):
    def test_review_lists_host_files_configuration_keys_update_difference_and_known_conflicts(self):
        from optional.lifeos_release_manager.dashboard.plugin_api import inplace_review
        from optional.lifeos_release_manager.release_programs import publish
        with tempfile.TemporaryDirectory() as directory:
            job = Path(directory)
            update = {'added': ['hermes_cli/new_hook.py'], 'changed': ['hermes_cli/plugins.py'], 'restored': ['run_agent.py']}
            publish(job / 'inplace-review.json', json.dumps({'configuration': ['plugins.enabled', 'plugins.entries'],
                                                             'update': update}).encode())
            entry = {'label': 'v0.0.1', 'commit': 'a' * 40,
                     'files': {'hermes_cli/plugins.py': {'stock': 'b' * 64, 'patched': 'c' * 64},
                               'agent/loop.py': {'stock': 'b' * 64, 'patched': 'd' * 64},
                               'hermes_cli/new_hook.py': {'stock': None, 'patched': 'e' * 64}},
                     'known_conflicts': ['The example-relay plugin replaces the delivery hook.']}
            value = {'host': {'source': '/home/owner/.hermes/hermes-agent'},
                     'dependencies': {'added': {'tree-sitter': ['0.26.0']}}}
            plan = {'services': {'roles': ['gateway'], 'created': [], 'consumers': []}}
            review = inplace_review(job, {'entry': entry}, value, plan)
        self.assertEqual(review['hermes']['files'], {'modified': ['agent/loop.py', 'hermes_cli/plugins.py'],
                                                     'added': ['hermes_cli/new_hook.py']})
        self.assertEqual((review['hermes']['modified'], review['hermes']['added']), (2, 1))
        self.assertEqual(review['configuration'], ['plugins.enabled', 'plugins.entries'])
        self.assertEqual(review['update'], update)
        self.assertEqual(review['known_conflicts'], ['The example-relay plugin replaces the delivery hook.'])
        self.assertEqual(review['packages'], ['tree-sitter==0.26.0'])
