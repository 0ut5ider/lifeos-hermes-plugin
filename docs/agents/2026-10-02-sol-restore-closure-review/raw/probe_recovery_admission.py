# ABOUTME: Records recovery admission for cross-origin and parameterized requests.
# ABOUTME: Uses authenticated local routes and captures launch intent without services.
import json
from pathlib import Path
from unittest.mock import patch
from test_memory_admin_dashboard import MemoryAdminDashboardTests
for case in ('origin', 'query', 'body'):
    fixture = MemoryAdminDashboardTests()
    fixture.setUp()
    try:
        fixture.login()
        job = fixture.interrupted_job()
        before = (job / 'status.json').read_bytes()
        path = fixture.prefix + '/update/recover'
        options = {'headers': {'Origin': 'https://other.invalid'}} if case == 'origin' else {'json': {'account': 'fabricated', 'job': 'other'}} if case == 'body' else {}
        if case == 'query':
            path += '?job=other'
        with patch.object(fixture.api, '_launch_lifeos_update') as launch:
            response = fixture.client.post(path, **options)
        request = json.loads((job / 'request.json').read_text())
        authorization = Path(request['memory_authorization'])
        fixture.addCleanup(fixture.fixture.fixture.admin().revoke, fixture.configuration, authorization)
        _, scope = fixture.fixture.fixture.admin().validate(fixture.configuration, authorization,
            binding=fixture.fixture.fixture.admin().job_binding(job, request, 'recover'), check_binding=True, purpose='recover')
        print(json.dumps({'case': case, 'http': response.status_code, 'body': response.json(),
            'launch_calls': launch.call_count, 'job_status_changed': before != (job / 'status.json').read_bytes(),
            'authorization_issued': authorization.exists(), 'authorized_account': scope.writer}, sort_keys=True))
        assert response.status_code == 200 and launch.call_count == 1
        assert scope.writer == fixture.account
    finally:
        fixture.doCleanups()
