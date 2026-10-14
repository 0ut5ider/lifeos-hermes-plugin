# ABOUTME: Verifies an actual development update or restore without reading personal records.
# ABOUTME: Exports release identity, service state, program hashes, and model-selection hashes only.
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess

from ruamel.yaml import YAML

parser = argparse.ArgumentParser()
parser.add_argument('operation')
parser.add_argument('--state', choices=('applied', 'rolled_back'), required=True)
args = parser.parse_args()
home = Path.home()
profile = home / '.hermes'
job = profile / '.lifeos-releases' / args.operation
request = json.loads((job / 'request.json').read_bytes())
status = json.loads((job / 'status.json').read_bytes())
programs = json.loads((job / 'program-snapshot/programs.json').read_bytes())
environment = dict(os.environ, HOME=str(home), HERMES_HOME=str(profile), PYTHONPATH='',
    PYTHONDONTWRITEBYTECODE='1', XDG_RUNTIME_DIR='/run/user/' + str(os.getuid()),
    DBUS_SESSION_BUS_ADDRESS='unix:path=/run/user/' + str(os.getuid()) + '/bus')
environment['PATH'] = str(home / '.local/bin') + ':' + environment.get('PATH', os.defpath)
command = home / '.local/bin/hermes'
version = subprocess.run([str(command), 'lifeos-version'], env=environment,
    capture_output=True, text=True, timeout=90)
assert version.returncode == 0, 'The installed version command fails'
active = json.loads(version.stdout)['active']
assert active['verification'] == 'verified', 'The active bridge has changed program bytes'
expected = request if args.state == 'applied' else {
    'version': '0.4.1', 'commit': '96f4f8fbef21f53ee704eb16f34698bc35b5dc77',
    'package_sha256': '462297fa0c20166ca77d0bf37fcef556b50832ff7bf46327d9777368ea80670e'}
assert all(active[key] == expected[key] for key in ('version', 'commit', 'package_sha256'))
assert status['state'] == args.state, 'The operation has not reached the expected state'
assert programs['state'] == ('applied' if args.state == 'applied' else 'restored')
config = YAML(typ='safe').load((profile / 'config.yaml').read_bytes())
settings = config.get('plugins', {}).get('entries', {}).get('lifeos-hook-bridge', {}).get('settings', {})
selection = {'model': config.get('model'), 'tiers': {key: value for key, value in settings.items()
    if key.startswith(('haiku', 'sonnet', 'opus', 'fable', 'pinned'))}}
model_hash = hashlib.sha256(json.dumps(selection, sort_keys=True).encode()).hexdigest()
assert model_hash == 'a4cabe0e802a98b003882fbdc776f4b30179b7ac3795de6644f1bdb9bca89e2f'
services = {}
for unit in ('hermes-gateway.service', 'hermes-dashboard.service', 'com.lifeos.pulse.service'):
    result = subprocess.run(['systemctl', '--user', 'show', unit, '-p', 'ActiveState', '-p', 'SubState'],
        env=environment, capture_output=True, text=True, check=True, timeout=30)
    services[unit] = dict(line.split('=', 1) for line in result.stdout.splitlines())
    assert services[unit] == {'ActiveState': 'active', 'SubState': 'running'}, 'A service does not run'
aliases = {}
for name in ('hermes', 'hermes-agent', 'hermes-acp'):
    target = home / '.local/bin' / name
    entry = next(entry for entry in programs['entries'] if entry['target'] == str(target))
    digest = hashlib.sha256(target.read_bytes()).hexdigest()
    assert digest == entry['after' if args.state == 'applied' else 'before']['sha256']
    aliases[name] = digest
if args.state == 'rolled_back':
    assert hashlib.sha256((profile / 'config.yaml').read_bytes()).hexdigest() == request['configuration_sha256']
print(json.dumps({'operation': args.operation, 'status': 'PASS', 'test_fixture_only': True,
    'operation_state': status['state'], 'program_transaction_state': programs['state'],
    'active_identity': {key: active[key] for key in ('version', 'commit', 'package_sha256')},
    'model_selection_sha256': model_hash, 'public_commands_sha256': aliases,
    'services': services, 'daily_server_changed': False}, indent=2))
