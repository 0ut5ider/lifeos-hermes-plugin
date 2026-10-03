# ABOUTME: Reproduces an integrated review boundary with disposable local fixtures.
# ABOUTME: Retains exact request or scheduling results without launching deployed services.
import json, shutil, subprocess, sys, threading, time
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
from test_memory_admin_dashboard import MemoryAdminDashboardTests
f=MemoryAdminDashboardTests(); f.setUp()
try:
    f.login()
    job=f.applied_job()
    tx=f.api.install_module.memory_module('update_transaction')
    if not (job/'snapshot/live-prior').exists():
        shutil.copytree(f.fixture.root,job/'snapshot/live-prior',symlinks=True)
    manifest=json.loads((job/'snapshot/manifest.json').read_text())
    manifest['user_data_links']=tx._external_user_data(f.fixture.root,excluded=(job/'snapshot',))
    manifest['user_data']=tx._memory_digest(f.fixture.root,manifest['user_data_links'])
    (job/'snapshot/manifest.json').write_text(json.dumps(manifest))
    entered=threading.Event()
    @f.app.get('/auth/login/restore-scheduling-probe')
    async def ready():
        return {'ok':True}
    def launch(*args):
        entered.set()
        subprocess.run([sys.executable,'-c','import time; time.sleep(0.8)'],check=True)
    with patch.object(f.api,'_launch_lifeos_update',side_effect=launch), ThreadPoolExecutor(max_workers=1) as pool:
        pending=pool.submit(f.post,'/update/restore')
        assert entered.wait(5),'launch was not reached'
        start=time.monotonic()
        response=f.client.get('/auth/login/restore-scheduling-probe')
        elapsed=time.monotonic()-start
        result=pending.result(5)
        print(json.dumps({'restore_status':result.status_code,'probe_status':response.status_code,'concurrent_request_seconds':elapsed,'launch_subprocess_sleep_seconds':0.8}))
finally:
    f.doCleanups()
