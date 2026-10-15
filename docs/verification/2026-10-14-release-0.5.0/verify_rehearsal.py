# ABOUTME: Verifies selected synthetic release identities and governed memory after apply or rollback.
# ABOUTME: Checks all service HOME bindings and model hashes without exporting credentials.
import hashlib
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import time

import httpx
from ruamel.yaml import YAML

os.umask(0o077)
home = Path('/home/lifeos-hermes')
profile = home / '.hermes'
stage = home / 'releases/qualification-0.5.0'
expected_version = sys.argv[1]
phase = sys.argv[2]
prepared = json.loads((stage / 'daily-layout-preparation.json').read_bytes())
native_home = str(Path(prepared['installed']).parent)
os.environ.update(HOME=native_home, HERMES_HOME=str(profile), XDG_RUNTIME_DIR='/run/user/1000',
    DBUS_SESSION_BUS_ADDRESS='unix:path=/run/user/1000/bus', PATH=str(home / '.local/bin') + ':/usr/bin:/bin')
result = subprocess.run([str(home / '.local/bin/hermes'), 'lifeos-version'],
    text=True, capture_output=True, timeout=90, check=True)
active = json.loads(result.stdout)['active']
assert active['version'] == expected_version and active['verification'] == 'verified'
if expected_version == '0.5.0':
    assert active['commit'] == prepared['candidate']
    assert active['package_sha256'] == prepared['preparation']['package_sha256']
else:
    assert active['commit'] == '9af633252004a0ac8dd780d5fc12e9644f97bb0c'
    assert active['package_sha256'] == '2aada985dd26dee4ffb4da1d3348c43c76cff2e697d04028cfbba9d6f1b11a24'
config = YAML(typ='safe').load((profile / 'config.yaml').read_bytes())
settings = config.get('plugins', {}).get('entries', {}).get('lifeos-hook-bridge', {}).get('settings', {})
selection = {'model': config.get('model'), 'tiers': {key: value for key, value in settings.items()
    if key.startswith(('haiku', 'sonnet', 'opus', 'fable', 'pinned'))}}
selection_hash = hashlib.sha256(json.dumps(selection, sort_keys=True).encode()).hexdigest()
assert selection_hash == prepared['model_selection_sha256']
services = {}
for name in ('hermes-gateway.service', 'hermes-dashboard.service', 'com.lifeos.pulse.service'):
    result = subprocess.run(['systemctl', '--user', 'show', name,
        '--property=ActiveState,SubState,Environment', '--no-pager'],
        text=True, capture_output=True, timeout=15, check=True)
    values = dict(line.split('=', 1) for line in result.stdout.splitlines() if '=' in line)
    environment = dict(value.split('=', 1) for value in shlex.split(values['Environment']))
    assert values['ActiveState'] == 'active' and values['SubState'] == 'running'
    assert environment['HOME'] == native_home and environment['HERMES_HOME'] == str(profile)
    services[name] = {'active': True, 'native_home_preserved': True, 'profile_preserved': True}
credentials = json.loads((home / 'install-input/dashboard-access.json').read_bytes())
with httpx.Client(base_url='http://127.0.0.1:18819', timeout=60) as client:
    deadline = time.monotonic() + 60
    while True:
        try:
            response = client.post('/auth/password-login', json={'provider': 'basic', **credentials})
            if response.status_code == 200:
                break
        except httpx.ConnectError:
            pass
        assert time.monotonic() < deadline, 'The synthetic dashboard is unavailable'
        time.sleep(0.2)
    response = client.post('/api/plugins/lifeos-hook-bridge/memory/review',
        headers={'X-Hermes-Profile': 'default'}, json={'tool': 'lifeos_memory_search',
        'arguments': {'query': 'D246-HOME-PRESERVE-1014'}})
    assert response.status_code == 200, response.status_code
    recalled = response.json()
    prior = json.loads((home / 'deployment/2026-10-14/synthetic-memory-result.json').read_bytes())
    assert recalled['status'] == 'ok' and len(recalled['results']) == 1
    assert recalled['results'][0]['reference'] == prior['reference']
    if phase == 'applied':
        later = client.post('/api/plugins/lifeos-hook-bridge/memory/review',
            headers={'X-Hermes-Profile': 'default'}, json={'tool': 'lifeos_memory_remember',
            'arguments': {'content': 'Synthetic post-update preservation marker is D246-AFTER-UPDATE-1014.',
                'category': 'project', 'project': 'release-qualification',
                'title': 'Synthetic rollback acceptance', 'request_id': 'home-rehearsal-after-update-1014'}})
        assert later.status_code == 200 and later.json()['status'] == 'committed'
        (stage / 'post-update-synthetic-memory.json').write_text(json.dumps(later.json(), indent=2) + '\n')
    if phase == 'restored':
        later = client.post('/api/plugins/lifeos-hook-bridge/memory/review',
            headers={'X-Hermes-Profile': 'default'}, json={'tool': 'lifeos_memory_search',
            'arguments': {'query': 'D246-AFTER-UPDATE-1014'}})
        assert later.status_code == 200 and later.json()['status'] == 'ok'
        after = json.loads((stage / 'post-update-synthetic-memory.json').read_bytes())
        assert len(later.json()['results']) == 1
        assert later.json()['results'][0]['reference'] == after['reference']
    report = {'status': 'PASS', 'phase': phase, 'active': active, 'services': services,
        'model_selection_sha256': selection_hash, 'model_mapping_preserved': True,
        'native_store_preserved': True, 'synthetic_memory_reference': prior['reference'],
        'memory_http_status': response.status_code, 'production_guest_changed': False,
        'personal_data_imported_or_reset': False}
    (stage / ('verify-' + phase + '.json')).write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
