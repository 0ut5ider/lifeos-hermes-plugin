# ABOUTME: Reproduces OAuth replay and registration exhaustion in disposable synthetic profiles.
# ABOUTME: Writes only safe measurements and never reads a live memory store.

import asyncio
import base64
import hashlib
import json
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from starlette.applications import Starlette
from starlette.testclient import TestClient
from lifeos_hook_bridge.memory_remote import HTTP_PREFIX, MCP_PATH, MemoryRemoteMiddleware
from lifeos_hook_bridge.memory_oauth import MemoryAuthorization
from test_memory_remote import MemoryRemoteTests


def profile():
    fixture = MemoryRemoteTests()
    fixture.setUp()
    fixture.configure()
    fixture.configuration.update(lambda value: value.update(sharing_enabled=True))
    return fixture


def register(client, **extra):
    return client.post(HTTP_PREFIX + '/register', json={
        'client_name': 'Synthetic independent review',
        'redirect_uris': ['http://127.0.0.1:9812/callback'],
        'token_endpoint_auth_method': 'none',
        'grant_types': ['authorization_code', 'refresh_token'],
        'response_types': ['code'], 'scope': 'lifeos:memory', **extra})


def replay_refresh():
    fixture = profile()
    try:
        origin = 'http://127.0.0.1:9100'
        with TestClient(MemoryRemoteMiddleware(Starlette(), configuration=fixture.path), base_url=origin) as client:
            identifier = register(client).json()['client_id']
            verifier = 'synthetic-independent-review-verifier-' + 'a' * 50
            challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip('=')
            parameters = {'client_id': identifier, 'response_type': 'code', 'redirect_uri': 'http://127.0.0.1:9812/callback',
                'code_challenge': challenge, 'code_challenge_method': 'S256', 'scope': 'lifeos:memory',
                'state': 'synthetic-review', 'resource': origin + MCP_PATH}
            response = client.get(HTTP_PREFIX + '/authorize', params=parameters, follow_redirects=False)
            assert response.status_code == 302
            pending = fixture.remote.status(account=fixture.owner)['pending'][0]['id']
            grant = {'client': 'review-desktop', 'read': ['project'], 'write_project': False,
                'projects': ['lab'], 'model_route': 'unknown'}
            approved = MemoryAuthorization(fixture.remote).approve(pending, grant, account=fixture.owner)
            code = parse_qs(urlsplit(approved['redirect_url']).query)['code'][0]
            first = client.post(HTTP_PREFIX + '/token', data={
                'grant_type': 'authorization_code', 'client_id': identifier, 'code': code,
                'redirect_uri': parameters['redirect_uri'], 'code_verifier': verifier, 'resource': origin + MCP_PATH})
            assert first.status_code == 200
            first = first.json()
            form = {'grant_type': 'refresh_token', 'client_id': identifier,
                'refresh_token': first['refresh_token'], 'resource': origin + MCP_PATH}
            replacement = client.post(HTTP_PREFIX + '/token', data=form)
            assert replacement.status_code == 200
            replacement = replacement.json()
            replay = client.post(HTTP_PREFIX + '/token', data=form)
            headers = {'Authorization': 'Bearer ' + replacement['access_token'],
                'Accept': 'application/json, text/event-stream', 'MCP-Protocol-Version': '2025-03-26'}
            continued = client.post(origin + MCP_PATH, headers=headers,
                json={'jsonrpc': '2.0', 'id': 1, 'method': 'tools/list', 'params': {}})
            refresh_after_replay = client.post(HTTP_PREFIX + '/token', data={**form,
                'refresh_token': replacement['refresh_token']})
            # A second worker can load the same token before the first worker exchanges it.
            current = refresh_after_replay.json()
            provider = MemoryAuthorization(fixture.remote)
            oauth_client = asyncio.run(provider.get_client(identifier))
            loaded = asyncio.run(provider.load_refresh_token(oauth_client, current['refresh_token']))
            asyncio.run(provider.exchange_refresh_token(oauth_client, loaded, ['lifeos:memory']))
            race_error = None
            try:
                asyncio.run(provider.exchange_refresh_token(oauth_client, loaded, ['lifeos:memory']))
            except Exception as caught:
                race_error = type(caught).__name__ + ': ' + str(caught)
            return {'original_refresh': 200, 'replay_status': replay.status_code,
                'replacement_access_after_replay': continued.status_code,
                'replacement_refresh_after_replay': refresh_after_replay.status_code,
                'replacement_stays_authorized': continued.status_code == 200 and refresh_after_replay.status_code == 200,
                'preloaded_refresh_race_error': race_error}
    finally:
        fixture.doCleanups()


def exhaust_registration_count():
    fixture = profile()
    try:
        with TestClient(MemoryRemoteMiddleware(Starlette(), configuration=fixture.path),
                base_url='http://127.0.0.1:9100', raise_server_exceptions=False) as client:
            codes = [register(client).status_code for _ in range(512)]
            blocked = register(client)
            fixture.remote.configure({'enabled': False, 'public_url': 'http://127.0.0.1:9100'}, account=fixture.owner)
            fixture.remote.configure({'enabled': True, 'public_url': 'http://127.0.0.1:9100'}, account=fixture.owner)
            blocked_after_reset = register(client)
            state = fixture.remote.store.load()
            return {'accepted_registrations': codes.count(201), 'next_status': blocked.status_code,
                'next_error_body': blocked.text, 'count_after_disable_enable': len(state['clients']),
                'after_disable_enable_status': blocked_after_reset.status_code,
                'grants_created': len(fixture.configuration.load()['clients']),
                'retention_days': 365}
    finally:
        fixture.doCleanups()


def exhaust_registration_bytes():
    fixture = profile()
    try:
        with TestClient(MemoryRemoteMiddleware(Starlette(), configuration=fixture.path),
                base_url='http://127.0.0.1:9100', raise_server_exceptions=False) as client:
            large = [register(client, software_id='x' * 1000000).status_code for _ in range(4)]
            size = fixture.remote.store.path.stat().st_size
            # Exact remaining registration budget leaves fewer bytes than one personal token entry.
            remaining = 4 * 1024 * 1024 - size
            overhead_trial = register(client, software_id='x')
            overhead = fixture.remote.store.path.stat().st_size - size - 1
            fill = register(client, software_id='x' * (remaining - overhead * 2 - 120))
            before = fixture.remote.store.path.stat().st_size
            error = None
            try:
                fixture.enroll('review-owner-token')
            except Exception as caught:
                error = type(caught).__name__ + ': ' + str(caught)
            grant = fixture.configuration.load()['clients'].get('review-owner-token')
            return {'large_registration_statuses': large, 'metadata_trial_status': overhead_trial.status_code,
                'fill_registration_status': fill.status_code, 'stored_bytes': before,
                'remaining_bytes': 4 * 1024 * 1024 - before,
                'owner_enrollment_error': error, 'uncredentialed_owner_grant_created': bool(grant)}
    finally:
        fixture.doCleanups()


if __name__ == '__main__':
    output = Path(__file__).with_name('probe-results.json')
    result = {}
    for name, operation in [('refresh_replay', replay_refresh), ('registration_count', exhaust_registration_count),
                            ('registration_bytes', exhaust_registration_bytes)]:
        result[name] = operation()
        output.write_text(json.dumps(result, indent=2) + '\n')
        print(json.dumps({name: result[name]}, indent=2), flush=True)
