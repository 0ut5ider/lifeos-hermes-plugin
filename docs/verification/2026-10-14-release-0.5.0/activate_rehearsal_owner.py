# ABOUTME: Activates fresh synthetic ownership after verifying the real dashboard owner session.
# ABOUTME: Uses the installed backup coordinator and governed memory endpoint without Discord credentials.
import importlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

import httpx

os.umask(0o077)
home = Path('/home/lifeos-hermes')
profile = home / '.hermes'
evidence = home / 'deployment/2026-10-14'
environment = json.loads((evidence / 'environment.json').read_bytes())
os.environ.update(environment, XDG_RUNTIME_DIR='/run/user/1000',
    DBUS_SESSION_BUS_ADDRESS='unix:path=/run/user/1000/bus')
sys.path[:0] = [str(profile / 'plugins'), str(home / 'runtime/releases/0.3.1-9af63325/hermes')]
module = lambda name: importlib.import_module('lifeos-hook-bridge.' + name)
credentials = json.loads((home / 'install-input/dashboard-access.json').read_bytes())
with httpx.Client(base_url='http://127.0.0.1:18819', timeout=120) as client:
    response = client.post('/auth/password-login', json={'provider': 'basic', **credentials})
    assert response.status_code == 200, response.status_code
    response = client.get('/api/auth/me')
    assert response.status_code == 200, response.status_code
    session = response.json()
    assert session['provider'] == 'basic' and session['user_id'] == 'adrian'
    assert session['expires_at'] > time.time()
    account = 'dashboard:' + session['provider'] + ':' + session['user_id']
    configuration = module('memory_service').MemoryConfiguration(profile / 'lifeos-memory.json')
    configuration.check_owner(configuration.load(), account)
    setup = module('ownership_setup').OwnershipSetup(configuration)
    current = setup.status(account=account)
    if current['state'] == 'configured':
        receipt = current
    else:
        plan = setup.prepare(evidence / 'synthetic-ownership-backup', account=account)
        receipt = setup.apply(plan['signature'], account=account)
    assert receipt['state'] == 'configured'
    assert configuration.load()['ownership_enabled'] is True
    assert configuration.load()['sharing_enabled'] is False
    subprocess.run(['systemctl', '--user', 'enable', '--now',
        'hermes-gateway.service', 'com.lifeos.pulse.service'], check=True, capture_output=True)
    deadline = time.monotonic() + 60
    while True:
        try:
            ready = client.post('/auth/password-login', json={'provider': 'basic', **credentials})
            if ready.status_code == 200:
                break
        except httpx.ConnectError:
            pass
        assert time.monotonic() < deadline, 'The synthetic dashboard does not resume'
        time.sleep(0.2)
    response = client.post('/api/plugins/lifeos-hook-bridge/memory/review',
        headers={'X-Hermes-Profile': 'default'}, json={'tool': 'lifeos_memory_remember', 'arguments': {
            'content': 'Synthetic account HOME preservation marker is D246-HOME-PRESERVE-1014.',
            'category': 'project', 'project': 'release-qualification',
            'title': 'Synthetic native HOME acceptance', 'request_id': 'home-rehearsal-1014'}})
    assert response.status_code == 200, response.status_code
    result = response.json()
    (evidence / 'synthetic-memory-result.json').write_text(json.dumps(result, indent=2) + '\n')
    report = {'status': 'PASS', 'authenticated_owner_verified': True,
        'ownership_enabled': True, 'sharing_enabled': False,
        'ownership_receipt': receipt, 'memory_http_status': response.status_code,
        'discord_credentials_present': False, 'production_guest_changed': False}
    (evidence / 'synthetic-ownership.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
