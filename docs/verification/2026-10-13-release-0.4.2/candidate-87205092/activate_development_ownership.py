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
stage = Path.home() / 'releases/qualification-0.4.2-87205092'
authority = json.loads((stage / 'development-owner-authority.json').read_bytes())
assert authority['http_status'] == 200
session = authority['session']
assert session['provider'] == 'basic' and session['user_id'] == 'release-owner'
assert session['expires_at'] > time.time()
account = 'dashboard:' + session['provider'] + ':' + session['user_id']
os.environ.update(HERMES_HOME=str(profile), XDG_RUNTIME_DIR='/run/user/' + str(os.getuid()),
    DBUS_SESSION_BUS_ADDRESS='unix:path=/run/user/' + str(os.getuid()) + '/bus',
    PATH=str(Path.home() / '.local/bin') + ':/usr/bin:/bin')
sys.path[:0] = [str(profile / 'plugins'),
    str(profile / '.lifeos-releases/3240c42939f2451293bd9d5cfcd8bf12/hermes')]


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
    value['accounts']['terminal:' + str(os.getuid())] = value['principal']
    value['destinations']['terminal:' + str(profile)] = {
        'visibility': 'private', 'participants': [value['principal']],
        'read': ['principal', 'assistant', 'project'], 'write': ['principal', 'assistant', 'project'],
        'projects': ['*'], 'model_routes': [route]}


configuration.update(local_grant)
installed = Path(selected['root'])
publish = module('memory_transaction').publish
connector = installed / 'LIFEOS/USER/CONFIG/memory-access.json'
expected = {'version': 1, 'command': [sys.executable,
    str(profile / 'plugins/lifeos-hook-bridge/memory_rpc.py'),
    '--configuration', str(configuration.path)]}
if connector.exists():
    assert not connector.is_symlink() and json.loads(connector.read_bytes()) == expected
else:
    publish(connector, json.dumps(expected).encode())
http = connector.with_name('memory-http.json')
expected_http = {'version': 1, 'dashboard_base_url': 'http://127.0.0.1:9119'}
if http.exists():
    assert not http.is_symlink() and json.loads(http.read_bytes()) == expected_http
else:
    publish(http, json.dumps(expected_http).encode())
module('memory_administration')._connector(configuration, configuration.load())
setup = module('ownership_setup').OwnershipSetup(configuration)
report = {'status': 'IN_PROGRESS', 'operation': '3240c42939f2451293bd9d5cfcd8bf12',
    'authenticated_owner_verified': True, 'local_owner_uid': os.getuid(),
    'private_model_route_sha256': route, 'model_selection_sha256': before,
    'connector_verified': True, 'personal_data_imported': False, 'sharing_enabled': False,
    'daily_server_changed': False}
try:
    plan = setup.prepare(stage / 'development-ownership-backup', account=account)
    report['backup_review'] = plan
    (stage / 'development-ownership-review.json').write_text(json.dumps(report, indent=2) + '\n')
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
    (stage / 'development-ownership-activation.json').write_text(json.dumps(report, indent=2) + '\n')
    (stage / 'development-ownership-activation.done').write_text('0\n' if report['status'] == 'PASS' else '1\n')
