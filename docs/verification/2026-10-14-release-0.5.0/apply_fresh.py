# ABOUTME: Applies a prepared first installation through the authenticated release dashboard.
# ABOUTME: Verifies selected programs, preserved model settings, and inactive optional writers.
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

import httpx
from ruamel.yaml import YAML

os.umask(0o077)
home = Path('/home/lifeos-hermes')
profile = home / '.hermes'
stage = home / 'releases/qualification-0.5.0'
os.environ.update(HOME=str(home), HERMES_HOME=str(profile), XDG_RUNTIME_DIR='/run/user/1000',
    DBUS_SESSION_BUS_ADDRESS='unix:path=/run/user/1000/bus', PATH=str(home / '.local/bin') + ':/usr/bin:/bin')
build = json.loads((stage / 'stable-build.json').read_bytes())
prepared = json.loads((stage / 'fresh-preparation.json').read_bytes())
assert prepared['status'] == 'PASS' and prepared['candidate'] == build['head']
identifier = prepared['preparation']['identifier']
job = profile / '.lifeos-releases' / identifier
request = json.loads((job / 'request.json').read_bytes())
credentials = json.loads((home / 'install-input/dashboard-access.json').read_bytes())
report = {'status': 'FAIL', 'operation': identifier, 'test_fixture_only': True,
    'production_guest_changed': False, 'commit': build['head'], 'package_sha256': build['archive_sha256']}
code = 1
try:
    with httpx.Client(base_url='http://127.0.0.1:18819', timeout=180) as client:
        deadline = time.monotonic() + 90
        while True:
            try:
                login = client.post('/auth/password-login', json={'provider': 'basic', **credentials})
                if login.status_code == 200: break
            except httpx.ConnectError:
                pass
            assert time.monotonic() < deadline, 'The stock dashboard does not become ready'
            time.sleep(0.2)
        session = client.get('/api/auth/me').json()
        assert session['provider'] == 'basic' and session['user_id'] == 'qualification-owner'
        assert session['expires_at'] > time.time()
        route = '/api/plugins/lifeos-release-manager/operations/' + identifier
        reviewed = client.post(route + '/review', headers={'X-Hermes-Profile': 'default'})
        assert reviewed.status_code == 200
        value = reviewed.json()
        assert value['fresh'] and value['native_mount_required']
        assert value['commit'] == build['head'] and value['package_sha256'] == build['archive_sha256']
        accepted = client.post(route + '/apply', headers={'X-Hermes-Profile': 'default'})
        assert accepted.status_code == 200
    deadline = time.monotonic() + 900
    while True:
        state = json.loads((job / 'status.json').read_bytes())['state']
        if state == 'applied': break
        assert state not in {'failed', 'recovery_required', 'rolled_back'}, 'The installation requires measured failure investigation'
        assert time.monotonic() < deadline
        time.sleep(1)
    active = json.loads(subprocess.check_output([str(home / '.local/bin/hermes'), 'lifeos-version'], timeout=90))['active']
    assert active['version'] == '0.5.0' and active['commit'] == build['head']
    assert active['package_sha256'] == build['archive_sha256'] and active['verification'] == 'verified'
    config = YAML(typ='safe').load((profile / 'config.yaml').read_bytes())
    settings = config['plugins']['entries']['lifeos-hook-bridge']['settings']
    selection = {'model': config['model'], 'tiers': {key: value for key, value in settings.items()
        if key.startswith(('haiku', 'sonnet', 'opus', 'fable', 'pinned'))}}
    assert hashlib.sha256(json.dumps(selection, sort_keys=True).encode()).hexdigest() == prepared['model_selection_sha256']
    units = {}
    for name in ('hermes-dashboard.service', 'hermes-gateway.service', 'com.lifeos.pulse.service'):
        value = subprocess.check_output(['systemctl', '--user', 'show', name, '--property=ActiveState,SubState'], text=True)
        units[name] = dict(line.split('=', 1) for line in value.splitlines())
    assert units['hermes-dashboard.service']['ActiveState'] == 'active'
    assert units['hermes-gateway.service']['ActiveState'] == units['com.lifeos.pulse.service']['ActiveState'] == 'inactive'
    report.update(status='PASS', native_mount_required=True, authenticated_owner_verified=True,
        selected_model_and_tiers_preserved=True, active=active, services=units,
        personal_data_imported_or_reset=False, browser_interaction=False)
    code = 0
finally:
    (stage / 'fresh-apply.json').write_text(json.dumps(report, indent=2) + '\n')
    (stage / 'fresh-apply.done').write_text(str(code) + '\n')
