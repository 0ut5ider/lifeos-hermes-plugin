# ABOUTME: Prepares only the isolated installed profile for actual dashboard and Pulse acceptance.
# ABOUTME: Selects the reviewed fresh home and retains the existing private model tier configuration.
import importlib
import hashlib
import io
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys

sys.dont_write_bytecode = True
stage = Path('/home/lifeos-hermes/migration/2026-10-09/daily-text-581d76a7')
package = stage / 'package'
candidate = stage / 'mount-plugin-source/lifeos'
profile = stage / 'profile'
review = json.loads((stage / 'fresh-store-installed.json').read_text())['fresh_store_review']
installed = Path(review['installed'])
home = installed.parent
python = '/home/lifeos-hermes/.hermes/installs/995dd15ff6e15ed0/environments/65f4231f26e94a2d989e89eb96b98808/venv/bin/python'
os.umask(0o077)
os.environ.update(HOME=str(home), HERMES_HOME=str(profile),
    PATH=str(stage / 'bin') + ':/home/lifeos-hermes/.local/bin:/home/lifeos-hermes/.hermes/tools/node-26.7.0-linux-x64/bin:/usr/bin:/bin',
    PYTHONPATH=str(package / 'hermes'), TZ='America/Toronto',
    LIFEOS_NOTIFICATION_CHANNEL='headless', BUN_CONFIG_NO_AUTO_INSTALL='1')
sys.path.insert(0, str(package / 'hermes'))
from ruamel.yaml import YAML
configured = YAML(typ='safe').load(Path('/home/lifeos-hermes/.hermes/config.yaml').read_text())
model = configured['model']
settings = configured['plugins']['entries']['lifeos-hook-bridge']['settings']
tiers = {key: value for key, value in settings.items()
    if key == 'pinned_tier' or key.endswith(('_model', '_provider', '_effort', '_inherit_child_default'))}
for name, effort in {'haiku': 'low', 'sonnet': 'medium', 'opus': 'xhigh', 'fable': 'xhigh'}.items():
    if tiers.get(name + '_effort') != effort:
        raise RuntimeError('The installed private tier selection differs from the approved release')
plugins = profile / 'plugins'
plugins.mkdir(mode=0o700, exist_ok=True)
bridge = plugins / 'lifeos-hook-bridge'
if bridge.exists():
    expected = json.loads((stage / 'APPLICATION-CANDIDATE.json').read_text())['plugin_files']
    for relative, digest in expected.items():
        selected = bridge / Path(relative).relative_to('lifeos_hook_bridge')
        if hashlib.sha256(selected.read_bytes()).hexdigest() != digest:
            raise RuntimeError('The retained application bridge differs from the staged package')
else:
    shutil.copytree(package / 'lifeos_hook_bridge', bridge, ignore=shutil.ignore_patterns('__pycache__'))
sys.path.insert(0, str(plugins))
def module(name):
    return importlib.import_module('lifeos-hook-bridge.' + name)
configuration = module('memory_service').MemoryConfiguration(profile / 'lifeos-memory.json')
fresh = module('fresh_store').FreshStore(configuration)
current_home, current = fresh.review_home(home.parent.name, account='dashboard:acceptance-owner')
if current_home != home or current['state'] != 'review' or current['names'] != review['names']:
    raise RuntimeError('The isolated fresh review changes before application preparation')
workspace = stage / 'workspace'
workspace.mkdir(mode=0o700, exist_ok=True)
module('lifeos_installation').publish(profile, home, workspace)
route = module('memory_context').route_identity('custom', model['default'], model['base_url'],
    model.get('api_mode', 'chat_completions'))
configuration.update(lambda value: value.update(root=str(installed),
    accounts={'dashboard:basic:acceptance-owner': value['principal'],
              'dashboard:acceptance-owner': value['principal'], f'terminal:{os.getuid()}': value['principal']},
    destinations={'terminal:' + str(profile): {'visibility': 'private', 'participants': [value['principal']],
        'read': ['principal', 'assistant', 'project'], 'write': ['principal', 'assistant', 'project'],
        'projects': ['*'], 'model_routes': [route]}}))
from plugins.dashboard_auth.basic import hash_password
document = {'model': model, 'agent': configured.get('agent', {}),
    'memory': {'memory_enabled': False, 'user_profile_enabled': False},
    'plugins': {'enabled': ['lifeos-hook-bridge'], 'entries': {'lifeos-hook-bridge': {'settings': {
        **tiers, 'lifeos_source_dir': str(candidate / 'LifeOS/install')}}}},
    'dashboard': {'public_url': 'http://acceptance.invalid:18819',
        'basic_auth': {'username': 'acceptance-owner',
            'password_hash': hash_password('synthetic-application-acceptance-password')}}}
yaml = YAML()
yaml.default_flow_style = False
serialized = io.StringIO()
yaml.dump(document, serialized)
module('memory_transaction').publish(profile / 'config.yaml', serialized.getvalue().encode())
(stage / 'bin').mkdir(mode=0o700, exist_ok=True)
launcher = stage / 'bin/hermes'
launcher.write_text('#!/bin/sh\nexec ' + shlex.quote(python) + ' -B -m hermes_cli.main "$@"\n')
launcher.chmod(0o700)
baseline = module('version_drift').default_baseline_path(home)
receipt = module('install_source').finalize_prepared_lifeos(candidate, installed, profile,
    baseline, module('version_drift').create_baseline, module('version_drift').save_baseline)
# The fixed connector selects the same copied bridge as dashboard plugin discovery.
directory = installed / 'LIFEOS/USER/CONFIG'
publish = module('memory_transaction').publish
publish(directory / 'memory-access.json', json.dumps({'version': 1, 'command': [python,
    str(bridge / 'memory_rpc.py'), '--configuration', str(configuration.path)]}).encode())
publish(directory / 'memory-http.json', json.dumps({'version': 1, 'dashboard_base_url':
    'http://127.0.0.1:18819'}).encode())
daily = (package / 'docs/deployment/daily-text/PULSE.user.toml').read_bytes()
publish(directory / 'PULSE.user.toml', daily)
conduit = installed / 'LIFEOS/USER/CONDUIT/config.json'
conduit.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
publish(conduit, (package / 'docs/deployment/daily-text/CONDUIT.config.json').read_bytes())
report = {'profile': str(profile), 'installed': str(installed), 'workspace': str(workspace),
    'mount': receipt, 'ownership_enabled': configuration.load()['ownership_enabled'],
    'sharing_enabled': configuration.load()['sharing_enabled'], 'private_tiers': tiers,
    'loopback_ports': {'dashboard': 18819, 'pulse': 18837},
    'transport_credentials_loaded': False, 'live_profile_changed': False}
(stage / 'applications-prepared.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
