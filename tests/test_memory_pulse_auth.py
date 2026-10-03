# ABOUTME: Exercises PULSE owner requests through real Hermes dashboard authentication.
# ABOUTME: Uses isolated native facts and private account bindings for each request.
import importlib.util
import os
from pathlib import Path
import secrets
import sys
import unittest
from unittest.mock import patch

HOST = Path(os.environ.get('LIFEOS_HERMES_SOURCE', str(Path.home() /
    '.cache/lifeos-plugin-memory/source-gate-20261001-cortex-final/hermes')))
sys.path.insert(0, str(HOST))

from fastapi import FastAPI
from fastapi.testclient import TestClient
from hermes_cli.dashboard_auth.cookies import SESSION_AT_COOKIE
from hermes_cli.dashboard_auth.middleware import gated_auth_middleware
from hermes_cli.dashboard_auth.registry import register_global_provider, restore_registration, snapshot_registration
from hermes_cli.dashboard_auth.routes import router as auth_router, _reset_password_rate_limit
from plugins.dashboard_auth.basic import BasicAuthProvider, hash_password
from lifeos_hook_bridge.memory_service import MemoryConfiguration
import test_memory_pulse as pulse_fixture
from test_memory_sharing import public_key


class MemoryPulseAuthTests(unittest.TestCase):
    endpoint = '/api/plugins/lifeos-hook-bridge/memory/pulse/'

    def setUp(self):
        _reset_password_rate_limit()
        self.addCleanup(_reset_password_rate_limit)
        self.fixture = pulse_fixture.MemoryPulseTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.home = self.fixture.fixture.fixture.fixture.home
        self.profile = self.home / 'hermes'
        self.configuration = MemoryConfiguration(self.profile / 'lifeos-memory.json')
        config = self.fixture.fixture.fixture.configuration.load()
        config['accounts']['dashboard:basic:synthetic-owner'] = config['principal']
        self.configuration.save(config)
        self.fixture.fixture.fixture.fixture.remember('RULE: Synthetic authenticated PULSE fact',
                                                     'http-pulse', 'principal')
        self.environment = patch.dict(os.environ, {'HOME': str(self.home), 'HERMES_HOME': str(self.profile)})
        self.environment.start()
        self.addCleanup(self.environment.stop)
        previous = snapshot_registration('basic')
        self.provider = BasicAuthProvider(username='synthetic-owner', password_hash=hash_password('synthetic-password'),
                                          secret=secrets.token_bytes(32))
        register_global_provider(self.provider)
        self.addCleanup(restore_registration, 'basic', self.provider, previous)
        api = Path(__file__).parents[1] / 'lifeos_hook_bridge/dashboard/plugin_api.py'
        spec = importlib.util.spec_from_file_location('pulse_authenticated_test_api', api)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.app = FastAPI()
        self.app.state.auth_required = True
        self.app.middleware('http')(gated_auth_middleware)
        module.install_memory_cache_headers(self.app)
        self.app.include_router(auth_router)
        self.app.include_router(module.router, prefix='/api/plugins/lifeos-hook-bridge')
        self.client = TestClient(self.app)
        self.client.__enter__()
        self.addCleanup(self.client.__exit__, None, None, None)

    def login(self):
        response = self.client.post('/auth/password-login', json={'provider': 'basic',
            'username': 'synthetic-owner', 'password': 'synthetic-password'})
        self.assertEqual(response.status_code, 200, response.text)
        return self.client.cookies.get(SESSION_AT_COOKIE)

    def memory_requests(self):
        base = '/api/plugins/lifeos-hook-bridge/memory'
        return [(method, base + path, body) for method, path, body in (
            ('GET', '', None), ('POST', '/review', {'tool': 'lifeos_memory_search',
                'arguments': {'query': 'authenticated PULSE'}}),
            ('POST', '/adoption/preview', {}),
            ('POST', '/adoption', {'signature': 'synthetic-preview', 'projects': {}, 'request_id': 'denied-adopt'}),
            ('POST', '/sharing', {'enabled': True}),
            ('POST', '/connections', {'client': 'denied-client', 'public_key': public_key(90),
                'projects': ['lab'], 'model_route': 'unknown'}),
            ('DELETE', '/connections/absent-client', None),
            ('GET', '/pulse/snapshot', None), ('GET', '/wiki?target=%2Fapi%2Fwiki', None))]

    def assert_memory_routes_deny(self, status):
        before = self.configuration.path.read_bytes()
        for method, endpoint, body in self.memory_requests():
            with self.subTest(method=method, endpoint=endpoint):
                response = self.client.request(method, endpoint, json=body)
                self.assertEqual(response.status_code, status, response.text)
                self.assertEqual(response.headers.get('cache-control'), 'no-store')
                self.assertNotIn('Synthetic authenticated PULSE fact', response.text)
        self.assertEqual(self.configuration.path.read_bytes(), before)

    def test_every_memory_route_requires_a_verified_session_when_host_gate_is_disabled(self):
        self.app.state.auth_required = False
        self.assert_memory_routes_deny(401)

    def test_every_memory_route_rechecks_revoked_account_binding(self):
        self.login()
        self.configuration.update(lambda config: config['accounts'].pop('dashboard:basic:synthetic-owner'))
        self.assert_memory_routes_deny(403)

    def test_distinct_authenticated_account_without_binding_cannot_read_or_change_memory(self):
        other = BasicAuthProvider(username='synthetic-other', password_hash=hash_password('synthetic-other-password'),
                                  secret=secrets.token_bytes(32))
        register_global_provider(other)
        self.addCleanup(restore_registration, 'basic', other, self.provider)
        response = self.client.post('/auth/password-login', json={'provider': 'basic',
            'username': 'synthetic-other', 'password': 'synthetic-other-password'})
        self.assertEqual(response.status_code, 200, response.text)
        self.assert_memory_routes_deny(403)

    def test_revoked_owner_cannot_forget_a_native_fact(self):
        self.login()
        base = '/api/plugins/lifeos-hook-bridge/memory'
        result = self.client.post(base + '/review', json={'tool': 'lifeos_memory_search',
            'arguments': {'query': 'authenticated PULSE'}}).json()
        reference = result['results'][0]['reference']
        self.configuration.update(lambda config: config['accounts'].pop('dashboard:basic:synthetic-owner'))
        response = self.client.post(base + '/review', json={'tool': 'lifeos_memory_forget',
            'arguments': {'reference': reference, 'request_id': 'revoked-owner-forget'}})
        self.assertEqual(response.status_code, 403, response.text)
        from test_memory_native import OWNER
        self.assertEqual(self.fixture.fixture.fixture.fixture.memory.get(OWNER, reference)['status'], 'ok')

    def test_password_login_preserves_all_four_governed_views(self):
        self.login()
        for view in ('snapshot', 'state', 'health', 'runs'):
            with self.subTest(view=view):
                response = self.client.get(self.endpoint + view)
                self.assertEqual(response.status_code, 200, response.text)
                self.assertEqual(response.headers['cache-control'], 'no-store')
                self.assertNotIn('etag', response.headers)
        self.assertEqual(self.client.get(self.endpoint + 'snapshot').json()['principalMemory']['entries'],
                         ['RULE: Synthetic authenticated PULSE fact'])

    def test_anonymous_or_fabricated_identity_never_admits_owner(self):
        for headers in ({}, {'X-LifeOS-Owner': 'owner', 'X-Forwarded-User': 'synthetic-owner'},
                        {'Authorization': 'Bearer invalid-synthetic-token'}):
            with self.subTest(headers=headers):
                response = self.client.get(self.endpoint + 'snapshot', headers=headers)
                self.assertEqual(response.status_code, 401, response.text)
                self.assertNotIn('Synthetic authenticated PULSE fact', response.text)

    def test_disabled_host_gate_does_not_mint_an_owner_scope(self):
        self.app.state.auth_required = False
        response = self.client.get(self.endpoint + 'snapshot')
        self.assertEqual(response.status_code, 401, response.text)
        self.assertEqual(response.headers['cache-control'], 'no-store')

    def test_account_binding_and_principal_are_rechecked_on_same_connection(self):
        self.login()
        self.assertEqual(self.client.get(self.endpoint + 'snapshot').status_code, 200)
        self.configuration.update(lambda config: config['accounts'].pop('dashboard:basic:synthetic-owner'))
        response = self.client.get(self.endpoint + 'snapshot', headers={'X-LifeOS-Owner': 'owner'})
        self.assertEqual(response.status_code, 403, response.text)
        self.assertEqual(response.headers['cache-control'], 'no-store')
        self.configuration.update(lambda config: config['accounts'].update({'dashboard:basic:synthetic-owner': 'other'}))
        self.assertEqual(self.client.get(self.endpoint + 'snapshot').status_code, 403)

    def test_changed_installation_binding_refuses_private_snapshot(self):
        self.login()
        self.configuration.update(lambda config: config.update(root=str(self.home / 'other-install')))
        response = self.client.get(self.endpoint + 'snapshot')
        self.assertEqual(response.status_code, 503, response.text)
        self.assertNotIn(str(self.home), response.text)

    def test_bad_bearer_does_not_fall_back_to_valid_cookie(self):
        self.login()
        response = self.client.get(self.endpoint + 'snapshot', headers={'Authorization': 'Bearer invalid-token'})
        self.assertEqual(response.status_code, 401)

    def test_browser_logout_removes_cookie_authority(self):
        self.login()
        response = self.client.post('/auth/logout', follow_redirects=False)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.client.get(self.endpoint + 'snapshot').status_code, 401)

    def test_read_only_routes_ignore_no_caller_scope_or_source_arguments(self):
        self.login()
        self.assertEqual(self.client.post(self.endpoint + 'snapshot', json={}).status_code, 405)
        self.assertEqual(self.client.get(self.endpoint + 'graph').status_code, 422)
        self.assertEqual(self.client.get(self.endpoint + 'snapshot', params={'account': 'owner'}).status_code, 400)

    def test_host_and_framework_denials_always_disable_response_storage(self):
        anonymous = self.client.get(self.endpoint + 'snapshot')
        self.assertEqual(anonymous.headers.get('cache-control'), 'no-store')
        self.login()
        denied = [self.client.get(self.endpoint + 'snapshot', headers={'Authorization': 'Bearer invalid-token'}),
                  self.client.get(self.endpoint + 'graph'), self.client.post(self.endpoint + 'snapshot', json={})]
        for response in denied:
            self.assertEqual(response.headers.get('cache-control'), 'no-store', response.text)

    def test_corrupt_registry_returns_sanitized_unavailable_response(self):
        self.login()
        self.fixture.fixture.fixture.fixture.memory.database.write_bytes(b'Synthetic corrupt registry')
        response = self.client.get(self.endpoint + 'snapshot')
        self.assertEqual(response.status_code, 503, response.text)
        self.assertEqual(response.json(), {'error': 'Memory is unavailable under the current installation policy'})
        self.assertEqual(response.headers.get('cache-control'), 'no-store')

    def test_private_response_headers_leave_unrelated_routes_unchanged(self):
        response = self.client.get('/api/unrelated')
        self.assertEqual(response.status_code, 401)
        self.assertIsNone(response.headers.get('cache-control'))
