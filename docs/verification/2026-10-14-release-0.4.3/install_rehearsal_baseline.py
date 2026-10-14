# ABOUTME: Installs the accepted 0.3.1 program package in the synthetic daily-layout rehearsal guest.
# ABOUTME: Creates fresh synthetic data and native HOME service definitions without Discord credentials.
import hashlib
import importlib
import io
import json
import os
from pathlib import Path
import secrets
import shlex
import shutil
import subprocess
import sys
import tarfile

os.umask(0o077)
account_home = Path('/home/lifeos-hermes')
package = account_home / 'releases/0.3.1-9af63325'
runtime = account_home / 'runtime/releases/0.3.1-9af63325/hermes'
runtime.parent.mkdir(parents=True, mode=0o700)
shutil.copytree(package / 'hermes', runtime, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
dashboard = account_home / 'releases/hermes-dashboard-031.tgz'
assert hashlib.sha256(dashboard.read_bytes()).hexdigest() == '078d6da534408339fefcb3893431835ccfc7ce9483cc85a46ebf6b917e8cb2ee'
compiled = account_home / 'releases/compiled-dashboard-031'
compiled.mkdir(mode=0o700)
with tarfile.open(dashboard) as archive:
    archive.extractall(compiled, filter='data')
shutil.copytree(compiled / 'hermes_cli/web_dist', runtime / 'hermes_cli/web_dist')
profile = account_home / '.hermes'
evidence = account_home / 'deployment/2026-10-14'
evidence.mkdir(parents=True, mode=0o700, exist_ok=True)
python = account_home / '.hermes/installs/995dd15ff6e15ed0/environments/65f4231f26e94a2d989e89eb96b98808/venv/bin/python'
os.environ.update(PATH=str(account_home / '.local/bin') + ':' + str(account_home / '.hermes/tools/node-26.7.0-linux-x64/bin') + ':/usr/bin:/bin',
    HERMES_HOME=str(profile), PYTHONPATH=str(runtime), TZ='America/Toronto',
    LIFEOS_NOTIFICATION_CHANNEL='headless', BUN_CONFIG_NO_AUTO_INSTALL='1',
    BUN_INSTALL_CACHE_DIR=str(account_home / '.cache/daily-bun'), PYTHONDONTWRITEBYTECODE='1',
    XDG_RUNTIME_DIR='/run/user/' + str(os.getuid()),
    DBUS_SESSION_BUS_ADDRESS='unix:path=/run/user/' + str(os.getuid()) + '/bus')
sys.path[:0] = [str(runtime), str(package)]
from ruamel.yaml import YAML
from plugins.dashboard_auth.basic import hash_password

module = lambda name: importlib.import_module('lifeos_hook_bridge.' + name)
manifest = json.loads((package / 'DAILY-CANDIDATE.json').read_text())
assert manifest['head'] == '9af633252004a0ac8dd780d5fc12e9644f97bb0c'
for relative, expected in manifest['plugin_files'].items():
    assert hashlib.sha256((package / relative).read_bytes()).hexdigest() == expected, relative
source = module('install_source')
hermes_manifest = source.validate_supported_hermes(package / 'hermes')
lifeos_manifest = source.validate_prepared_lifeos(package / 'lifeos')
selected = {'model': {'default': 'flashnext-w4a16-fp8ple', 'provider': 'custom', 'base_url': 'http://127.0.0.1:9/v1', 'api_mode': 'chat_completions'}, 'agent': {'max_turns': 10}, 'tiers': {**{name + '_model': 'flashnext-w4a16-fp8ple' for name in ('haiku', 'sonnet', 'opus', 'fable')}, 'haiku_effort': 'low', 'sonnet_effort': 'medium', 'opus_effort': 'xhigh', 'fable_effort': 'xhigh'}, 'model_environment': {'CUSTOM_API_KEY': secrets.token_urlsafe(32)}}
assert selected['model']['default'] == 'flashnext-w4a16-fp8ple'
assert {name: selected['tiers'][name + '_effort'] for name in ('haiku', 'sonnet', 'opus', 'fable')} == {
    'haiku': 'low', 'sonnet': 'medium', 'opus': 'xhigh', 'fable': 'xhigh'}
assert not (profile / 'config.yaml').exists(), 'The daily profile is already configured'
profile.mkdir(mode=0o700, exist_ok=True)
os.chmod(profile, 0o700)
bridge = profile / 'plugins/lifeos-hook-bridge'
bridge.parent.mkdir(mode=0o700)
shutil.copytree(package / 'lifeos_hook_bridge', bridge, ignore=shutil.ignore_patterns('__pycache__'))
launcher = account_home / '.local/bin/hermes'
launcher.write_text('#!/bin/sh\nexport PYTHONPATH=' + shlex.quote(str(runtime)) + '\nexec ' + shlex.quote(str(python)) + ' -B -m hermes_cli.main "$@"\n')
launcher.chmod(0o700)
bootstrap = account_home / 'deployment/bootstrap/home/.claude'
bootstrap.parent.mkdir(parents=True, mode=0o700)
bootstrap_receipt = source.install_prepared_lifeos(package / 'lifeos', bootstrap, evidence / 'failed-bootstrap')
configuration = module('memory_service').MemoryConfiguration(profile / 'lifeos-memory.json')
configuration.save({'version': 1, 'root': str(bootstrap), 'principal': 'adrian',
    'ownership_enabled': False, 'sharing_enabled': False,
    'accounts': {'dashboard:basic:adrian': 'adrian'}, 'destinations': {}, 'clients': {}})
fresh = module('fresh_store').FreshStore(configuration).prepare(package / 'lifeos',
    principal_name='Synthetic Qualification', assistant_name='Synthetic Cerebo', account='dashboard:basic:adrian')
assert fresh['active_facts'] == 0 and not fresh['ownership_enabled'] and not fresh['sharing_enabled']
root = Path(fresh['installed'])
home = root.parent
workspace = account_home / 'HermesWorkspace'
workspace.mkdir(mode=0o700)
module('lifeos_installation').publish(profile, home, workspace)
route = module('memory_context').route_identity('custom', selected['model']['default'],
    selected['model']['base_url'], selected['model'].get('api_mode', 'chat_completions'))
configuration.update(lambda value: value.update(root=str(root), hermes_workspace=str(workspace),
    accounts={'dashboard:basic:adrian': 'adrian', 'terminal:' + str(os.getuid()): 'adrian'},
    pulse_http={'dashboard_base_url': 'http://127.0.0.1:18819'},
    destinations={'terminal:' + str(profile): {'visibility': 'private', 'participants': ['adrian'],
        'read': ['principal', 'assistant', 'project'], 'write': ['principal', 'assistant', 'project'],
        'projects': ['*'], 'model_routes': [route]}}))
password = secrets.token_urlsafe(32)
credentials = account_home / 'install-input/dashboard-access.json'
credentials.write_text(json.dumps({'username': 'adrian', 'password': password}) + '\n')
document = {'model': selected['model'], 'agent': selected['agent'],
    'platforms': {'api_server': {'enabled': True, 'extra': {'key': secrets.token_urlsafe(32), 'host': '127.0.0.1', 'port': 18642}}},
    'memory': {'memory_enabled': False, 'user_profile_enabled': False},
    'plugins': {'enabled': ['lifeos-hook-bridge'], 'entries': {'lifeos-hook-bridge': {'settings': {
        **selected['tiers'], 'lifeos_source_dir': str(package / 'lifeos/LifeOS/install')}}}},
    'dashboard': {'public_url': 'http://192.168.8.246:18819', 'basic_auth': {
        'username': 'adrian', 'password_hash': hash_password(password)}}}
stream = io.StringIO()
YAML().dump(document, stream)
publish = module('memory_transaction').publish
publish(profile / 'config.yaml', stream.getvalue().encode())
from dotenv import set_key
for key, value in selected['model_environment'].items():
    assert key == 'CUSTOM_API_KEY'
    set_key(str(profile / '.env'), key, value)
os.chmod(profile / '.env', 0o600)
os.environ.update(HOME=str(home), LIFEOS_DIR=str(root / 'LIFEOS'), LIFEOS_HOOK_SETTINGS=str(root / 'settings.json'))
mount = source.finalize_prepared_lifeos(package / 'lifeos', root, profile,
    module('version_drift').default_baseline_path(home),
    module('version_drift').create_baseline, module('version_drift').save_baseline)
directory = root / 'LIFEOS/USER/CONFIG'
publish(directory / 'memory-access.json', json.dumps({'version': 1, 'command': [str(python),
    str(bridge / 'memory_rpc.py'), '--configuration', str(configuration.path)]}).encode())
publish(directory / 'memory-http.json', json.dumps({'version': 1,
    'dashboard_base_url': 'http://127.0.0.1:18819'}).encode())
publish(directory / 'PULSE.user.toml', (package / 'docs/deployment/daily-text/PULSE.user.toml').read_bytes())
conduit = root / 'LIFEOS/USER/CONDUIT/config.json'
conduit.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
publish(conduit, (package / 'docs/deployment/daily-text/CONDUIT.config.json').read_bytes())
memory = module('memory_access').NativeMemory(root)
scope = module('memory_preferences').MemoryPreferences._owner_scope(configuration.load())
atlas = module('memory_atlas_sync').run(memory, scope, ['gear', 'projects'], 'full', check_current=lambda: None)
assert atlas['ok'], atlas
assert not module('memory_atlas').view(memory, scope)['body']['assets']
assert module('memory_morning_brief').run(memory, scope)['stdout'] == 'Good morning.\n'
units = {'gateway': 'hermes-gateway.service', 'dashboard': 'hermes-dashboard.service',
    'pulse': 'com.lifeos.pulse.service'}
commands = {'gateway': str(launcher) + ' gateway run --external-supervisor',
    'dashboard': str(launcher) + ' dashboard --isolated --skip-build --no-open --host 127.0.0.1 --port 18819',
    'pulse': str(account_home / '.local/bin/bun') + ' --no-install ' + str(root / 'LIFEOS/PULSE/pulse.ts')}
working = {'gateway': profile, 'dashboard': home, 'pulse': root / 'LIFEOS/PULSE'}
environment = {'HOME': str(home), 'HERMES_HOME': str(profile), 'PYTHONPATH': str(runtime),
    'PATH': os.environ['PATH'], 'TZ': 'America/Toronto', 'LANG': 'C.UTF-8',
    'PYTHONDONTWRITEBYTECODE': '1', 'BUN_CONFIG_NO_AUTO_INSTALL': '1',
    'LIFEOS_NOTIFICATION_CHANNEL': 'headless', 'PULSE_PORT': '18837', 'PULSE_URL': 'http://127.0.0.1:18837',
    'LIFEOS_DIR': str(root / 'LIFEOS'), 'LIFEOS_HOOK_SETTINGS': str(root / 'settings.json')}
definition = account_home / '.config/systemd/user'
definition.mkdir(parents=True, mode=0o700, exist_ok=True)
for role, name in units.items():
    lines = ['# ABOUTME: Runs the selected daily Hermes and LifeOS service.',
        '# ABOUTME: Uses the frozen program package and the private selected store.',
        '[Unit]', 'Description=LifeOS daily ' + role, '[Service]', 'Type=simple',
        'UMask=0077', 'KillMode=control-group', 'TimeoutStopSec=' + ('90' if role == 'gateway' else '45'),
        'Restart=on-failure',
        'RestartSec=5', 'WorkingDirectory=' + str(working[role]), 'ExecStart=' + commands[role]]
    lines.extend('Environment="' + key + '=' + value + '"' for key, value in environment.items())
    lines.extend(['[Install]', 'WantedBy=default.target'])
    publish(definition / name, ('\n'.join(lines) + '\n').encode())
publish(evidence / 'environment.json', json.dumps(environment, indent=2).encode())
publish(evidence / 'fresh-review.json', json.dumps(fresh, indent=2).encode())
publish(profile / 'daily-release.json', json.dumps({'version': '0.3.1', 'program_head': manifest['head'],
    'merged_main': '2514eea89c6dcf15aa2d77ebc23634f69f118a10', 'plugin_files': manifest['plugin_files'],
    'hermes_manifest': hermes_manifest, 'lifeos_manifest': lifeos_manifest}, indent=2).encode())
subprocess.run(['systemctl', '--user', 'daemon-reload'], check=True)
# The dashboard authenticates the synthetic owner before ownership activation.
subprocess.run(['systemctl', '--user', 'enable', '--now', units['dashboard']], check=True)
report = {'status': 'INSTALLED_CHANNEL_PENDING', 'hostname': 'lifeos-043-daily-rehearsal', 'address': '192.168.8.246',
    'guest_id': 111, 'guest_type': 'unprivileged LXC', 'profile': str(profile), 'installed': str(root),
    'workspace': str(workspace), 'hermes_runtime': str(runtime), 'names': fresh['names'], 'active_facts': 0,
    'empty_personal_templates': len(fresh['empty_personal_templates']),
    'omitted_personal_templates': len(fresh['omitted_personal_templates']), 'atlas_initialized': True,
    'program_head': manifest['head'], 'merged_main': '2514eea89c6dcf15aa2d77ebc23634f69f118a10',
    'plugin_files_verified': len(manifest['plugin_files']), 'model': selected['model']['default'],
    'model_endpoint': selected['model']['base_url'], 'tier_efforts': {
        name: selected['tiers'][name + '_effort'] for name in ('haiku', 'sonnet', 'opus', 'fable')},
    'units': units, 'dashboard_running': True, 'gateway_running': False, 'pulse_running': False,
    'ownership_enabled': False, 'sharing_enabled': False, 'discord_credentials_present': False,
    'bootstrap_receipt': bootstrap_receipt, 'mount': mount,
    'remaining': ['Off-server whole-guest recovery acceptance', 'Private Discord channel and audience checks',
        'Bot cutover, lasting-memory activation, and scheduled owner services']}
publish(evidence / 'installation.json', json.dumps(report, indent=2).encode())
publish(profile / 'integration-release.json', json.dumps({'format': 1, 'version': '0.3.1', 'commit': manifest['head'], 'package_sha256': hashlib.sha256((account_home / 'releases/0.3.1-9af63325.tgz').read_bytes()).hexdigest(), 'plugin_files': {name.removeprefix('lifeos_hook_bridge/'): digest for name, digest in manifest['plugin_files'].items()}}).encode())
print(json.dumps({key: report[key] for key in ('status', 'address', 'names', 'active_facts',
    'plugin_files_verified', 'empty_personal_templates', 'tier_efforts')}, indent=2))
