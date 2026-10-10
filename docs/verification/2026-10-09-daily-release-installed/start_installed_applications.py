# ABOUTME: Starts three distinct acceptance services for the isolated current package.
# ABOUTME: Binds actual gateway, dashboard, and Pulse processes without transport credentials.
import json
import os
from pathlib import Path
import subprocess

stage = Path('/home/lifeos-hermes/migration/2026-10-09/daily-text-581d76a7')
prepared = json.loads((stage / 'applications-prepared.json').read_text())
profile = Path(prepared['profile'])
installed = Path(prepared['installed'])
home = installed.parent
os.umask(0o077)
os.environ.update(XDG_RUNTIME_DIR='/run/user/1008',
    DBUS_SESSION_BUS_ADDRESS='unix:path=/run/user/1008/bus')
units = {role: 'lifeos-daily-acceptance-' + role + '.service'
    for role in ('gateway', 'dashboard', 'pulse')}
commands = {'gateway': str(stage / 'bin/hermes') + ' gateway run --external-supervisor',
    'dashboard': str(stage / 'bin/hermes') + ' dashboard --isolated --skip-build --no-open --host 127.0.0.1 --port 18819',
    'pulse': '/home/lifeos-hermes/.local/bin/bun --no-install ' + str(installed / 'LIFEOS/PULSE/pulse.ts')}
directories = {'gateway': profile, 'dashboard': home, 'pulse': installed / 'LIFEOS/PULSE'}
definition = Path('/home/lifeos-hermes/.config/systemd/user')
environment = {'HOME': str(home), 'HERMES_HOME': str(profile),
    'PYTHONPATH': str(stage / 'package/hermes'),
    'PATH': str(stage / 'bin') + ':/home/lifeos-hermes/.local/bin:/usr/bin:/bin',
    'TZ': 'America/Toronto', 'LANG': 'C.UTF-8', 'PYTHONDONTWRITEBYTECODE': '1',
    'BUN_CONFIG_NO_AUTO_INSTALL': '1', 'LIFEOS_NOTIFICATION_CHANNEL': 'headless',
    'PULSE_PORT': '18837', 'PULSE_URL': 'http://127.0.0.1:18837',
    'LIFEOS_DIR': str(installed / 'LIFEOS'), 'LIFEOS_HOOK_SETTINGS': str(installed / 'settings.json')}
if prepared['ownership_enabled'] or prepared['sharing_enabled']:
    raise RuntimeError('Initial application acceptance requires a disabled isolated owner profile')
for role, name in units.items():
    target = definition / name
    if target.exists() or target.is_symlink():
        raise RuntimeError('The acceptance service definition already exists')
    lines = ['# ABOUTME: Runs the isolated installed daily application acceptance.',
        '# ABOUTME: Uses no production profile or messaging credential.',
        '[Unit]', 'Description=LifeOS daily acceptance ' + role, '[Service]', 'Type=simple',
        'UMask=0077', 'KillMode=control-group', 'TimeoutStopSec=45',
        'WorkingDirectory=' + str(directories[role]), 'ExecStart=' + commands[role]]
    lines.extend('Environment="' + key + '=' + value + '"' for key, value in environment.items())
    target.write_text('\n'.join(lines) + '\n')
    target.chmod(0o600)
subprocess.run(['systemctl', '--user', 'daemon-reload'], check=True)
subprocess.run(['systemctl', '--user', 'start', units['dashboard'], units['pulse'], units['gateway']], check=True)
(stage / 'application-units.json').write_text(json.dumps({'units': units,
    'working_directories': {role: str(path) for role, path in directories.items()},
    'transport_credentials_loaded': False, 'live_units_changed': False}, indent=2) + '\n')
print(json.dumps({'started': units, 'live_units_changed': False}, indent=2))
