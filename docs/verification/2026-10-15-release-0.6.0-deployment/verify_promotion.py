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

def verify_daily_memory(baseline, recalled):
    assert baseline['status'] == 'PASS' and baseline['server'] == 'daily'
    assert baseline['synthetic_query'] == 'STABLE-050-DAILY-04EFE633'
    assert baseline['actual_owner_save_and_search_verified'] is True
    assert baseline['authenticated_owner_verified'] is True and baseline['prior_forgotten_facts_absent'] is True
    assert baseline['personal_data_imported_or_reset'] is False
    reference = baseline['reference']
    assert set(reference) == {'id', 'revision'} and len(reference['id']) == 32
    assert set(reference['id']) <= set('0123456789abcdef')
    assert type(reference['revision']) is int and reference['revision'] > 0
    assert recalled['status'] == 'ok' and len(recalled['results']) == 1
    assert recalled['results'][0]['reference'] == reference
    return reference


parser = argparse.ArgumentParser()
parser.add_argument('server', choices=('daily', 'development'))
parser.add_argument('operation')
parser.add_argument('baseline', type=Path)
args = parser.parse_args()
if sys.flags.optimize:
    raise RuntimeError('Promotion verification requires assertions')
home = Path('/home/lifeos-hermes')
profile = home / '.hermes'
baseline = json.loads(args.baseline.read_bytes())
assert baseline['status'] == 'PASS' and baseline['server'] == args.server
assert isinstance(baseline['configuration_file_sha256'], dict)
assert set(baseline['configuration_file_sha256']) == {'.env', 'lifeos-memory.json'}
for digest in [baseline['model_selection_sha256'], *baseline['configuration_file_sha256'].values()]:
    assert isinstance(digest, str) and len(digest) == 64 and set(digest) <= set('0123456789abcdef')
assert isinstance(baseline['services'], dict)
assert set(baseline['services']) == {'hermes-gateway.service', 'hermes-dashboard.service', 'com.lifeos.pulse.service'}
for expected in baseline['services'].values():
    assert isinstance(expected, dict) and expected['active'] is True
    assert expected['profile'] == str(profile)
    assert isinstance(expected['home'], str) and Path(expected['home']).is_absolute()
    assert Path(expected['home']).is_relative_to(home) and '..' not in Path(expected['home']).parts
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
assert request['version'] == '0.6.0'
assert request['commit'] == 'c86b5887b899ca779afbb217c33843e1ee12c381'
assert request['package_sha256'] == '9e2a1939efbaccc94abaa879b265f1af447f9bdfe0b82aecc76f872f15fa9fb7'
assert request['account_home'] == str(home)
assert cli.read_private(job / 'status.json')['state'] == 'applied'
plan = validate_plan(job, request)
transaction = ProgramTransaction(job / 'program-snapshot', expected_entries_sha256=plan['program_entries_sha256'])
worker = importlib.import_module(namespace.__name__ + '.release_worker')
current = worker.recovery_bridge(job, profile)
mount_module = current.memory_module('mount_transaction')
baseline_path = current.memory_module('version_drift').default_baseline_path(Path(request['installed']).parent)
mount = mount_module.MountTransaction(Path(request['installed']), profile, baseline_path)
worker.check_restore(job, request, plan, mount)
assert plan['fresh'] is False and plan['native_mount_required'] is False
mount_before = json.loads(args.baseline.with_name(args.server + '-owner-mount-before.json').read_bytes())
assert mount_before['status'] == 'PASS' and mount_before['state'] == 'committed'
assert hashlib.sha256(mount.journal.read_bytes()).hexdigest() == mount_before['current_owner_mount_sha256']
mount.check_completed()
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
    'native_mount_required': False, 'current_owner_mount_journal_preserved': True,
    'model_selection_sha256': model_hash, 'model_and_tiers_preserved': True,
    'credential_file_bytes_preserved': True, 'memory_configuration_bytes_preserved': True,
    'services': services, 'personal_data_imported_or_reset': False, 'personal_records_read': False}
if args.server == 'daily':
    credentials = json.loads((home / 'install-input/dashboard-access.json').read_bytes())
    with httpx.Client(base_url='http://127.0.0.1:18819', timeout=60) as client:
        login = client.post('/auth/password-login', json={'provider': 'basic', **credentials})
        assert login.status_code == 200
        identity = client.get('/api/auth/me')
        assert identity.status_code == 200
        me = identity.json()
        assert me['provider'] == 'basic' and me['user_id'] == 'adrian'
        response = client.post('/api/plugins/lifeos-hook-bridge/memory/review',
            headers={'X-Hermes-Profile': 'default'}, json={'tool': 'lifeos_memory_search',
                'arguments': {'query': 'STABLE-050-DAILY-04EFE633'}})
        recalled = response.json()
        assert response.status_code == 200
        memory_baseline = json.loads((home / 'releases/qualification-0.5.0/daily-memory-baseline.json').read_bytes())
        reference = verify_daily_memory(memory_baseline, recalled)
        prior = client.post('/api/plugins/lifeos-hook-bridge/memory/review',
            headers={'X-Hermes-Profile': 'default'}, json={'tool': 'lifeos_memory_search',
                'arguments': {'query': 'D253-CEREBO-1011'}})
        assert prior.status_code == 200 and prior.json() == {'status': 'ok', 'results': []}
        forgotten = client.post('/api/plugins/lifeos-hook-bridge/memory/review',
            headers={'X-Hermes-Profile': 'default'}, json={'tool': 'lifeos_memory_search',
                'arguments': {'query': 'D253-042-PROMOTION-1014'}})
        assert forgotten.status_code == 200 and forgotten.json() == {'status': 'ok', 'results': []}
        report.update(authenticated_owner_verified=True, synthetic_memory_reference=reference,
            synthetic_memory_preserved=True, prior_forgotten_fact_stays_absent=True)
print(json.dumps(report, indent=2))
