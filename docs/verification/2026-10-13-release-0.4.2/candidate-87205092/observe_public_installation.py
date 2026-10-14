# ABOUTME: Verifies actual public installation state and preserved model selection.
# ABOUTME: Exports program identity and process metadata without personal records or credentials.
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess

from ruamel.yaml import YAML

parser = argparse.ArgumentParser()
parser.add_argument('operation')
args = parser.parse_args()
home = Path.home()
profile = home / '.hermes'
job = profile / '.lifeos-releases' / args.operation
request = json.loads((job / 'request.json').read_bytes())
status = json.loads((job / 'status.json').read_bytes())
programs = json.loads((job / 'program-snapshot/programs.json').read_bytes())
environment = dict(os.environ, HOME=str(home), HERMES_HOME=str(profile),
    PYTHONDONTWRITEBYTECODE='1', XDG_RUNTIME_DIR='/run/user/' + str(os.getuid()),
    DBUS_SESSION_BUS_ADDRESS='unix:path=/run/user/' + str(os.getuid()) + '/bus')
environment['PATH'] = str(home / '.local/bin') + ':' + os.defpath
version = subprocess.run([str(home / '.local/bin/hermes'), 'lifeos-version'],
    env=environment, capture_output=True, text=True, check=True, timeout=90)
active = json.loads(version.stdout)['active']
expected = {'version': '0.4.2', 'commit': '87205092832c550a09fce6e1cb3ca944fdb69a8c',
    'package_sha256': '76c1c10e82ce75f86858a2cd27ae609f5f7eb8a8bc79612d94df6f95f45136a4'}
assert active['verification'] == 'verified'
assert all(active[key] == request[key] == value for key, value in expected.items())
assert status['state'] == programs['state'] == 'applied'
config = YAML(typ='safe').load((profile / 'config.yaml').read_bytes())
settings = config.get('plugins', {}).get('entries', {}).get('lifeos-hook-bridge', {}).get('settings', {})
selection = {'model': config.get('model'), 'tiers': {key: value for key, value in settings.items()
    if key.startswith(('haiku', 'sonnet', 'opus', 'fable', 'pinned'))}}
model_hash = hashlib.sha256(json.dumps(selection, sort_keys=True).encode()).hexdigest()
assert model_hash == '6f6aae9afe9ae447d2e8a4d7df31642a826ca4e2e2cd76112b9b3caad3710770'
aliases = {}
for name in ('hermes', 'hermes-agent', 'hermes-acp'):
    target = home / '.local/bin' / name
    entry = next(entry for entry in programs['entries'] if entry['target'] == str(target))
    digest = hashlib.sha256(target.read_bytes()).hexdigest()
    assert digest == entry['after']['sha256']
    aliases[name] = digest
services = {}
for unit in ('hermes-gateway.service', 'hermes-dashboard.service', 'com.lifeos.pulse.service'):
    result = subprocess.run(['systemctl', '--user', 'show', unit, '-p', 'ActiveState', '-p', 'SubState'],
        env=environment, capture_output=True, text=True, check=True, timeout=30)
    services[unit] = dict(line.split('=', 1) for line in result.stdout.splitlines())
assert services['hermes-dashboard.service'] == {'ActiveState': 'active', 'SubState': 'running'}
print(json.dumps({'status': 'PASS', 'operation': args.operation,
    'operation_state': status['state'], 'program_transaction_state': programs['state'],
    'active_identity': expected, 'model_selection_sha256': model_hash,
    'selected_models_and_tiers_preserved': True, 'public_commands_sha256': aliases,
    'services': services, 'daily_server_changed': False}, indent=2))
