# ABOUTME: Checks corrected OAuth boundaries against disposable native memory profiles.
# ABOUTME: Records safe protocol outcomes without retaining credentials or live memory.
import asyncio
import base64
import hashlib
import json
import time
from pathlib import Path
from urllib.parse import parse_qs, urlsplit
from starlette.applications import Starlette
from starlette.testclient import TestClient
from lifeos_hook_bridge.memory_remote import HTTP_PREFIX, MCP_PATH, MemoryRemoteMiddleware, MemoryRemote
from lifeos_hook_bridge.memory_oauth import MemoryAuthorization, UNAPPROVED_CLIENT_LIMIT
from test_memory_oauth_security import MemoryOAuthSecurityTests


def run():
    f = MemoryOAuthSecurityTests(); f.setUp()
    output = {}
    try:
        first_id, first = f.tokens('first')
        other_id, other = f.tokens('other')
        rotated = f.refresh(first_id, first['refresh_token']).json()
        # An unrelated registered client cannot invalidate a known refresh family.
        wrong = f.refresh(other_id, first['refresh_token'])
        output['wrong_client_refresh'] = {'status': wrong.status_code, 'family_retained': f.remote.authenticate(rotated['access_token']) == 'first'}
        # A fresh process object must recognize previously consumed hashes.
        f.remote = MemoryRemote(f.fixture.path)
        replay = f.refresh(first_id, first['refresh_token'])
        output['refresh_replay'] = {'status': replay.status_code,
            'replacement_revoked': f.remote.authenticate(rotated['access_token']) is None,
            'replacement_refresh_status': f.refresh(first_id, rotated['refresh_token']).status_code,
            'unrelated_retained': f.remote.authenticate(other['access_token']) == 'other'}
        # Anonymous admission exhaustion must not block the owner's separate token budget.
        accepted = [f.register().status_code for _ in range(UNAPPROVED_CLIENT_LIMIT)]
        blocked = f.register()
        owner_token = f.fixture.enroll('owner-after-full')
        output['registration_limit'] = {'accepted': accepted.count(201), 'blocked': blocked.status_code,
            'error': blocked.json()['error'], 'owner_enrollment': owner_token['status']}
        cleared = f.remote.clear_unapproved(account=f.owner)
        output['registration_recovery'] = {**cleared, 'next_status': f.register().status_code,
            'active_refresh_status': f.refresh(other_id, other['refresh_token']).status_code}
        # Repeated valid sign-in requests reach the pending budget and return an OAuth error.
        registration = f.register().json()
        verifier = 'independent-review-verifier-' + 'a' * 50
        challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip('=')
        params = {'client_id': registration['client_id'], 'response_type': 'code', 'redirect_uri': 'http://127.0.0.1:9812/callback',
            'code_challenge': challenge, 'code_challenge_method': 'S256', 'scope': 'lifeos:memory',
            'state': 'review', 'resource': f.origin + MCP_PATH}
        for _ in range(100):
            assert f.client.get(HTTP_PREFIX + '/authorize', params=params, follow_redirects=False).status_code == 302
        full = f.client.get(HTTP_PREFIX + '/authorize', params=params, follow_redirects=False)
        output['pending_limit'] = {'status': full.status_code, 'oauth_error': parse_qs(urlsplit(full.headers.get('location', '')).query).get('error')}
        f.remote.clear_unapproved(account=f.owner)
        # Expiry cleanup occurs before quota evaluation.
        f.register()
        with f.remote.store.transaction() as value:
            for item in value['clients'].values():
                if not item.get('approved'): item['expires_at'] = time.time() - 1
        output['expired_registration'] = {'next_status': f.register().status_code,
            'remaining_unapproved': sum(not item.get('approved') for item in f.remote.store.load()['clients'].values())}
        # A binding change after credential lookup must return the SDK exception.
        provider = MemoryAuthorization(f.remote)
        oauth_client = asyncio.run(provider.get_client(other_id))
        current_tokens = f.tokens('binding-race')
        binding_id, binding_tokens = current_tokens
        binding_client = asyncio.run(provider.get_client(binding_id))
        loaded = asyncio.run(provider.load_refresh_token(binding_client, binding_tokens['refresh_token']))
        f.remote.configuration.update(lambda value: value.update(sharing_enabled=False))
        error = None
        try:
            asyncio.run(provider.exchange_refresh_token(binding_client, loaded, ['lifeos:memory']))
        except Exception as caught:
            error = type(caught).__name__
        output['binding_change_error'] = error
        f.remote.configuration.update(lambda value: value.update(sharing_enabled=True))
        # Localhost origins must remain local even if the shared listener accepts LAN sockets.
        app = MemoryRemoteMiddleware(Starlette(), configuration=f.fixture.path)
        with TestClient(app, base_url=f.origin, client=('192.0.2.20', 23456)) as remote_client:
            response = remote_client.post(MCP_PATH, headers={'Authorization': 'Bearer ' + owner_token['token'],
                'Accept': 'application/json, text/event-stream', 'MCP-Protocol-Version': '2025-03-26'},
                json={'jsonrpc': '2.0', 'id': 1, 'method': 'tools/list', 'params': {}})
            output['plaintext_nonloopback_localhost_origin'] = {'status': response.status_code,
                'tools_returned': len(response.json().get('result', {}).get('tools', []))}
    finally:
        f.doCleanups()
    return output

if __name__ == '__main__':
    result = run()
    Path(__file__).with_name('probe-results.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
