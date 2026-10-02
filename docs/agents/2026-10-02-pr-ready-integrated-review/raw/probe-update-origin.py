# ABOUTME: Reproduces an integrated review boundary with disposable local fixtures.
# ABOUTME: Retains exact request or scheduling results without launching deployed services.
from unittest.mock import patch
import json
from test_memory_admin_dashboard import MemoryAdminDashboardTests
f=MemoryAdminDashboardTests(); f.setUp()
try:
    f.login()
    response=f.client.post(f.prefix+'/finalize',headers={'Origin':'http://testserver:8081'})
    print(json.dumps({'path':'/finalize','origin':'http://testserver:8081','status':response.status_code,'baseline_created':f.fixture.baseline.exists(),'grants':len(f.grants())}))
    with patch.object(f.api,'_launch_lifeos_update') as launch:
        response=f.client.post(f.prefix+'/update',headers={'Origin':'http://testserver:8081'})
        print(json.dumps({'path':'/update','origin':'http://testserver:8081','status':response.status_code,'body':response.json(),'launched':launch.called,'grants':len(f.grants())}))
finally:
    f.doCleanups()
