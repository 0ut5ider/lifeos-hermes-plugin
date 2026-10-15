# ABOUTME: Activates synthetic owner memory through the installed backup and service-drain coordinator.
# ABOUTME: Binds local grants to the authenticated owner, selected account, profile, and private model route.
import hashlib
import importlib
import json
import os
from pathlib import Path
import sys
import time

from ruamel.yaml import YAML

sys.dont_write_bytecode = True
os.umask(0o077)
profile = Path.home() / '.hermes'
stage = Path.home() / 'releases/qualification-0.5.0'
import httpx
credentials = json.loads((Path.home() / 'install-input/dashboard-access.json').read_bytes())
with httpx.Client(base_url='http://127.0.0.1:18819', timeout=90) as client:
    response = client.post('/auth/password-login', json={'provider': 'basic', **credentials})
    assert response.status_code == 200
    response = client.get('/api/auth/me')
    assert response.status_code == 200
    session = response.json()
    if not (profile / 'lifeos-memory.json').exists():
        claimed = client.post('/api/plugins/lifeos-hook-bridge/memory/owner', headers={'X-Hermes-Profile': 'default'})
        assert claimed.status_code == 200, 'The authenticated installation claim refuses'
assert session['provider'] == 'basic' and session['user_id'] == 'qualification-owner'
assert session['expires_at'] > time.time()
account = 'dashboard:' + session['provider'] + ':' + session['user_id']
os.environ.update(HERMES_HOME=str(profile), XDG_RUNTIME_DIR='/run/user/' + str(os.getuid()),
    DBUS_SESSION_BUS_ADDRESS='unix:path=/run/user/' + str(os.getuid()) + '/bus',
    PATH=str(Path.home() / '.local/bin') + ':/usr/bin:/bin')
prepared = json.loads((stage / 'fresh-preparation.json').read_bytes())
identifier = prepared['preparation']['identifier']
assert json.loads((stage / 'fresh-apply.json').read_bytes())['status'] == 'PASS'
sys.path[:0] = [str(profile / 'plugins'), str(profile / '.lifeos-releases' / identifier / 'hermes')]


def module(name):
    return importlib.import_module('lifeos-hook-bridge.' + name)


def selection_hash():
    data = YAML(typ='safe').load((profile / 'config.yaml').read_bytes())
    settings = data.get('plugins', {}).get('entries', {}).get('lifeos-hook-bridge', {}).get('settings', {})
    selected = {'model': data.get('model'), 'tiers': {key: value for key, value in settings.items()
        if key.startswith(('haiku', 'sonnet', 'opus', 'fable', 'pinned'))}}
    return hashlib.sha256(json.dumps(selected, sort_keys=True).encode()).hexdigest()


configuration = module('memory_service').MemoryConfiguration(profile / 'lifeos-memory.json')
selected = configuration.load()
configuration.check_owner(selected, account)
assert selected['ownership_enabled'] is False and selected['sharing_enabled'] is False
model = YAML(typ='safe').load((profile / 'config.yaml').read_bytes())['model']
route = module('memory_context').route_identity(model.get('provider', 'custom'),
    model['default'], model['base_url'], model.get('api_mode', 'chat_completions'))
assert route != 'unknown'
before = selection_hash()


def local_grant(value):
    configuration.check_owner(value, account)
    assert value['ownership_enabled'] is False
    value['pulse_http'] = {'dashboard_base_url': 'http://127.0.0.1:18819'}
    value['accounts']['terminal:' + str(os.getuid())] = value['principal']
    value['destinations']['terminal:' + str(profile)] = {
        'visibility': 'private', 'participants': [value['principal']],
        'read': ['principal', 'assistant', 'project'], 'write': ['principal', 'assistant', 'project'],
        'projects': ['*'], 'model_routes': [route]}


configuration.update(local_grant)
installed = Path(selected['root'])
publish = module('memory_transaction').publish
connector = installed / 'LIFEOS/USER/CONFIG/memory-access.json'
assert not connector.exists() and not connector.is_symlink()
publish(connector, json.dumps({'version': 1, 'command': [sys.executable,
    str(profile / 'plugins/lifeos-hook-bridge/memory_rpc.py'),
    '--configuration', str(configuration.path)]}).encode())
http = connector.with_name('memory-http.json')
assert not http.exists() and not http.is_symlink()
publish(http, json.dumps({'version': 1, 'dashboard_base_url': 'http://127.0.0.1:18819'}).encode())
module('memory_administration')._connector(configuration, configuration.load())
setup = module('ownership_setup').OwnershipSetup(configuration)
report = {'status': 'IN_PROGRESS', 'operation': identifier,
    'authenticated_owner_verified': True, 'local_owner_uid': os.getuid(),
    'private_model_route_sha256': route, 'model_selection_sha256': before,
    'connector_verified': True, 'personal_data_imported': False, 'sharing_enabled': False,
    'daily_server_changed': False}
try:
    plan = setup.prepare(stage / 'fresh-ownership-backup', account=account)
    report['backup_review'] = plan
    (stage / 'fresh-ownership-review.json').write_text(json.dumps(report, indent=2) + '\n')
    receipt = setup.apply(plan['signature'], account=account)
    assert receipt['state'] == 'configured' and configuration.load()['ownership_enabled'] is True
    assert selection_hash() == before
    report.update(status='PASS', ownership_receipt=receipt, service_state=setup.status(account=account),
        selected_model_and_tiers_preserved=True, actual_owner_turn_verified=False)
except BaseException as error:
    report.update(status='FAIL', error_type=type(error).__name__)
    if setup.status(account=account)['recovery_required']:
        report['recovery'] = setup.recover(account=account)
    raise
finally:
    (stage / 'fresh-ownership-activation.json').write_text(json.dumps(report, indent=2) + '\n')
    (stage / 'fresh-ownership-activation.done').write_text('0\n' if report['status'] == 'PASS' else '1\n')
