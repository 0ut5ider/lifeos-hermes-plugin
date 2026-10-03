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
from hermes_cli.dashboard_auth.routes import router as auth_router
from plugins.dashboard_auth.basic import BasicAuthProvider, hash_password
from lifeos_hook_bridge.memory_service import MemoryConfiguration
import test_memory_pulse as pulse_fixture


class MemoryPulseAuthTests(unittest.TestCase):
    endpoint = '/api/plugins/lifeos-hook-bridge/memory/pulse/'

    def setUp(self):
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
