# ABOUTME: Tests HTTP memory setup through authenticated Hermes dashboard sessions.
# ABOUTME: Verifies that anonymous MCP uses client credentials and owner actions retain session protection.

import importlib.util
import os
from pathlib import Path
import secrets
import unittest
from unittest.mock import patch

import test_memory_dashboard as dashboard_fixture
from fastapi import FastAPI
from fastapi.testclient import TestClient
from hermes_cli.dashboard_auth.middleware import gated_auth_middleware
from hermes_cli.dashboard_auth.routes import router as auth_router, _reset_password_rate_limit
from hermes_cli.dashboard_auth.registry import register_global_provider, restore_registration, snapshot_registration
from plugins.dashboard_auth.basic import BasicAuthProvider, hash_password
from lifeos_hook_bridge.memory_remote import install_http_memory, MCP_PATH, RESOURCE_METADATA_PATH
from lifeos_hook_bridge.memory_service import MemoryConfiguration
import test_memory_native as native_fixture


class MemoryRemoteDashboardTests(unittest.TestCase):
    def test_owner_setup_and_unauthenticated_protocol_discovery(self):
        fixture = native_fixture.NativeMemoryTests(); fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        path = fixture.home / '.hermes/lifeos-memory.json'
        MemoryConfiguration(path).save({'version': 1, 'root': str(fixture.root), 'principal': 'owner',
            'ownership_enabled': True, 'sharing_enabled': False, 'destinations': {}, 'clients': {},
            'accounts': {'dashboard:basic:synthetic-owner': 'owner'}})
        provider = BasicAuthProvider(username='synthetic-owner', password_hash=hash_password('synthetic-password'),
                                     secret=secrets.token_bytes(32))
        previous = snapshot_registration('basic')
        register_global_provider(provider)
        self.addCleanup(restore_registration, 'basic', provider, previous)
        _reset_password_rate_limit()
        self.addCleanup(_reset_password_rate_limit)
        with patch.dict(os.environ, {'HOME': str(fixture.home), 'HERMES_HOME': str(path.parent)}):
            source = Path(__file__).parents[1] / 'lifeos_hook_bridge/dashboard/plugin_api.py'
            spec = importlib.util.spec_from_file_location('remote_dashboard_test', source)
            module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
            app = FastAPI(); app.state.auth_required = True
            app.middleware('http')(gated_auth_middleware)
            app.include_router(auth_router)
            app.include_router(module.router, prefix='/api/plugins/lifeos-hook-bridge')
            module.install_memory_cache_headers(app)
            install_http_memory(app, path)
            endpoint = '/api/plugins/lifeos-hook-bridge/memory/http'
            with TestClient(app, base_url='http://127.0.0.1:9100') as client:
                self.assertEqual(client.get(endpoint + '/settings').status_code, 401)
                self.assertEqual(client.post('/auth/password-login', json={'provider': 'basic',
                    'username': 'synthetic-owner', 'password': 'synthetic-password'}).status_code, 200)
                response = client.post(endpoint + '/settings', json={'enabled': True, 'public_url': 'http://127.0.0.1:9100'})
                self.assertEqual(response.status_code, 200, response.text)
                self.assertEqual(response.headers['cache-control'], 'no-store')
                self.assertEqual(client.post(endpoint + '/settings', headers={'Origin': 'http://evil.example'},
                    json={'enabled': True, 'public_url': 'https://evil.example'}).status_code, 403)
                enrollment = client.post(endpoint + '/connections', json={'client': 'desktop', 'read': ['project'],
                    'write_project': False, 'projects': ['lab'], 'model_route': 'unknown'})
                self.assertEqual(enrollment.status_code, 200, enrollment.text)
                self.assertIn('token', enrollment.json())
                token = enrollment.json()['token']
                self.assertNotIn(token, client.get(endpoint + '/settings').text)
                response = client.post(endpoint + '/registrations/clear', json={})
                self.assertEqual(response.status_code, 200, response.text)
                self.assertTrue(response.json()['active_connections_preserved'])
                self.assertEqual(client.post(endpoint + '/registrations/clear', json={'caller': 'owner'}).status_code, 400)
                client.cookies.clear()
                self.assertEqual(client.get(RESOURCE_METADATA_PATH).status_code, 200)
                self.assertEqual(client.post(MCP_PATH).status_code, 401)
                self.assertEqual(client.get(endpoint + '/settings', headers={'Authorization': 'Bearer ' + token}).status_code, 401)
                self.assertEqual(client.post(endpoint + '/connections', headers={'Authorization': 'Bearer ' + token}, json={}).status_code, 401)
                self.assertEqual(client.post(endpoint + '/registrations/clear', headers={'Authorization': 'Bearer ' + token}, json={}).status_code, 401)


if __name__ == '__main__':
    unittest.main()
