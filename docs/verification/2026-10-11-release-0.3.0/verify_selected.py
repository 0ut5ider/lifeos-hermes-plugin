# ABOUTME: Checks the selected release through actual services, source files, and private model routing.
# ABOUTME: Retains private responses and exports only verification counts and status.
import argparse
import hashlib
import http.cookiejar
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import time
import urllib.error
import urllib.request

parser = argparse.ArgumentParser()
parser.add_argument('package', type=Path)
parser.add_argument('--daily', action='store_true')
args = parser.parse_args()
os.umask(0o077)
home = Path('/home/lifeos-hermes')
profile = home / '.hermes'
package = args.package.resolve()
sys.path[:0] = [str(package), str(package / 'hermes')]
from lifeos_hook_bridge import release_version
manifest = json.loads((package / 'DAILY-CANDIDATE.json').read_text())
config = json.loads((profile / 'lifeos-memory.json').read_text())
root = Path(config['root'])
evidence = home / 'deployment' / ('release-' + manifest['version'] + '-' + manifest['head'][:8])
os.environ.update(HERMES_HOME=str(profile), PYTHONDONTWRITEBYTECODE='1',
    XDG_RUNTIME_DIR='/run/user/' + str(os.getuid()),
    DBUS_SESSION_BUS_ADDRESS='unix:path=/run/user/' + str(os.getuid()) + '/bus')
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
active = release_version.status(profile, profile / 'plugins/lifeos-hook-bridge')['active']
assert active['version'] == manifest['version'] and active['commit'] == manifest['head']
assert active['verification'] == 'verified'
selection = json.loads((evidence / 'selection.json').read_text())
assert active['package_sha256'] == selection['package_sha256']
unit = (home / '.config/systemd/user/hermes-gateway.service').read_text()
launcher = Path(shlex.split(next(line.split('=', 1)[1] for line in unit.splitlines()
    if line.startswith('ExecStart=')))[0])
runtime = home / 'runtime/releases' / (manifest['version'] + '-' + manifest['head'][:8]) / 'hermes'
native_count = hermes_count = 0
for source in (package / 'hermes').rglob('*'):
    relative = source.relative_to(package / 'hermes')
    if not source.is_file() or {'__pycache__', '.git'} & set(relative.parts):
        continue
    assert sha(source) == sha(runtime / relative), str(relative)
    hermes_count += 1
native = package / 'lifeos/LifeOS/install'
for source in native.rglob('*'):
    relative = source.relative_to(native)
    if (not source.is_file() or relative.parts[0] not in {'LIFEOS', 'hooks'}
            or {'USER', 'MEMORY', 'node_modules', '__pycache__'} & set(relative.parts)
            or str(relative) == 'LIFEOS/DOCUMENTATION/ARCHITECTURE_SUMMARY.md'):
        continue
    assert sha(source) == sha(root / relative), str(relative)
    native_count += 1
version = subprocess.run([str(launcher), 'lifeos-version'], capture_output=True, text=True, timeout=60)
assert version.returncode == 0 and not version.stderr
assert json.loads(version.stdout)['active'] == active
marker = ('D253' if args.daily else 'D252') + '-RELEASE-' + manifest['version'].replace('.', '') + '-PASS'
model = subprocess.run([str(launcher), 'chat', '--oneshot', '--quiet', '--max-turns', '2',
    '--run-budget', '240', '--query-file', '-'],
    input='Release verification. Do not call a tool. Reply exactly ' + marker + '.',
    capture_output=True, text=True, cwd=profile, timeout=300)
(evidence / 'model.stdout').write_text(model.stdout)
(evidence / 'model.stderr').write_text(model.stderr)
assert model.returncode == 0 and marker in model.stdout, 'The actual model turn fails'
services = {}
for name in ('hermes-gateway.service', 'hermes-dashboard.service', 'com.lifeos.pulse.service'):
    result = subprocess.check_output(['systemctl', '--user', 'show', name,
        '--property=ActiveState,NRestarts,MainPID'], text=True)
    properties = dict(line.split('=', 1) for line in result.splitlines())
    assert properties['ActiveState'] == 'active' and properties['NRestarts'] == '0', name
    services[name] = properties
dashboard_checks = None
audience_verified = None
if args.daily:
    from dotenv import dotenv_values
    from lifeos_hook_bridge.discord_audience import DiscordAPI, resolve_audience
    assert config['ownership_enabled'] and not config['sharing_enabled']
    metadata = {'HERMES_SESSION_PLATFORM': 'discord', 'HERMES_SESSION_CHAT_ID': '1558870196784205927',
        'HERMES_SESSION_CHAT_TYPE': 'group', 'HERMES_SESSION_SCOPE_ID': '1553540018302099486',
        'HERMES_SESSION_USER_ID': '708089927468056648'}
    api = DiscordAPI(dotenv_values(profile / '.env')['DISCORD_BOT_TOKEN'])
    assert resolve_audience(config, metadata, api=api) is not None
    audience_verified = True
    credentials = json.loads((home / 'install-input/dashboard-access.json').read_text())
    client = urllib.request.build_opener(urllib.request.ProxyHandler({}),
        urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
    anonymous = None
    try:
        with client.open('http://127.0.0.1:18819/api/plugins/lifeos-hook-bridge/memory', timeout=15):
            pass
    except urllib.error.HTTPError as error:
        anonymous = error.code
    assert anonymous == 401
    request = urllib.request.Request('http://127.0.0.1:18819/auth/password-login',
        data=json.dumps({'provider': 'basic', **credentials}).encode(),
        headers={'Content-Type': 'application/json'})
    with client.open(request, timeout=15) as response:
        assert response.status == 200
        response.read()
    for url in ('http://127.0.0.1:18819/api/plugins/lifeos-hook-bridge/memory',
                'http://127.0.0.1:18837/api/memory'):
        with client.open(url, timeout=30) as response:
            assert response.status == 200
            response.read()
    dashboard_checks = {'anonymous': 401, 'authenticated_dashboard': 200, 'authenticated_pulse': 200}
    operator = home / '.local/libexec/lifeos-morning-discord.py'
    assert sha(operator) == manifest['operators']['morning']['sha256']
report = {'status': 'PASS', 'active': active, 'native_program_files': native_count,
    'hermes_program_files': hermes_count, 'actual_model_marker': marker, 'services': services,
    'dashboard_checks': dashboard_checks, 'private_discord_audience_verified': audience_verified,
    'ownership_preserved': config['ownership_enabled'], 'sharing_preserved': config['sharing_enabled']}
(evidence / 'installed-verification.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
