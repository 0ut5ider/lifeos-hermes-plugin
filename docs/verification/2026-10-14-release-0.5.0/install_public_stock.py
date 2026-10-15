# ABOUTME: Starts an unpatched stock Hermes dashboard in a fresh synthetic guest.
# ABOUTME: Records a manager-free baseline before the native plugin installation test.
import hashlib
import io
import json
import os
from pathlib import Path
import secrets
import shlex
import subprocess
import sys
import tarfile

from ruamel.yaml import YAML


os.umask(0o077)
home = Path('/home/lifeos-hermes')
profile = home / '.hermes'
runtime = home / 'runtime/stock-hermes'
stage = home / 'releases/qualification-0.5.0'
sys.path.insert(0, str(runtime))
from plugins.dashboard_auth.basic import hash_password

assert not (profile / 'config.yaml').exists()
assert not (profile / 'plugins').exists()
assert not (home / '.claude').exists()
python = home / 'stock-venv/bin/python'
assert python.resolve() == home / '.hermes/tools/python-3.14.7+20260901-linux-x64/bin/python3.14'
dashboard = home / 'releases/hermes-dashboard.tgz'
build = json.loads((stage / 'stable-build.json').read_bytes())
fixture = json.loads((stage / 'STOCK-BOOTSTRAP.json').read_bytes())
assert fixture['test_fixture_only'] and not fixture['production_qualified']
assert fixture['program_commit'] == build['head']
assert hashlib.sha256(dashboard.read_bytes()).hexdigest() == fixture['hermes_dashboard_sha256']
with tarfile.open(dashboard) as archive:
    archive.extractall(runtime, filter='data')
password = secrets.token_urlsafe(32)
credentials = home / 'install-input/dashboard-access.json'
credentials.write_text(json.dumps({'username': 'qualification-owner', 'password': password}) + '\n')
credentials.chmod(0o600)
model = {'default': 'flashnext-w4a16-fp8ple', 'provider': 'custom',
    'base_url': 'http://127.0.0.1:9/v1', 'api_mode': 'chat_completions'}
tiers = {**{name + '_model': model['default'] for name in ('haiku', 'sonnet', 'opus', 'fable')},
    'haiku_effort': 'low', 'sonnet_effort': 'medium', 'opus_effort': 'xhigh', 'fable_effort': 'xhigh'}
config = {'model': model, 'agent': {'max_turns': 10},
    'memory': {'memory_enabled': False, 'user_profile_enabled': False},
    'plugins': {'enabled': [], 'entries': {'lifeos-hook-bridge': {'settings': tiers}}},
    'dashboard': {'public_url': 'http://192.168.8.244:18819',
        'basic_auth': {'username': 'qualification-owner', 'password_hash': hash_password(password)}}}
stream = io.StringIO()
YAML().dump(config, stream)
(profile / 'config.yaml').write_text(stream.getvalue())
(profile / 'config.yaml').chmod(0o600)
(profile / '.env').write_text('CUSTOM_API_KEY=' + secrets.token_urlsafe(32) + '\n')
(profile / '.env').chmod(0o600)
launcher = home / '.local/bin/hermes'
launcher.write_text('#!/bin/sh\nexport PYTHONPATH=' + shlex.quote(str(runtime)) +
    '\nexec ' + shlex.quote(str(python)) + ' -B -m hermes_cli.main "$@"\n')
launcher.chmod(0o700)
unit = home / '.config/systemd/user/hermes-dashboard.service'
unit.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
environment = {'HOME': str(home), 'HERMES_HOME': str(profile), 'PYTHONPATH': str(runtime),
    'PATH': str(home / '.local/bin') + ':/usr/bin:/bin', 'TZ': 'America/Toronto',
    'LANG': 'C.UTF-8', 'PYTHONDONTWRITEBYTECODE': '1', 'BUN_CONFIG_NO_AUTO_INSTALL': '1'}
lines = ['[Unit]', 'Description=Stock Hermes synthetic qualification dashboard', '[Service]',
    'Type=simple', 'UMask=0077', 'KillMode=control-group', 'TimeoutStopSec=45',
    'Restart=on-failure', 'WorkingDirectory=' + str(home),
    'ExecStart=' + str(launcher) + ' dashboard --isolated --skip-build --no-open --host 127.0.0.1 --port 18819']
lines.extend('Environment="' + key + '=' + value + '"' for key, value in environment.items())
lines.extend(['[Install]', 'WantedBy=default.target'])
unit.write_text('\n'.join(lines) + '\n')
unit.chmod(0o600)
os.environ.update(environment, XDG_RUNTIME_DIR='/run/user/' + str(os.getuid()),
    DBUS_SESSION_BUS_ADDRESS='unix:path=/run/user/' + str(os.getuid()) + '/bus')
subprocess.run(['systemctl', '--user', 'daemon-reload'], check=True, capture_output=True)
subprocess.run(['systemctl', '--user', 'enable', '--now', unit.name], check=True, capture_output=True)
selection = {'model': model, 'tiers': tiers}
report = {'status': 'STOCK_DASHBOARD_STARTED', 'guest': 113, 'address': '192.168.8.244',
    'hermes_commit': '71d34bad1045610252eda02ee79549436896e784', 'hermes_patches': 0,
    'release_manager_installed': False, 'lifeos_installed': False, 'production_guest_changed': False,
    'model_selection_sha256': hashlib.sha256(json.dumps(selection, sort_keys=True).encode()).hexdigest(),
    'stock_source_sha256': json.loads((stage / 'stock-source.json').read_bytes())['archive_sha256']}
(stage / 'stock-baseline.json').write_text(json.dumps(report, indent=2) + '\n')
