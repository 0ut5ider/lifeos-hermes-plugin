# ABOUTME: Checks corrected recovery request scheduling over real loopback HTTP.
# ABOUTME: Captures launch with a bounded local subprocess and measures unrelated route response delay.
import json
from pathlib import Path
import socket
import subprocess
import sys
import threading
import time
import types
from unittest.mock import patch

from fastapi import FastAPI
import httpx
import uvicorn
from hermes_cli.dashboard_auth.middleware import gated_auth_middleware
from hermes_cli.dashboard_auth.routes import router as auth_router
from test_memory_admin_dashboard import MemoryAdminDashboardTests

OUTPUT = Path(__file__).parent
rows = []
commits = ['working']
for commit in commits:
    case = MemoryAdminDashboardTests()
    case.setUp()
    server = None
    thread = None
    try:
        source = Path('lifeos_hook_bridge/dashboard/plugin_api.py').read_text()
        (OUTPUT / ('scheduling-source-' + commit[:7] + '.py')).write_text(source)
        module = types.ModuleType('recovery_scheduling_' + commit[:7])
        module.__file__ = str(Path('lifeos_hook_bridge/dashboard/plugin_api.py').absolute())
        exec(compile(source, module.__file__, 'exec'), module.__dict__)
        for name in ['INSTALLED_ROOT', 'HERMES_HOME', 'BASELINE_PATH', 'INSTALL_CANDIDATE', 'LIFEOS_UPDATE_ROOT', 'HOST_SOURCE']:
            setattr(module, name, getattr(case.api, name))
        job = case.interrupted_job()
        app = FastAPI()
        app.state.auth_required = True
        app.middleware('http')(gated_auth_middleware)
        app.include_router(auth_router)
        app.include_router(module.router, prefix='/api/plugins/lifeos-hook-bridge')

        @app.get('/auth/login/probe-ping')
        async def ping():
            return {'ok': True}

        sock = socket.socket()
        sock.bind(('127.0.0.1', 0))
        origin = f'http://127.0.0.1:{sock.getsockname()[1]}'
        server = uvicorn.Server(uvicorn.Config(app, log_level='warning', access_log=False))
        thread = threading.Thread(target=server.run, kwargs={'sockets':[sock]}, daemon=True)
        thread.start()
        deadline = time.monotonic() + 10
        while not server.started:
            if time.monotonic() > deadline:
                raise RuntimeError('Loopback server failed to start')
            time.sleep(0.01)
        entered = threading.Event()
        timing = {}
        response_box = {}

        def launch(_job, action):
            assert _job == job and action == 'recover'
            timing['launch_started'] = time.monotonic()
            entered.set()
            subprocess.run([sys.executable, '-c', 'import time; time.sleep(0.8)'], check=True)
            timing['launch_finished'] = time.monotonic()

        with patch.object(module, '_launch_lifeos_update', side_effect=launch), \
                httpx.Client(base_url=origin, trust_env=False, timeout=10) as owner, \
                httpx.Client(base_url=origin, trust_env=False, timeout=10) as observer:
            response = owner.post('/auth/password-login', json={'provider':'basic', 'username':'synthetic-owner',
                                                               'password':'synthetic-password'})
            assert response.status_code == 200, response.text

            def recover():
                response_box['response'] = owner.post(case.prefix + '/update/recover', headers={'Origin':origin})

            caller = threading.Thread(target=recover)
            caller.start()
            assert entered.wait(timeout=10)
            started = time.monotonic()
            pong = observer.get('/auth/login/probe-ping')
            finished = time.monotonic()
            caller.join(timeout=10)
            assert pong.status_code == 200 and response_box['response'].status_code == 200
            row = {'commit':commit, 'recovery_status':response_box['response'].status_code,
                   'ping_status':pong.status_code, 'ping_seconds': finished-started,
                   'capture_launch_seconds':timing['launch_finished']-timing['launch_started'],
                   'ping_completed_during_launch':finished < timing['launch_finished'],
                   'capture':'local Python subprocess sleep 0.8 seconds; no systemd or remote service'}
            rows.append(row)
            print(json.dumps(row), flush=True)
    finally:
        if server is not None:
            server.should_exit = True
        if thread is not None:
            thread.join(timeout=10)
        case.doCleanups()

(OUTPUT/'scheduling-after-results.json').write_text(json.dumps(rows, indent=2) + '\n')
assert rows[0]['ping_completed_during_launch'] is True
print('PASS: other requests complete while the recovery launch waits', flush=True)
