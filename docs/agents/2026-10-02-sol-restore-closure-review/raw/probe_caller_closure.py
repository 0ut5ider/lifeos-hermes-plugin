# ABOUTME: Checks worker failure mapping through authenticated recovery admission.
# ABOUTME: Refuses authorization substitutes and avoids launching deployed services.
import contextlib
import io
import json
import sys
from pathlib import Path
from unittest.mock import patch
from test_memory_admin_dashboard import MemoryAdminDashboardTests
from lifeos_hook_bridge import update_worker

for state in ('stopped', 'swapped', 'restoring', 'rollback_failed', 'applied'):
    fixture = MemoryAdminDashboardTests()
    fixture.setUp()
    try:
        fixture.login()
        job = fixture.applied_job() if state == 'applied' else fixture.interrupted_job()
        manifest = json.loads((job / 'snapshot/manifest.json').read_text())
        manifest['state'] = state
        (job / 'snapshot/manifest.json').write_text(json.dumps(manifest))
        error = io.StringIO()
        with patch.object(sys, 'argv', ['worker', str(job), '--action', 'restore']), \
             patch.object(update_worker, 'run_update_job', side_effect=RuntimeError('Synthetic restore failure')), \
             contextlib.redirect_stderr(error):
            assert update_worker._main() == 1
        assert 'Synthetic restore failure' in error.getvalue()
        worker_status = json.loads((job / 'status.json').read_text())
        assert worker_status['state'] == ('applied' if state == 'applied' else 'interrupted')
        before_request = (job / 'request.json').read_bytes()
        before_status = (job / 'status.json').read_bytes()
        path = fixture.prefix + ('/update/restore' if state == 'applied' else '/update/recover')
        rejected = []
        if state == 'applied':
            with patch.object(fixture.api, '_launch_lifeos_update', side_effect=AssertionError('Admission must run first')):
                rejected = [fixture.client.post(path, headers={'Origin': 'https://other.invalid'}).status_code,
                            fixture.client.post(path + '?job=other').status_code,
                            fixture.client.post(path, json={'account': fixture.account}).status_code]
            assert rejected == [403, 400, 400], rejected
        assert (job / 'request.json').read_bytes() == before_request
        assert (job / 'status.json').read_bytes() == before_status
        assert fixture.grants() == []
        with patch.object(fixture.api, '_launch_lifeos_update') as launch:
            response = fixture.client.post(path)
        assert response.status_code == 200, response.text
        action = 'restore' if state == 'applied' else 'recover'
        launch.assert_called_once_with(job, action)
        request = json.loads((job / 'request.json').read_text())
        authorization = Path(request['memory_authorization'])
        fixture.addCleanup(fixture.fixture.fixture.admin().revoke, fixture.configuration, authorization)
        _, scope = fixture.fixture.fixture.admin().validate(fixture.configuration, authorization,
            binding=fixture.fixture.fixture.admin().job_binding(job, request, action), check_binding=True,
            purpose='mount' if action == 'restore' else 'recover')
        try:
            fixture.fixture.fixture.admin().validate(fixture.configuration, authorization,
                binding=fixture.fixture.fixture.admin().job_binding(job, request, 'apply'), check_binding=True)
        except PermissionError:
            pass
        else:
            raise AssertionError('Action substitution was accepted')
        print(json.dumps({'case': 'worker_' + state, 'worker_status': worker_status, 'worker_stderr': error.getvalue(),
            'refused_overrides': rejected, 'authenticated_http': response.status_code, 'action': action,
            'scope_categories': list(scope.read), 'wrong_action_refused': True}, sort_keys=True))
    finally:
        fixture.doCleanups()
