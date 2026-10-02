# ABOUTME: Checks recovery admission through a loopback HTTP server and real password authentication.
# ABOUTME: Records rejected state preservation and accepted action-bound grants at the captured launch boundary.
import hashlib
import json
from pathlib import Path
import secrets
import socket
import threading
import time
from unittest.mock import patch

import httpx
import uvicorn
from hermes_cli.dashboard_auth.registry import register_global_provider, restore_registration
from plugins.dashboard_auth.basic import BasicAuthProvider, hash_password
from test_memory_admin_dashboard import MemoryAdminDashboardTests

OUTPUT = Path(__file__).parent
assert hashlib.sha256(Path('lifeos_hook_bridge/dashboard/plugin_api.py').read_bytes()).hexdigest() == json.loads((OUTPUT/'source-pins.json').read_text())['lifeos_hook_bridge/dashboard/plugin_api.py'], 'Reviewed source changed'
results = []
case = MemoryAdminDashboardTests()
case.setUp()
server = None
thread = None
try:
    job = case.interrupted_job()
    sock = socket.socket()
    sock.bind(('127.0.0.1', 0))
    origin = f'http://127.0.0.1:{sock.getsockname()[1]}'
    server = uvicorn.Server(uvicorn.Config(case.app, log_level='warning', access_log=False))
    thread = threading.Thread(target=server.run, kwargs={'sockets': [sock]}, daemon=True)
    thread.start()
    deadline = time.monotonic() + 10
    while not server.started:
        if time.monotonic() > deadline:
            raise RuntimeError('Loopback server failed to start')
        time.sleep(0.01)
    path = case.prefix + '/update/recover'
    launched = []
    admin = case.fixture.fixture.admin()
    initial_request = (job / 'request.json').read_bytes()
    initial_status = (job / 'status.json').read_bytes()
    watched = [job / 'request.json', job / 'status.json', job / 'snapshot/manifest.json', case.configuration.path]

    def state():
        return {str(p.relative_to(case.fixture.profile)) if p.is_relative_to(case.fixture.profile) else p.name:
                {'sha256': hashlib.sha256(p.read_bytes()).hexdigest(), 'mode': p.stat().st_mode & 0o777}
                for p in watched} | {'grants': sorted(p.name for p in case.grants())}

    def login(client, username='synthetic-owner', password='synthetic-password'):
        response = client.post('/auth/password-login', json={'provider': 'basic', 'username': username, 'password': password})
        assert response.status_code == 200, response.text

    def rejected(client, name, expected, method='POST', url=path, **options):
        before = state()
        before_launches = len(launched)
        response = client.request(method, url, **options)
        row = {'case': name, 'method': method, 'status': response.status_code, 'expected': expected,
               'response': response.text, 'unchanged': state() == before,
               'new_launch_count': len(launched) - before_launches, 'state_before': before, 'state_after': state()}
        results.append(row)
        print(json.dumps({k:v for k,v in row.items() if k not in ('state_before', 'state_after')}), flush=True)
        assert response.status_code == expected, row
        assert row['unchanged'] and row['new_launch_count'] == 0, row

    with patch.object(case.api, '_launch_lifeos_update', side_effect=lambda job, action: launched.append((job, action))), \
            httpx.Client(base_url=origin, trust_env=False, timeout=10) as owner, \
            httpx.Client(base_url=origin, trust_env=False, timeout=10) as anonymous:
        rejected(anonymous, 'anonymous_gate_enabled', 401)
        rejected(anonymous, 'anonymous_fabricated_identity', 401,
                 headers={'X-LifeOS-Owner': 'owner', 'X-Forwarded-User': 'synthetic-owner'})
        case.app.state.auth_required = False
        rejected(anonymous, 'anonymous_gate_disabled', 401)
        rejected(anonymous, 'anonymous_gate_disabled_bad_origin_and_body', 401,
                 headers={'Origin': 'https://other.invalid', 'X-LifeOS-Owner': 'owner'}, json={'account': case.account})
        case.app.state.auth_required = True
        login(owner)
        rejected(owner, 'invalid_bearer_with_owner_cookie', 401, headers={'Authorization': 'Bearer invalid-synthetic-token'})
        for name, value in [('different_origin', 'https://other.invalid'), ('null_origin', 'null'),
                            ('different_scheme', origin.replace('http:', 'https:'))]:
            rejected(owner, name, 403, headers={'Origin': value})
        for name, suffix in [('job_query', '?job=other'), ('account_query', '?account=dashboard%3Abasic%3Asynthetic-other'),
                             ('empty_query_value', '?job='), ('bare_query_key', '?job'), ('repeated_query', '?job=x&job=y')]:
            rejected(owner, name, 400, url=path + suffix)
        for name, body, content_type in [('json_job', b'{"job":"other"}', 'application/json'),
                                        ('json_empty_object', b'{}', 'application/json'),
                                        ('json_null', b'null', 'application/json'),
                                        ('malformed_json', b'{', 'application/json'),
                                        ('whitespace', b' ', 'text/plain'),
                                        ('form_body', b'job=other', 'application/x-www-form-urlencoded'),
                                        ('binary_body', b'\x00', 'application/octet-stream')]:
            rejected(owner, name, 400, content=body, headers={'Content-Type': content_type})
        rejected(owner, 'chunked_body', 400, content=iter([b'{', b'}']))
        for method in ['GET', 'HEAD', 'PUT', 'PATCH', 'DELETE', 'OPTIONS']:
            rejected(owner, 'method_' + method.lower(), 405, method=method)
        case.configuration.update(lambda config: config['accounts'].pop(case.account))
        rejected(owner, 'revoked_owner', 403)
        case.configuration.update(lambda config: config['accounts'].update({case.account: config['principal']}))
        other = BasicAuthProvider(username='synthetic-other', password_hash=hash_password('synthetic-other-password'),
                                  secret=secrets.token_bytes(32))
        register_global_provider(other)
        try:
            with httpx.Client(base_url=origin, trust_env=False, timeout=10) as unbound:
                login(unbound, 'synthetic-other', 'synthetic-other-password')
                rejected(unbound, 'authenticated_unbound_account', 403)
        finally:
            restore_registration('basic', other, case.provider)
        for name, headers in [('valid_current_origin_no_body', {'Origin': origin}),
                              ('valid_no_origin_no_body', {}),
                              ('valid_zero_length_json_content_type', {'Origin': origin, 'Content-Type': 'application/json'})]:
            before_count = len(launched)
            response = owner.post(path, headers=headers)
            assert response.status_code == 200, response.text
            assert launched[-1] == (job, 'recover') and len(launched) == before_count + 1
            request = json.loads((job / 'request.json').read_text())
            authorization = Path(request['memory_authorization'])
            binding = admin.job_binding(job, request, 'recover')
            config, scope = admin.validate(case.configuration, authorization, binding=binding,
                                           check_binding=True, purpose='recover')
            assert scope.writer == case.account
            assert not scope.read and not scope.write
            denied = []
            for label, changed_binding, purpose in [
                ('apply_action', admin.job_binding(job, request, 'apply'), 'recover'),
                ('restore_action', admin.job_binding(job, request, 'restore'), 'recover'),
                ('other_job', admin.job_binding(job.parent / 'other-job', request, 'recover'), 'recover'),
                ('other_request', admin.job_binding(job, {**request, 'candidate_commit':'other'}, 'recover'), 'recover'),
                ('mount_purpose', binding, 'mount')]:
                try:
                    admin.validate(case.configuration, authorization, binding=changed_binding, check_binding=True, purpose=purpose)
                except PermissionError:
                    denied.append(label)
                else:
                    raise AssertionError(f'Grant accepted {label}')
            payload = json.loads(authorization.read_text())['payload']
            row = {'case': name, 'status': response.status_code, 'response': response.json(),
                   'new_launch_count': len(launched) - before_count, 'launch_action': launched[-1][1],
                   'grant_count': len(case.grants()), 'purpose': payload['purpose'], 'writer': scope.writer,
                   'binding': binding, 'wrong_binding_or_purpose_denied': denied,
                   'read_categories': list(scope.read), 'write_categories': list(scope.write),
                   'job_mode': (job/'request.json').stat().st_mode & 0o777,
                   'grant_mode': authorization.stat().st_mode & 0o777,
                   'grant_omitted_from_response': 'memory_authorization' not in response.text,
                   'ownership_enabled': config.get('ownership_enabled', False)}
            results.append(row)
            print(json.dumps(row), flush=True)
            admin.revoke(case.configuration, authorization)
            (job/'request.json').write_bytes(initial_request)
            (job/'status.json').write_bytes(initial_status)
finally:
    (OUTPUT/'http-probe-results.json').write_text(json.dumps(results, indent=2) + '\n')
    if server is not None:
        server.should_exit = True
    if thread is not None:
        thread.join(timeout=10)
    case.doCleanups()

print(f'PASS: {len(results)} local HTTP scenarios', flush=True)
