# ABOUTME: Records operational development service and code paths without reading memory records.
# ABOUTME: Keeps tokens and transport credentials out of release acceptance evidence.
import json
import os
from pathlib import Path
import subprocess

home = Path('/home/lifeos-hermes')
profile = home / '.hermes'
result = {'host': subprocess.check_output(['hostname'], text=True).strip(),
    'home': str(home), 'profile': str(profile), 'native_link': str((home / '.claude').resolve()),
    'services': {}, 'home_directories': sorted(path.name for path in home.iterdir() if path.is_dir())}
configuration = json.loads((profile / 'lifeos-memory.json').read_text())
result['memory_configuration'] = {key: configuration.get(key) for key in ('version', 'root', 'ownership_enabled', 'sharing_enabled')}
result['plugin_directory'] = {'path': str(profile / 'plugins/lifeos-hook-bridge'),
    'is_symlink': (profile / 'plugins/lifeos-hook-bridge').is_symlink()}
for name in ('hermes-gateway.service', 'hermes-dashboard.service', 'com.lifeos.pulse.service'):
    args = ['runuser', '-u', 'lifeos-hermes', '--', 'env', 'XDG_RUNTIME_DIR=/run/user/1008',
        'DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1008/bus', 'systemctl', '--user', 'show', name,
        '--property=ActiveState,SubState,WorkingDirectory,UMask,FragmentPath']
    output = subprocess.run(args, capture_output=True, text=True, check=True)
    result['services'][name] = dict(line.split('=', 1) for line in output.stdout.splitlines() if '=' in line)
print(json.dumps(result, indent=2))
