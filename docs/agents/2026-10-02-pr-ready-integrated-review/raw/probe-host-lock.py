# ABOUTME: Reproduces an integrated review boundary with disposable local fixtures.
# ABOUTME: Retains exact request or scheduling results without launching deployed services.
import json
from unittest.mock import patch
from lifeos_hook_bridge.installation_lock import installation_lock
from test_memory_admin_dashboard import MemoryAdminDashboardTests
f=MemoryAdminDashboardTests();f.setUp()
try:
    f.login()
    f.api.HOST_PATCH_ROOT=f.fixture.profile/'state/host-patches'
    snapshot=f.api.HOST_PATCH_ROOT/'synthetic-applied'
    snapshot.mkdir(parents=True,mode=0o700)
    (snapshot/'manifest.json').write_text(json.dumps({'state':'applied'}))
    with installation_lock(f.fixture.profile), patch.object(f.api,'_launch_host_patch') as launch:
        response=f.post('/restore-hermes')
        print(json.dumps({'status':response.status_code,'body':response.json(),'launcher_called_while_lock_held':launch.called,'manifest_state':json.loads((snapshot/'manifest.json').read_text())['state']}))
finally:
    f.doCleanups()
