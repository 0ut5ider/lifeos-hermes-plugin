# ABOUTME: Verifies the restored daily program seal and current configuration through safe checks.
# ABOUTME: Exercises actual authenticated owner routes and synthetic Atlas cases without exporting personal records.
import hashlib
import importlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import types

home = Path('/home/lifeos-hermes')
profile = home / '.hermes'
stage = home / 'checkpoint-verification-20261014'
operation = '52af3122ef614ac49ef55b692e392f0c'
job = profile / '.lifeos-releases' / operation
package = job / 'package'
os.environ.update(HOME=str(home), HERMES_HOME=str(profile), PYTHONDONTWRITEBYTECODE='1',
    XDG_RUNTIME_DIR='/run/user/1000', DBUS_SESSION_BUS_ADDRESS='unix:path=/run/user/1000/bus',
    PATH=str(home / '.local/bin') + ':' + str(Path(sys.executable).parent) + ':/usr/local/bin:/usr/bin:/bin')
namespace = types.ModuleType('checkpoint_release_manager')
namespace.__path__ = [str(profile / 'plugins/lifeos-release-manager')]
sys.modules[namespace.__name__] = namespace
validate_plan = importlib.import_module(namespace.__name__ + '.release_operation').validate_plan
ProgramTransaction = importlib.import_module(namespace.__name__ + '.release_programs').ProgramTransaction
request = json.loads((job / 'request.json').read_bytes())
assert request['version'] == '0.4.3' and request['commit'] == 'a1abb579558edcf29f7cd04ecfd998995d48db54'
assert request['package_sha256'] == '1c7de7abc4014bfee83bc9bdcd4bfdb6c169526844d44491741d56645f400177'
assert json.loads((job / 'status.json').read_bytes())['state'] == 'applied'
plan = validate_plan(job, request)
transaction = ProgramTransaction(job / 'program-snapshot', expected_entries_sha256=plan['program_entries_sha256'])
transaction.check_applied()
baseline = json.loads((stage / 'daily-promotion-baseline.json').read_bytes())
assert baseline['status'] == 'PASS' and baseline['server'] == 'daily'
assert set(baseline['configuration_file_sha256']) == {'.env', 'lifeos-memory.json'}
for name, digest in baseline['configuration_file_sha256'].items():
    assert hashlib.sha256((profile / name).read_bytes()).hexdigest() == digest
units = home / '.config/systemd/user'
for name in ('hermes-dashboard.service', 'hermes-gateway.service', 'com.lifeos.pulse.service'):
    assert (units / name).is_symlink() and os.readlink(units / name) == '/dev/null'
    assert (units / (name + '.before-checkpoint-test')).is_file()
version = subprocess.run([str(home / '.local/bin/hermes'), 'lifeos-version'],
    capture_output=True, text=True, check=True, timeout=90)
active = json.loads(version.stdout)['active']
assert active['verification'] == 'verified' and all(active[key] == request[key] for key in ('version', 'commit', 'package_sha256'))
import httpx
from ruamel.yaml import YAML
config = YAML(typ='safe').load((profile / 'config.yaml').read_bytes())
settings = config.get('plugins', {}).get('entries', {}).get('lifeos-hook-bridge', {}).get('settings', {})
selection = {'model': config.get('model'), 'tiers': {key: value for key, value in settings.items()
    if key.startswith(('haiku', 'sonnet', 'opus', 'fable', 'pinned'))}}
assert hashlib.sha256(json.dumps(selection, sort_keys=True).encode()).hexdigest() == baseline['model_selection_sha256']
stdout = (stage / 'dashboard.stdout').open('w')
stderr = (stage / 'dashboard.stderr').open('w')
server_code = "from dotenv import load_dotenv;load_dotenv('.env');from hermes_cli.web_server import app;import uvicorn;uvicorn.run(app,host='127.0.0.1',port=18819,lifespan='off',ws='none',log_level='error')"
dashboard = subprocess.Popen([sys.executable, '-B', '-c', server_code],
    cwd=profile, stdout=stdout, stderr=stderr, start_new_session=True)
try:
    with httpx.Client(base_url='http://127.0.0.1:18819', timeout=60) as client:
        deadline = time.monotonic() + 90
        while True:
            assert dashboard.poll() is None, 'The isolated dashboard exits before readiness'
            try:
                if client.get('/api/auth/providers').status_code == 200:
                    break
            except httpx.TransportError:
                pass
            assert time.monotonic() < deadline, 'The isolated dashboard does not become ready'
            time.sleep(0.5)
        credentials = json.loads((home / 'install-input/dashboard-access.json').read_bytes())
        response = client.post('/auth/password-login', json={'provider': 'basic', **credentials})
        assert response.status_code == 200
        identity = client.get('/api/auth/me').json()
        assert identity['provider'] == 'basic' and identity['user_id'] == 'adrian'
        owner = client.get('/api/plugins/lifeos-hook-bridge/memory')
        assert owner.status_code == 200
        for marker in ('D253-042-PROMOTION-1014', 'D253-CEREBO-1011'):
            result = client.post('/api/plugins/lifeos-hook-bridge/memory/review',
                headers={'X-Hermes-Profile': 'default'}, json={'tool': 'lifeos_memory_search', 'arguments': {'query': marker}})
            assert result.status_code == 200 and result.json()['status'] == 'ok' and not result.json()['results']
finally:
    import signal
    os.killpg(dashboard.pid, signal.SIGTERM)
    dashboard.wait(timeout=30)
    stdout.close()
    stderr.close()

helper = stage / 'history_guest_recovery.py'
for action in ('prepare', 'verify'):
    result = subprocess.run([sys.executable, '-B', str(helper), action, str(package)],
        capture_output=True, text=True, timeout=600)
    (stage / ('atlas-' + action + '.stdout')).write_text(result.stdout)
    (stage / ('atlas-' + action + '.stderr')).write_text(result.stderr)
    assert result.returncode == 0, 'The synthetic current Atlas ' + action + ' fails; inspect private guest evidence'
    history = json.loads(result.stdout)
    assert history['status'] == 'PASS' and history['version'] == '0.4.3' and len(history['cases']) == 3
    assert history['personal_data_used'] is False and history['live_store_modified'] is False
print(json.dumps({'status': 'PASS', 'version': request['version'], 'program_commit': request['commit'],
    'archive_sha256': request['package_sha256'], 'operation': operation,
    'sealed_program_targets': len(transaction._load()['entries']),
    'credential_and_memory_configuration_bytes_preserved': True, 'model_and_tiers_preserved': True,
    'authenticated_restored_owner_verified': True, 'dashboard_background_startup_disabled': True, 'governed_synthetic_forget_state_preserved': True,
    'personal_records_exported': False, 'personal_data_imported_or_reset': False,
    'atlas_cases': history['cases'],
    'atlas_scope': 'Synthetic current-program fixtures created and verified after restoring the daily checkpoint. These fixtures were not inside the checkpoint.',
    'source_daily_server_modified': False}, indent=2))
