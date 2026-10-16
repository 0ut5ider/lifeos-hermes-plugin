# ABOUTME: Reproduces refresh replay and public registration admission failures with real HTTP requests.
# ABOUTME: Verifies owner recovery, bounded metadata, and credential publication before memory grants.

import asyncio
import base64
import hashlib
import json
import time
import unittest
from urllib.parse import parse_qs, urlsplit

from mcp.server.auth.provider import TokenError
from starlette.applications import Starlette
from starlette.testclient import TestClient

from lifeos_hook_bridge.memory_access import MemoryUnavailable
from lifeos_hook_bridge.memory_oauth import MemoryAuthorization
from lifeos_hook_bridge.memory_remote import HTTP_PREFIX, MCP_PATH, MemoryRemoteMiddleware
import test_memory_remote as remote_fixture


class MemoryOAuthSecurityTests(unittest.TestCase):
    def setUp(self):
        self.fixture = remote_fixture.MemoryRemoteTests(); self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.fixture.configure()
        self.remote = self.fixture.remote
        self.owner = self.fixture.owner
        self.remote.configuration.update(lambda value: value.update(sharing_enabled=True))
        self.origin = 'http://127.0.0.1:9100'
        self.client = self.enterContext(TestClient(MemoryRemoteMiddleware(Starlette(), configuration=self.fixture.path), base_url=self.origin, client=('127.0.0.1', 5000)))

    def register(self, **extra):
        return self.client.post(HTTP_PREFIX + '/register', json={
            'client_name': 'Synthetic security review', 'redirect_uris': ['http://127.0.0.1:9812/callback'],
            'token_endpoint_auth_method': 'none', 'grant_types': ['authorization_code', 'refresh_token'],
            'response_types': ['code'], 'scope': 'lifeos:memory', **extra})

    def tokens(self, grant):
        identifier = self.register().json()['client_id']
        verifier = 'synthetic-security-verifier-' + 'a' * 50
        challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip('=')
        params = {'client_id': identifier, 'response_type': 'code', 'redirect_uri': 'http://127.0.0.1:9812/callback',
                  'code_challenge': challenge, 'code_challenge_method': 'S256', 'scope': 'lifeos:memory',
                  'state': 'synthetic-security', 'resource': self.origin + MCP_PATH}
        response = self.client.get(HTTP_PREFIX + '/authorize', params=params, follow_redirects=False)
        self.assertEqual(response.status_code, 302, response.text)
        pending = self.remote.status(account=self.owner)['pending'][0]['id']
        approved = MemoryAuthorization(self.remote).approve(pending, {'client': grant, 'read': ['project'],
            'write_project': False, 'projects': ['lab'], 'model_route': 'unknown'}, account=self.owner)
        code = parse_qs(urlsplit(approved['redirect_url']).query)['code'][0]
        issued = self.client.post(HTTP_PREFIX + '/token', data={'grant_type': 'authorization_code',
            'client_id': identifier, 'code': code, 'redirect_uri': params['redirect_uri'],
            'code_verifier': verifier, 'resource': self.origin + MCP_PATH})
        self.assertEqual(issued.status_code, 200, issued.text)
        return identifier, issued.json()

    def refresh(self, identifier, token):
        return self.client.post(HTTP_PREFIX + '/token', data={'grant_type': 'refresh_token',
            'client_id': identifier, 'refresh_token': token, 'resource': self.origin + MCP_PATH})

    def test_refresh_replay_revokes_replacement_family_and_preserves_an_unrelated_client(self):
        identifier, first = self.tokens('first')
        other_id, other = self.tokens('other')
        rotated = self.refresh(identifier, first['refresh_token']).json()
        self.assertEqual(self.refresh(identifier, first['refresh_token']).status_code, 400)
        self.assertIsNone(self.remote.authenticate(rotated['access_token']))
        self.assertEqual(self.refresh(identifier, rotated['refresh_token']).status_code, 400)
        self.assertEqual(self.remote.authenticate(other['access_token']), 'other')
        self.assertEqual(self.refresh(other_id, other['refresh_token']).status_code, 200)

    def test_preloaded_refresh_race_raises_the_sdk_invalid_grant_and_revokes_the_family(self):
        identifier, first = self.tokens('race')
        provider = MemoryAuthorization(self.remote)
        client = asyncio.run(provider.get_client(identifier))
        loaded = asyncio.run(provider.load_refresh_token(client, first['refresh_token']))
        rotated = asyncio.run(provider.exchange_refresh_token(client, loaded, ['lifeos:memory']))
        with self.assertRaises(TokenError) as caught:
            asyncio.run(provider.exchange_refresh_token(client, loaded, ['lifeos:memory']))
        self.assertEqual(caught.exception.error, 'invalid_grant')
        self.assertIsNone(self.remote.authenticate(rotated.access_token))

    def test_registration_metadata_is_bounded_before_persistence(self):
        response = self.register(software_id='x' * 1000000)
        self.assertEqual(response.status_code, 400, response.text[:100])
        self.assertEqual(response.json()['error'], 'invalid_client_metadata')
        self.assertFalse(self.remote.store.load()['clients'])
        self.assertEqual(self.fixture.enroll()['status'], 'enrolled')
        self.assertLess(self.remote.store.path.stat().st_size, 4096)

    def test_unapproved_registration_limit_has_an_owner_recovery_path(self):
        from lifeos_hook_bridge.memory_oauth import UNAPPROVED_CLIENT_LIMIT
        identifier, tokens = self.tokens('retained')
        for _ in range(UNAPPROVED_CLIENT_LIMIT):
            self.assertEqual(self.register().status_code, 201)
        response = self.register()
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['error'], 'invalid_client_metadata')
        with self.assertRaises(PermissionError):
            self.remote.clear_unapproved(account='dashboard:test:other')
        result = self.remote.clear_unapproved(account=self.owner)
        self.assertEqual(result['registrations_removed'], UNAPPROVED_CLIENT_LIMIT)
        self.assertEqual(self.remote.authenticate(tokens['access_token']), 'retained')
        self.assertEqual(self.refresh(identifier, tokens['refresh_token']).status_code, 200)
        self.assertEqual(self.register().status_code, 201)

    def test_full_credential_file_cannot_persist_a_partial_owner_grant(self):
        self.remote.configuration.update(lambda value: value.update(sharing_enabled=False))
        with self.remote.store.transaction() as value:
            value['tokens']['synthetic-padding'] = {'expires_at': time.time() + 600, 'padding': ''}
            overhead = len((json.dumps(value, indent=2) + '\n').encode())
            value['tokens']['synthetic-padding']['padding'] = 'x' * (4 * 1024 * 1024 - overhead - 100)
        before = self.fixture.path.read_bytes()
        with self.assertRaises(MemoryUnavailable):
            self.fixture.enroll('not-published')
        self.assertEqual(self.fixture.path.read_bytes(), before)
        self.assertFalse(self.remote.configuration.load()['sharing_enabled'])


if __name__ == '__main__':
    unittest.main()
