# ABOUTME: Independently checks HTTP transport boundaries and OAuth revocation in synthetic profiles.
# ABOUTME: Records protocol outcomes without storing credentials or using live services.
import asyncio
import importlib.util
import json
from pathlib import Path
from starlette.applications import Starlette
from starlette.testclient import TestClient
from lifeos_hook_bridge.memory_remote import (
    AUTH_METADATA_PATH, HTTP_PREFIX, MCP_PATH, RESOURCE_METADATA_PATH,
    MemoryRemoteMiddleware, public_origin,
)
from test_memory_oauth_security import MemoryOAuthSecurityTests


def prior_boundary_checks():
    path = Path(__file__).parents[1] / '2026-10-16-http-memory-review-2/review_probes.py'
    spec = importlib.util.spec_from_file_location('previous_independent_probes', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    result = module.run()
    assert result['refresh_replay']['replacement_revoked']
    assert result['refresh_replay']['replacement_refresh_status'] == 400
    assert result['registration_limit']['accepted'] == 128
    assert result['registration_limit']['blocked'] == 400
    assert result['registration_recovery']['active_refresh_status'] == 200
    assert result['pending_limit']['oauth_error'] == ['temporarily_unavailable']
    assert result['binding_change_error'] == 'TokenError'
    assert result['plaintext_nonloopback_localhost_origin'] == {'status': 400, 'tools_returned': 0}
    return result


def transport_checks():
    fixture = MemoryOAuthSecurityTests(); fixture.setUp()
    try:
        credential = fixture.fixture.enroll('transport')
        app = MemoryRemoteMiddleware(Starlette(), configuration=fixture.fixture.path)
        routes = [RESOURCE_METADATA_PATH, AUTH_METADATA_PATH,
                  HTTP_PREFIX + '/authorize', HTTP_PREFIX + '/token',
                  HTTP_PREFIX + '/register', HTTP_PREFIX + '/revoke', MCP_PATH]
        methods = ['GET', 'GET', 'GET', 'POST', 'POST', 'POST', 'POST']
        headers = {'Authorization': 'Bearer ' + credential['token'],
                   'Accept': 'application/json, text/event-stream', 'MCP-Protocol-Version': '2025-03-26'}
        output = {}
        for peer in [('192.0.2.20', 12345), None]:
            with TestClient(app, base_url=fixture.origin, client=peer) as client:
                statuses = [client.request(method, route, headers=headers).status_code
                            for method, route in zip(methods, routes)]
                assert statuses == [400] * len(routes), statuses
                output['remote' if peer else 'missing_peer'] = dict(zip(routes, statuses))
        fixture.remote.configure({'enabled': True, 'public_url': 'https://memory.example:443'}, account=fixture.owner)
        fixture.remote.configuration.update(lambda value: value.update(sharing_enabled=True))
        assert fixture.remote.status(account=fixture.owner)['public_url'] == 'https://memory.example'
        with TestClient(app, base_url='https://memory.example', client=('192.0.2.20', 12345)) as client:
            response = client.get(RESOURCE_METADATA_PATH)
            assert response.status_code == 200
            output['direct_https_nonloopback'] = response.status_code
        with TestClient(app, base_url='http://memory.example', client=('127.0.0.1', 12345)) as client:
            response = client.get(RESOURCE_METADATA_PATH)
            assert response.status_code == 200
            output['local_tls_proxy'] = response.status_code
        with TestClient(app, base_url='http://memory.example', client=('192.0.2.20', 12345)) as client:
            response = client.get(RESOURCE_METADATA_PATH, headers={'X-Forwarded-Proto': 'https'})
            assert response.status_code == 400
            output['untrusted_forwarded_proto'] = response.status_code
        assert public_origin('http://localhost:80') == 'http://localhost'
        assert public_origin('https://[::1]:443') == 'https://[::1]'
        output['default_port_canonicalization'] = True
        return output
    finally:
        fixture.doCleanups()


if __name__ == '__main__':
    result = {'previous_findings': prior_boundary_checks(), 'transport_boundaries': transport_checks()}
    Path(__file__).with_name('probe-results.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
