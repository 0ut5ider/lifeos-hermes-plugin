# ABOUTME: Reproduces an integrated review boundary with disposable local fixtures.
# ABOUTME: Retains exact request or scheduling results without launching deployed services.
import json, threading
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
from test_memory_admin_dashboard import MemoryAdminDashboardTests
f=MemoryAdminDashboardTests(); f.setUp()
try:
    f.prepare_baseline()
    barrier=threading.Barrier(2)
    original=f.api.get_lifeos_update_status
    def concurrent_status():
        result=original()
        barrier.wait(timeout=5)
        return result
    with patch.object(f.api,'get_lifeos_update_status',side_effect=concurrent_status), patch.object(f.api,'_launch_lifeos_update') as launch, ThreadPoolExecutor(max_workers=2) as pool:
        responses=list(pool.map(lambda _:f.post('/update'),range(2)))
        print(json.dumps({'statuses':[r.status_code for r in responses],'responses':[r.json() for r in responses],'launcher_calls':launch.call_count,'jobs':len(list(f.api.LIFEOS_UPDATE_ROOT.glob('update-*'))),'grants':len(f.grants())}))
finally:
    f.doCleanups()
