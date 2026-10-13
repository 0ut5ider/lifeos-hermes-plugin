# ABOUTME: Measures effective systemd Environment values with a supported literal percent profile path.
# ABOUTME: Uses one inactive task-owned unit and the real dashboard binding parser without starting a dashboard.
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
from uuid import uuid4

from optional.lifeos_release_manager.release_services import _quoted, _service_paths, dashboard_binding


def command(*args):
    result = subprocess.run(args, capture_output=True, text=True, timeout=20)
    if result.returncode or result.stderr:
        raise RuntimeError(result.stdout + result.stderr)
    return result.stdout


with tempfile.TemporaryDirectory(prefix='pr18-effective-environment-') as folder:
    home = Path(folder) / 'literal%%name'
    home.mkdir(mode=0o700)
    profile = home / '.hermes'
    profile.mkdir(mode=0o700)
    _service_paths(home, profile, home / '.claude')
    launcher = home / '.local/bin/hermes'
    launcher.parent.mkdir(parents=True)
    launcher.write_text('#!/bin/sh\nexit 0\n')
    launcher.chmod(0o700)
    unit = 'pr18-review-percent-' + uuid4().hex + '.service'
    definition = Path(folder) / unit
    definition.write_text('[Unit]\nDescription=PR18 isolated inactive environment probe\n[Service]\n'
        'Environment=' + _quoted('HERMES_HOME=' + str(profile)) + '\n'
        'ExecStart=' + _quoted(launcher, command=True) + ' dashboard --isolated --no-open\n')
    linked = False
    try:
        command('systemctl', '--user', '--quiet', 'link', '--runtime', str(definition))
        linked = True
        command('systemctl', '--user', 'daemon-reload')
        properties = command('systemctl', '--user', 'show', unit,
            '--property=MainPID,Environment,EnvironmentFiles,ExecStart', '--no-pager')
        values = dict(line.split('=', 1) for line in properties.splitlines() if '=' in line)
        module = SimpleNamespace(UNITS={'dashboard': unit}, _run=lambda *args: command('systemctl', '--user', *args))
        try:
            binding = dashboard_binding(module, profile, values)
            result = {'accepted': True, 'binding': binding}
        except ValueError as error:
            result = {'accepted': False, 'exception': type(error).__name__, 'error': str(error)}
        result.update(profile=str(profile), effective_environment=values['Environment'],
            main_pid=values['MainPID'], supported_service_path=True,
            unit_definition=definition.read_text(), limit='Real inactive temporary unit and effective environment; no service process starts.')
        Path(__file__).with_name('environment-probe.json').write_text(json.dumps(result, indent=2) + '\n')
        print(json.dumps(result, indent=2))
    finally:
        if linked:
            command('systemctl', '--user', '--quiet', 'disable', '--runtime', unit)
            command('systemctl', '--user', 'daemon-reload')
