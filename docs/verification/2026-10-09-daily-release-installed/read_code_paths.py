# ABOUTME: Discovers service executable paths and selected operational environment fields.
# ABOUTME: Excludes credentials and memory records from the installed release baseline.
import json
from pathlib import Path
import subprocess
import re

result = {}
for name in ('hermes-gateway.service', 'hermes-dashboard.service', 'com.lifeos.pulse.service'):
    args = ['runuser', '-u', 'lifeos-hermes', '--', 'env', 'XDG_RUNTIME_DIR=/run/user/1008',
        'DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1008/bus', 'systemctl', '--user', 'show', name,
        '--property=MainPID,ExecStart']
    output = subprocess.check_output(args, text=True)
    entries = dict(line.split('=', 1) for line in output.splitlines() if '=' in line)
    pid = int(entries['MainPID'])
    command = Path(f'/proc/{pid}/cmdline').read_bytes().decode().split('\0')
    environment = Path(f'/proc/{pid}/environ').read_bytes().decode().split('\0')
    result[name] = {'interpreter': command[0],
        'programs': [value for value in command[1:] if value.endswith(('.py', '.ts', '.js'))],
        'working_directory': str(Path(f'/proc/{pid}/cwd').resolve()),
        'environment': {key: value for item in environment if '=' in item
            for key, value in [item.split('=', 1)] if key in {'HOME', 'HERMES_HOME', 'LIFEOS_DIR', 'PATH', 'PYTHONPATH', 'PYTHONHOME', 'VIRTUAL_ENV'}}}
print(json.dumps(result, indent=2))
