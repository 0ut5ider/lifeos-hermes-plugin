# ABOUTME: Runs a fixed synthetic release action through the authenticated owner dashboard.
# ABOUTME: Verifies the exact candidate identity and preserves private configuration hashes.
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

import httpx


parser = argparse.ArgumentParser()
parser.add_argument('action', choices=('apply', 'restore', 'recover'))
parser.add_argument('preparation', choices=('daily-layout', 'daily-layout-interruption', 'final-apply'))
parser.add_argument('phase', choices=('applied', 'restored', 'recovered', 'final-applied'))
args = parser.parse_args()
home = Path('/home/lifeos-hermes')
profile = home / '.hermes'
folder = home / 'releases/qualification-0.5.0'
assert os.getuid() == profile.stat().st_uid
os.umask(0o077)
environment = json.loads((home / 'deployment/2026-10-14/environment.json').read_bytes())
os.environ.update(environment, XDG_RUNTIME_DIR='/run/user/' + str(os.getuid()),
    DBUS_SESSION_BUS_ADDRESS='unix:path=/run/user/' + str(os.getuid()) + '/bus')
build = json.loads((folder / 'stable-build.json').read_bytes())
prepared = json.loads((folder / (args.preparation + '-preparation.json')).read_bytes())
assert prepared['status'] == 'PASS' and prepared['candidate'] == build['head']
identifier = prepared['preparation']['identifier']
assert len(identifier) == 32 and all(character in '0123456789abcdef' for character in identifier)
job = profile / '.lifeos-releases' / identifier
request = json.loads((job / 'request.json').read_bytes())
assert request['version'] == '0.5.0' and request['commit'] == build['head']
assert request['package_sha256'] == build['archive_sha256']
assert request['account_home'] == str(home) and request['profile'] == str(profile)
assert Path(request['installed']).parent == Path(environment['HOME'])
baseline_path = folder / 'private-preservation-baseline.json'
hashes = lambda: {name: hashlib.sha256((profile / name).read_bytes()).hexdigest()
    for name in ('.env', 'lifeos-memory.json')}
if baseline_path.exists():
    baseline = json.loads(baseline_path.read_bytes())
else:
    assert args.action == 'apply' and args.phase == 'applied'
    baseline = hashes()
    baseline_path.write_text(json.dumps(baseline) + '\n')
assert hashes() == baseline
report = {'status': 'FAIL', 'action': args.action, 'operation': identifier,
    'phase': args.phase, 'program_commit': build['head'], 'archive_sha256': build['archive_sha256'],
    'test_fixture_only': True, 'production_guest_changed': False}
code = 1
try:
    credentials = json.loads((home / 'install-input/dashboard-access.json').read_bytes())
    with httpx.Client(base_url='http://127.0.0.1:18819', timeout=120) as client:
        login = client.post('/auth/password-login', json={'provider': 'basic', **credentials})
        assert login.status_code == 200
        session = client.get('/api/auth/me').json()
        assert session['provider'] == 'basic' and session['user_id'] == 'adrian'
        assert session['expires_at'] > time.time()
        route = '/api/plugins/lifeos-release-manager/operations/' + identifier
        if args.action == 'apply':
            reviewed = client.post(route + '/review', headers={'X-Hermes-Profile': 'default'})
            assert reviewed.status_code == 200, 'The authenticated release review refuses'
            value = reviewed.json()
            assert value['commit'] == build['head'] and value['package_sha256'] == build['archive_sha256']
            report['native_mount_required'] = value['native_mount_required']
        accepted = client.post(route + '/' + args.action, headers={'X-Hermes-Profile': 'default'})
        report['http_status'] = accepted.status_code
        assert accepted.status_code == 200, 'The authenticated release action refuses'
    deadline = time.monotonic() + 900
    expected = 'applied' if args.action == 'apply' else 'rolled_back'
    while True:
        state = json.loads((job / 'status.json').read_bytes())['state']
        if state == expected:
            break
        assert state not in {'failed', 'recovery_required'}, 'The action requires measured failure investigation'
        assert time.monotonic() < deadline, 'The synthetic release action does not finish'
        time.sleep(1)
    assert hashes() == baseline, 'The release changes credential or memory configuration bytes'
    verify_phase = 'applied' if args.phase == 'applied' else 'restored' if args.phase in {'restored', 'recovered'} else 'final-applied'
    version = '0.5.0' if args.action == 'apply' else '0.3.1'
    python = home / '.hermes/installs/995dd15ff6e15ed0/environments/65f4231f26e94a2d989e89eb96b98808/venv/bin/python'
    with (folder / (args.phase + '-verification.stdout')).open('w') as stdout, (folder / (args.phase + '-verification.stderr')).open('w') as stderr:
        result = subprocess.run([str(python), '-B', str(folder / 'verify_rehearsal.py'), version, verify_phase],
            stdout=stdout, stderr=stderr, timeout=180)
    assert result.returncode == 0, 'The selected identity or synthetic memory verification fails'
    report.update(status='PASS', state=state, authenticated_owner_verified=True,
        credential_bytes_preserved=True, memory_configuration_bytes_preserved=True)
    code = 0
finally:
    (folder / (args.phase + '-action.json')).write_text(json.dumps(report, indent=2) + '\n')
    (folder / (args.phase + '-action.done')).write_text(str(code) + '\n')
