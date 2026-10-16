# ABOUTME: Records safe release, model, credential-file digest, and service HOME baselines before promotion.
# ABOUTME: Reads installation configuration only and excludes personal memory records and credential values.
import hashlib
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
from ruamel.yaml import YAML

home = Path('/home/lifeos-hermes')
profile = home / '.hermes'
os.environ.update(HERMES_HOME=str(profile), XDG_RUNTIME_DIR='/run/user/' + str(os.getuid()),
    DBUS_SESSION_BUS_ADDRESS='unix:path=/run/user/' + str(os.getuid()) + '/bus',
    PATH=str(home / '.local/bin') + ':/usr/bin:/bin')
config = YAML(typ='safe').load((profile / 'config.yaml').read_bytes())
settings = config.get('plugins', {}).get('entries', {}).get('lifeos-hook-bridge', {}).get('settings', {})
selection = {'model': config.get('model'), 'tiers': {key: value for key, value in settings.items()
    if key.startswith(('haiku', 'sonnet', 'opus', 'fable', 'pinned'))}}
model_hash = hashlib.sha256(json.dumps(selection, sort_keys=True).encode()).hexdigest()
assert config['model']['default'] == 'flashnext-w4a16-fp8ple'
assert all(settings.get(name + '_model') == 'flashnext-w4a16-fp8ple' for name in ('haiku', 'sonnet', 'opus', 'fable'))
services = {}
for name in ('hermes-gateway.service', 'hermes-dashboard.service', 'com.lifeos.pulse.service'):
    result = subprocess.run(['systemctl', '--user', 'show', name,
        '--property=ActiveState,SubState,Environment,MainPID', '--no-pager'], text=True, capture_output=True, check=True)
    values = dict(line.split('=', 1) for line in result.stdout.splitlines() if '=' in line)
    explicit = dict(value.split('=', 1) for value in shlex.split(values['Environment']))
    environment = dict(value.split('=', 1) for value in
        Path('/proc/' + values['MainPID'] + '/environ').read_bytes().decode().split('\0') if '=' in value)
    assert values['ActiveState'] == 'active' and values['SubState'] == 'running'
    assert environment['HERMES_HOME'] == str(profile)
    assert explicit.get('HOME', environment['HOME']) == environment['HOME']
    services[name] = {'home': environment['HOME'], 'profile': environment['HERMES_HOME'], 'active': True,
                      'explicit_home': explicit.get('HOME')}
version = subprocess.run([str(home / '.local/bin/hermes'), 'lifeos-version'],
    text=True, capture_output=True, check=True, timeout=90)
active = json.loads(version.stdout)['active']
assert active['verification'] == 'verified'
assert active['version'] == '0.5.0' and active['commit'] == '04efe633296eb2b1a1d95561ca6d3e9516cd47dc'
assert active['package_sha256'] == 'a6dd0e11b8fb1b5ae30345be20c955db02728839f7bc907f60a70944ad392813'
report = {'status': 'PASS', 'server': sys.argv[1], 'prior_identity': active, 'services': services,
    'model_selection_sha256': model_hash,
    'configuration_semantic_sha256': hashlib.sha256(json.dumps(config, sort_keys=True, separators=(',', ':'), default=str).encode()).hexdigest(),
    'configuration_file_sha256': {name: hashlib.sha256((profile / name).read_bytes()).hexdigest()
        for name in ('.env', 'lifeos-memory.json')}, 'personal_records_read': False,
    'credential_values_exported': False}
print(json.dumps(report, indent=2))
