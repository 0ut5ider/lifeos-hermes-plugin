# ABOUTME: Exercises HTTP memory credentials and native tools in disposable owner profiles.
# ABOUTME: Verifies resource binding, client isolation, live revocation, and restart persistence.

import asyncio
import json
from pathlib import Path
import unittest

from starlette.testclient import TestClient
from starlette.applications import Starlette
from lifeos_hook_bridge.memory_service import MemoryConfiguration
from lifeos_hook_bridge.memory_remote import MemoryRemote, MemoryRemoteMiddleware, MCP_PATH
import test_memory_native as native_fixture


class MemoryRemoteTests(unittest.TestCase):
    def setUp(self):
        self.fixture = native_fixture.NativeMemoryTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.path = self.fixture.home / 'hermes/lifeos-memory.json'
        self.configuration = MemoryConfiguration(self.path)
        self.configuration.save({'version': 1, 'root': str(self.fixture.root), 'principal': 'owner',
            'ownership_enabled': True, 'sharing_enabled': False,
            'accounts': {'dashboard:test:adrian': 'owner'}, 'destinations': {}, 'clients': {}})
        self.remote = MemoryRemote(self.path)
        self.owner = 'dashboard:test:adrian'

    def configure(self, base='http://127.0.0.1:9100'):
        return self.remote.configure({'enabled': True, 'public_url': base}, account=self.owner)

    def enroll(self, name='reader', **overrides):
        return self.remote.enroll({'client': name, 'read': ['project'], 'write_project': False,
            'projects': ['lab'], 'model_route': 'unknown', **overrides}, account=self.owner)

    def test_disabled_by_default_owner_required_and_https_for_remote_access(self):
        self.assertFalse(self.remote.status(account=self.owner)['enabled'])
        with self.assertRaises(PermissionError):
            self.remote.configure({'enabled': True, 'public_url': 'https://memory.example'}, account='dashboard:test:other')
        for url in ['http://192.168.8.252:9119', 'https://user:secret@example.com',
                    'https://example.com/path', 'https://example.com?token=bad', 'https://example.com#bad']:
            with self.subTest(url=url), self.assertRaises(ValueError):
                self.configure(url)
        self.assertTrue(self.configure('https://memory.example')['enabled'])

    def test_credentials_are_private_hashed_and_persist_across_restart(self):
        self.configure()
        credential = self.enroll()
        self.assertGreaterEqual(len(credential['token']), 40)
        self.assertEqual(MemoryRemote(self.path).authenticate(credential['token']), 'reader')
        self.assertNotIn(credential['token'], self.path.read_text())
        self.assertNotIn(credential['token'], self.remote.store.path.read_text())
        self.assertEqual(self.remote.store.path.stat().st_mode & 0o777, 0o600)
        self.assertNotIn('token', self.remote.status(account=self.owner))
        self.assertIsNone(self.remote.authenticate('wrong'))
        self.remote.revoke('reader', account=self.owner)
        self.assertIsNone(self.remote.authenticate(credential['token']))
        with self.assertRaises(ValueError):
            self.enroll()

    def test_a_copied_profile_cannot_reuse_a_connection_to_the_same_native_store(self):
        import shutil
        self.configure()
        credential = self.enroll()
        copied = self.fixture.home / 'another-profile/lifeos-memory.json'
        copied.parent.mkdir(mode=0o700)
        shutil.copy2(self.path, copied)
        other = MemoryRemote(copied)
        shutil.copy2(self.remote.store.path, other.store.path)
        self.assertIsNone(other.authenticate(credential['token']))

    def test_authority_and_resource_changes_invalidate_credentials(self):
        self.configure()
        first = self.enroll()
        self.configuration.update(lambda value: value.update(sharing_enabled=False))
        self.assertIsNone(self.remote.authenticate(first['token']))
        self.configuration.update(lambda value: value.update(sharing_enabled=True))
        self.assertEqual(self.remote.authenticate(first['token']), 'reader')
        self.configure('https://different.example')
        self.assertIsNone(self.remote.authenticate(first['token']))

    def test_disabled_plugin_and_oversized_requests_fail_closed(self):
        self.configure()
        credential = self.enroll()
        for available, expected in [(lambda: False, 404), (lambda: True, 413)]:
            with TestClient(MemoryRemoteMiddleware(Starlette(), configuration=self.path, available=available),
                            base_url='http://127.0.0.1:9100') as client:
                response = client.post(MCP_PATH, headers={'Authorization': 'Bearer ' + credential['token']},
                                       content=b'x' * (1024 * 1024 + 1))
                self.assertEqual(response.status_code, expected)

    def test_https_origin_rejects_plaintext_lan_requests_and_untrusted_proxy_headers(self):
        self.configure('https://memory.example')
        self.enroll()
        from lifeos_hook_bridge.memory_remote import RESOURCE_METADATA_PATH
        app = MemoryRemoteMiddleware(Starlette(), configuration=self.path)
        with TestClient(app, base_url='http://memory.example', client=('192.0.2.10', 5000)) as client:
            self.assertEqual(client.get(RESOURCE_METADATA_PATH).status_code, 400)
            self.assertEqual(client.get(RESOURCE_METADATA_PATH, headers={'X-Forwarded-Proto': 'https'}).status_code, 400)
        with TestClient(app, base_url='http://memory.example', client=('127.0.0.1', 5000)) as client:
            self.assertEqual(client.get(RESOURCE_METADATA_PATH).status_code, 200)

    def test_backup_recovery_retains_credentials_but_cannot_reuse_them(self):
        from test_profile_backup_recovery import ProfileRecoveryTests
        fixture = ProfileRecoveryTests(); fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        config = fixture.configuration
        config.update(lambda value: value.update(ownership_enabled=True,
            accounts={**value.get('accounts', {}), self.owner: value['principal']}))
        remote = MemoryRemote(config.path)
        remote.configure({'enabled': True, 'public_url': 'http://localhost:9100'}, account=self.owner)
        credential = remote.enroll({'client': 'backup-reader', 'read': ['project'], 'write_project': False,
            'projects': ['lab'], 'model_route': 'unknown'}, account=self.owner)
        self.assertEqual(remote.authenticate(credential['token']), 'backup-reader')
        result = fixture.recover(fixture.snapshot())
        candidate = MemoryRemote(Path(result['profile']) / config.path.name)
        self.assertTrue(candidate.store.path.is_file())
        self.assertIsNone(candidate.authenticate(credential['token']))
        candidate.configuration.update(lambda value: value.update(ownership_enabled=True, sharing_enabled=True))
        self.assertIsNone(candidate.authenticate(credential['token']))
        self.assertEqual(remote.authenticate(credential['token']), 'backup-reader')

    def test_http_challenge_host_origin_and_native_grants(self):
        saved = self.fixture.remember()
        self.fixture.remember('RULE: forbidden HTTP lab marker', 'private', 'principal')
        self.configure()
        first = self.enroll()
        second = self.enroll('other', projects=['other'])
        app = MemoryRemoteMiddleware(Starlette(), configuration=self.path)
        with TestClient(app, base_url='http://127.0.0.1:9100') as client:
            self.assertEqual(client.get('/unrelated').status_code, 404)
            challenge = client.post(MCP_PATH)
            self.assertEqual(challenge.status_code, 401)
            self.assertIn('resource_metadata=', challenge.headers['www-authenticate'])
            self.assertEqual(challenge.headers['cache-control'], 'no-store')
            headers = {'Authorization': 'Bearer ' + first['token'],
                       'Accept': 'application/json, text/event-stream', 'MCP-Protocol-Version': '2025-03-26'}
            message = {'jsonrpc': '2.0', 'id': 1, 'method': 'tools/call',
                       'params': {'name': 'lifeos_memory_search', 'arguments': {'query': 'synthetic lab'}}}
            response = client.post(MCP_PATH, headers=headers, json=message)
            self.assertEqual(response.status_code, 200, response.text)
            body = response.json()['result']['structuredContent']
            self.assertEqual(body['results'][0]['reference'], saved['reference'])
            self.assertNotIn('forbidden', json.dumps(body))
            message['params']['arguments'] = {'query': 'synthetic lab', 'client': 'owner'}
            self.assertEqual(client.post(MCP_PATH, headers=headers, json=message).json()['result']['structuredContent']['status'], 'rejected')
            message['params']['arguments'] = {'query': 'synthetic lab'}
            denied = client.post(MCP_PATH, headers={**headers, 'Authorization': 'Bearer ' + second['token']}, json=message)
            self.assertEqual(denied.json()['result']['structuredContent']['results'], [])
            for extra, expected in [({'Host': 'evil.example'}, 421), ({'Origin': 'https://evil.example'}, 403)]:
                self.assertEqual(client.post(MCP_PATH, headers={**headers, **extra}, json=message).status_code, expected)
            self.remote.revoke('reader', account=self.owner)
            self.assertEqual(client.post(MCP_PATH, headers=headers, json=message).status_code, 401)

    def test_oauth_owner_consent_pkce_single_use_refresh_and_revocation(self):
        import base64
        import hashlib
        from urllib.parse import urlsplit, parse_qs
        from lifeos_hook_bridge.memory_remote import HTTP_PREFIX, RESOURCE_METADATA_PATH, AUTH_METADATA_PATH
        from lifeos_hook_bridge.memory_oauth import MemoryAuthorization
        self.configure()
        self.configuration.update(lambda value: value.update(sharing_enabled=True))
        provider = MemoryAuthorization(self.remote)
        with TestClient(MemoryRemoteMiddleware(Starlette(), configuration=self.path), base_url='http://127.0.0.1:9100') as client:
            origin = 'http://127.0.0.1:9100'
            resource = origin + MCP_PATH
            self.assertEqual(client.get(RESOURCE_METADATA_PATH).json()['resource'], resource)
            metadata = client.get(AUTH_METADATA_PATH).json()
            self.assertEqual(metadata['issuer'], origin + HTTP_PREFIX)
            registration = client.post(HTTP_PREFIX + '/register', json={
                'client_name': 'Synthetic desktop', 'redirect_uris': ['http://127.0.0.1:9812/callback'],
                'token_endpoint_auth_method': 'none', 'grant_types': ['authorization_code', 'refresh_token'],
                'response_types': ['code'], 'scope': 'lifeos:memory'})
            self.assertEqual(registration.status_code, 201, registration.text)
            identifier = registration.json()['client_id']
            verifier = 'synthetic-verifier-' + 'a' * 50
            challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip('=')
            parameters = {'client_id': identifier, 'response_type': 'code', 'redirect_uri': 'http://127.0.0.1:9812/callback',
                          'code_challenge': challenge, 'code_challenge_method': 'S256', 'scope': 'lifeos:memory',
                          'state': 'synthetic-state', 'resource': resource}
            wrong = client.get(HTTP_PREFIX + '/authorize', params={**parameters, 'resource': 'https://other.example/mcp'}, follow_redirects=False)
            self.assertIn('error=', wrong.headers['location'])
            response = client.get(HTTP_PREFIX + '/authorize', params=parameters, follow_redirects=False)
            self.assertEqual(response.status_code, 302, response.text)
            pending = self.remote.status(account=self.owner)['pending']
            self.assertEqual(len(pending), 1)
            self.assertEqual(pending[0]['client_name'], 'Synthetic desktop')
            self.assertFalse(self.configuration.load()['clients'])
            grant = {'client': 'desktop', 'read': ['project'], 'write_project': False, 'projects': ['lab'], 'model_route': 'unknown'}
            with self.assertRaises(PermissionError):
                provider.approve(pending[0]['id'], grant, account='dashboard:test:other')
            approved = provider.approve(pending[0]['id'], grant, account=self.owner)
            callback = parse_qs(urlsplit(approved['redirect_url']).query)
            self.assertEqual(callback['state'], ['synthetic-state'])
            form = {'grant_type': 'authorization_code', 'client_id': identifier, 'code': callback['code'][0],
                    'redirect_uri': parameters['redirect_uri'], 'code_verifier': verifier, 'resource': resource}
            self.assertEqual(client.post(HTTP_PREFIX + '/token', data={**form, 'code_verifier': 'wrong'}).status_code, 400)
            self.assertEqual(client.post(HTTP_PREFIX + '/token', data={**form, 'resource': 'https://wrong.example'}).status_code, 400)
            issued = client.post(HTTP_PREFIX + '/token', data=form)
            self.assertEqual(issued.status_code, 200, issued.text)
            tokens = issued.json()
            self.assertEqual(self.remote.authenticate(tokens['access_token']), 'desktop')
            self.assertNotIn(tokens['access_token'], self.remote.store.path.read_text())
            self.assertNotIn(tokens['refresh_token'], self.remote.store.path.read_text())
            self.assertEqual(client.post(HTTP_PREFIX + '/token', data=form).status_code, 400)
            refresh = {'grant_type': 'refresh_token', 'client_id': identifier, 'refresh_token': tokens['refresh_token'], 'resource': resource}
            rotated = client.post(HTTP_PREFIX + '/token', data=refresh)
            self.assertEqual(rotated.status_code, 200, rotated.text)
            self.assertIsNone(self.remote.authenticate(tokens['access_token']))
            self.assertEqual(client.post(HTTP_PREFIX + '/token', data=refresh).status_code, 400)
            self.remote.revoke('desktop', account=self.owner)
            self.assertIsNone(self.remote.authenticate(rotated.json()['access_token']))
            self.assertEqual(client.post(HTTP_PREFIX + '/token', data={**refresh, 'refresh_token': rotated.json()['refresh_token']}).status_code, 400)

    def test_actual_http_sdk_connection_writes_reads_and_stops_after_revoke(self):
        self.exercise_http_connection(tls=False)

    def test_actual_https_sdk_connection_verifies_tls_and_native_permissions(self):
        self.exercise_http_connection(tls=True)

    def exercise_http_connection(self, *, tls):
        import socket
        import ssl
        import subprocess
        import threading
        import time
        import httpx2
        import uvicorn
        from mcp import Client
        from mcp.client.streamable_http import streamable_http_client
        listener = socket.socket()
        listener.bind(('127.0.0.1', 0))
        port = listener.getsockname()[1]
        origin = f"{'https' if tls else 'http'}://127.0.0.1:{port}"
        self.configure(origin)
        options = {}
        verify = True
        if tls:
            certificate, key = self.fixture.home / 'test-cert.pem', self.fixture.home / 'test-key.pem'
            subprocess.run(['openssl', 'req', '-x509', '-newkey', 'rsa:2048', '-nodes', '-days', '1',
                '-subj', '/CN=localhost', '-addext', 'subjectAltName=DNS:localhost,IP:127.0.0.1',
                '-keyout', str(key), '-out', str(certificate)], capture_output=True, check=True)
            key.chmod(0o600)
            options = {'ssl_certfile': str(certificate), 'ssl_keyfile': str(key)}
            verify = ssl.create_default_context(cafile=str(certificate))
        credential = self.enroll('writer', write_project=True)
        app = MemoryRemoteMiddleware(Starlette(), configuration=self.path)
        server = uvicorn.Server(uvicorn.Config(app, host='127.0.0.1', port=port, log_config=None, access_log=False, lifespan='off', ws='none', **options))
        thread = threading.Thread(target=server.run, kwargs={'sockets': [listener]}, daemon=True)
        thread.start()
        def cleanup():
            server.should_exit = True
            thread.join(10)
            listener.close()
            self.assertFalse(thread.is_alive(), 'The HTTP test server must stop')
        self.addCleanup(cleanup)
        deadline = time.monotonic() + 10
        while not server.started and time.monotonic() < deadline:
            time.sleep(0.01)
        self.assertTrue(server.started)
        async def exercise():
            async with httpx2.AsyncClient(headers={'Authorization': 'Bearer ' + credential['token']}, verify=verify) as http:
                async with Client(streamable_http_client(origin + MCP_PATH, http_client=http), cache=None) as client:
                    self.assertEqual(len((await client.list_tools()).tools), 9)
                    arguments = {'category': 'project', 'content': 'Synthetic HTTP SDK acceptance marker',
                                 'title': 'HTTP acceptance', 'project': 'lab', 'request_id': 'http-sdk-save'}
                    saved = (await client.call_tool('lifeos_memory_remember', arguments)).structured_content
                    self.assertEqual(saved['status'], 'committed', saved)
                    found = (await client.call_tool('lifeos_memory_search', {'query': 'HTTP SDK acceptance'})).structured_content
                    self.assertEqual(found['results'][0]['reference'], saved['reference'])
                    rejected = (await client.call_tool('lifeos_memory_remember', {**arguments, 'category': 'principal', 'request_id': 'http-denied'})).structured_content
                    self.assertEqual(rejected['status'], 'rejected')
            self.remote.revoke('writer', account=self.owner)
            async with httpx2.AsyncClient(headers={'Authorization': 'Bearer ' + credential['token']}, verify=verify) as http:
                response = await http.post(origin + MCP_PATH, json={})
                self.assertEqual(response.status_code, 401)
        asyncio.run(exercise())


if __name__ == '__main__':
    unittest.main()
