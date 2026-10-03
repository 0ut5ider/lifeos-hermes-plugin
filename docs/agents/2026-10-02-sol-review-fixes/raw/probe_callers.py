# ABOUTME: Checks local update status handling after a restore worker failure.
# ABOUTME: Uses real authenticated local routes without services or remote calls.
import contextlib
import io
import json
import sys
from unittest.mock import patch
from test_memory_admin_dashboard import MemoryAdminDashboardTests
from lifeos_hook_bridge import update_worker
fixture = MemoryAdminDashboardTests()
fixture.setUp()
try:
    fixture.login()
    job = fixture.applied_job()
    manifest_path = job / 'snapshot/manifest.json'
    manifest = json.loads(manifest_path.read_text())
    manifest['state'] = 'restoring'
    manifest_path.write_text(json.dumps(manifest))
    stderr = io.StringIO()
    with patch.object(sys, 'argv', ['update_worker.py', str(job), '--action', 'restore']), \
         patch.object(update_worker, 'run_update_job', side_effect=RuntimeError('Synthetic profile refusal after program swap')), \
         contextlib.redirect_stderr(stderr):
        worker_exit = update_worker._main()
    status = fixture.api.get_lifeos_update_status()
    response = fixture.post('/update/recover')
    print(json.dumps({'worker_exit':worker_exit, 'worker_stderr':stderr.getvalue(),
                      'worker_status':json.loads((job/'status.json').read_text()),
                      'get_status':status, 'recover_status':response.status_code, 'recover_body':response.json()},sort_keys=True))
    assert worker_exit == 1 and status['state'] == 'failed'
    assert response.status_code == 409
finally:
    fixture.doCleanups()
