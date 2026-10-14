# ABOUTME: Verifies the complete selected public release and preserved installation configuration after promotion.
# ABOUTME: Uses authenticated memory tools for the daily synthetic fact and exports no personal records or credential values.
import argparse
import hashlib
import importlib
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import types

import httpx
from ruamel.yaml import YAML

parser = argparse.ArgumentParser()
parser.add_argument('server', choices=('daily', 'development'))
parser.add_argument('operation')
parser.add_argument('baseline', type=Path)
args = parser.parse_args()
home = Path('/home/lifeos-hermes')
profile = home / '.hermes'
baseline = json.loads(args.baseline.read_bytes())
assert baseline['status'] == 'PASS' and baseline['server'] == args.server
os.environ.update(HERMES_HOME=str(profile), XDG_RUNTIME_DIR='/run/user/' + str(os.getuid()),
    DBUS_SESSION_BUS_ADDRESS='unix:path=/run/user/' + str(os.getuid()) + '/bus',
    PATH=str(home / '.local/bin') + ':/usr/bin:/bin', PYTHONDONTWRITEBYTECODE='1')
namespace = types.ModuleType('promotion_manager')
namespace.__path__ = [str(profile / 'plugins/lifeos-release-manager')]
sys.modules[namespace.__name__] = namespace
cli = importlib.import_module(namespace.__name__ + '.cli')
validate_plan = importlib.import_module(namespace.__name__ + '.release_operation').validate_plan
ProgramTransaction = importlib.import_module(namespace.__name__ + '.release_programs').ProgramTransaction
job, request = cli.operation(profile, args.operation)
assert request['version'] == '0.4.3'
assert request['commit'] == 'a1abb579558edcf29f7cd04ecfd998995d48db54'
assert request['package_sha256'] == '1c7de7abc4014bfee83bc9bdcd4bfdb6c169526844d44491741d56645f400177'
assert request['account_home'] == str(home)
assert cli.read_private(job / 'status.json')['state'] == 'applied'
plan = validate_plan(job, request)
transaction = ProgramTransaction(job / 'program-snapshot', expected_entries_sha256=plan['program_entries_sha256'])
transaction.check_applied()
active = json.loads(subprocess.run([str(home / '.local/bin/hermes'), 'lifeos-version'],
    capture_output=True, text=True, check=True, timeout=90).stdout)['active']
assert active['verification'] == 'verified'
assert all(active[key] == request[key] for key in ('version', 'commit', 'package_sha256'))
config = YAML(typ='safe').load((profile / 'config.yaml').read_bytes())
settings = config.get('plugins', {}).get('entries', {}).get('lifeos-hook-bridge', {}).get('settings', {})
selection = {'model': config.get('model'), 'tiers': {key: value for key, value in settings.items()
    if key.startswith(('haiku', 'sonnet', 'opus', 'fable', 'pinned'))}}
model_hash = hashlib.sha256(json.dumps(selection, sort_keys=True).encode()).hexdigest()
assert model_hash == baseline['model_selection_sha256']
for name, digest in baseline['configuration_file_sha256'].items():
    assert hashlib.sha256((profile / name).read_bytes()).hexdigest() == digest, name
services = {}
for name, expected in baseline['services'].items():
    result = subprocess.run(['systemctl', '--user', 'show', name,
        '--property=ActiveState,SubState,MainPID', '--no-pager'], capture_output=True, text=True, check=True)
    values = dict(line.split('=', 1) for line in result.stdout.splitlines() if '=' in line)
    assert values['ActiveState'] == 'active' and values['SubState'] == 'running'
    environment = dict(value.split('=', 1) for value in
        Path('/proc/' + values['MainPID'] + '/environ').read_bytes().decode().split('\0') if '=' in value)
    assert environment['HOME'] == expected['home'] and environment['HERMES_HOME'] == expected['profile']
    services[name] = {'active': True, 'home_preserved': True, 'profile_preserved': True}
report = {'status': 'PASS', 'server': args.server, 'operation': args.operation, 'active_identity': active,
    'program_state': 'applied', 'sealed_program_targets': len(transaction._load()['entries']),
    'model_selection_sha256': model_hash, 'model_and_tiers_preserved': True,
    'credential_file_bytes_preserved': True, 'memory_configuration_bytes_preserved': True,
    'services': services, 'personal_data_imported_or_reset': False, 'personal_records_read': False}
if args.server == 'daily':
    credentials = json.loads((home / 'install-input/dashboard-access.json').read_bytes())
    with httpx.Client(base_url='http://127.0.0.1:18819', timeout=60) as client:
        login = client.post('/auth/password-login', json={'provider': 'basic', **credentials})
        assert login.status_code == 200
        me = client.get('/api/auth/me').json()
        assert me['session']['provider'] == 'basic' and me['session']['user_id'] == 'adrian'
        response = client.post('/api/plugins/lifeos-hook-bridge/memory/review',
            headers={'X-Hermes-Profile': 'default'}, json={'tool': 'lifeos_memory_search',
                'arguments': {'query': 'D253-042-PROMOTION-1014'}})
        recalled = response.json()
        assert response.status_code == 200 and recalled['status'] == 'ok' and len(recalled['results']) == 1
        reference = recalled['results'][0]['reference']
        assert reference == {'id': '8565b850a9ce45a18f4c0540e398b5ee', 'revision': 1}
        prior = client.post('/api/plugins/lifeos-hook-bridge/memory/review',
            headers={'X-Hermes-Profile': 'default'}, json={'tool': 'lifeos_memory_search',
                'arguments': {'query': 'D253-CEREBO-1011'}})
        assert prior.status_code == 200 and prior.json()['status'] == 'ok' and not prior.json()['results']
        report.update(authenticated_owner_verified=True, synthetic_memory_reference=reference,
            synthetic_memory_preserved=True, prior_forgotten_fact_stays_absent=True)
print(json.dumps(report, indent=2))
