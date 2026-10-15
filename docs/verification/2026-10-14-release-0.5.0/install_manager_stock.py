# ABOUTME: Installs the exact manager through the authenticated stock dashboard plugin route.
# ABOUTME: Verifies native installation bytes before complete LifeOS preparation on the fresh guest.
import hashlib
import json
import os
from pathlib import Path
import time

import httpx

os.umask(0o077)
home = Path('/home/lifeos-hermes')
profile = home / '.hermes'
stage = home / 'releases/qualification-0.5.0'
build = json.loads((stage / 'stable-build.json').read_bytes())
assert json.loads((stage / 'stock-baseline.json').read_bytes())['release_manager_installed'] is False
assert not (profile / 'plugins/lifeos-release-manager').exists()
credentials = json.loads((home / 'install-input/dashboard-access.json').read_bytes())
report = {'status': 'FAIL', 'test_fixture_only': True, 'production_guest_changed': False}
code = 1
try:
    with httpx.Client(base_url='http://127.0.0.1:18819', timeout=180) as client:
        login = client.post('/auth/password-login', json={'provider': 'basic', **credentials})
        assert login.status_code == 200
        session = client.get('/api/auth/me').json()
        assert session['provider'] == 'basic' and session['user_id'] == 'qualification-owner'
        assert session['expires_at'] > time.time()
        response = client.post('/api/dashboard/agent-plugins/install', json={
            'identifier': 'https://github.com/0ut5ider/lifeos-hermes-plugin#optional/lifeos_release_manager',
            'ref': build['head'], 'force': False, 'enable': True})
        assert response.status_code == 200, 'The stock dashboard plugin installation refuses'
        result = response.json()
        assert result.get('success') is not False
    import tarfile
    archive = stage / Path(build['archive']).name
    with tarfile.open(archive) as stream:
        manifest = json.load(stream.extractfile('DAILY-CANDIDATE.json'))
    expected = manifest['manager_files']
    actual = {str(path.relative_to(profile / 'plugins/lifeos-release-manager')):
        hashlib.sha256(path.read_bytes()).hexdigest()
        for path in (profile / 'plugins/lifeos-release-manager').rglob('*')
        if path.is_file() and '__pycache__' not in path.parts}
    assert actual == expected
    assert not (home / '.claude').exists()
    report.update(status='PASS', endpoint='/api/dashboard/agent-plugins/install', http_status=200,
        commit=build['head'], manager_file_count=len(actual), authenticated_owner_verified=True,
        lifeos_installed=False, browser_interaction=False)
    code = 0
finally:
    (stage / 'stock-manager-install.json').write_text(json.dumps(report, indent=2) + '\n')
    (stage / 'stock-manager-install.done').write_text(str(code) + '\n')
