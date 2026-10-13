# ABOUTME: Stages fixed inactive user services for the first complete integration installation.
# ABOUTME: Binds the stock dashboard writer to its owner service before publishing programs.
from pathlib import Path
import inspect
import os
import re
import shlex

from .release_catalog import ReleaseRejected
from .release_programs import fingerprint, publish


class FirstInstallationUnavailable(ReleaseRejected):
    def __init__(self):
        super().__init__('This release does not support managed dashboard first installation. Choose a qualified release with first-install service support.')


def require_fresh_services(current):
    if 'first_installation' not in inspect.signature(current.memory_module('profile_services').ProfileServices).parameters:
        raise FirstInstallationUnavailable()


def _quoted(value, *, command=False):
    value = str(value)
    if any(ord(character) < 32 for character in value):
        raise ReleaseRejected('Service paths require bounded physical account names')
    value = value.replace('\\', '\\\\').replace('"', '\\"').replace('%', '%%')
    return '"' + (value.replace('$', '$$') if command else value) + '"'


def _service_paths(home, profile, installed):
    for path in (home, profile, installed):
        if (not path.is_absolute() or path.resolve() != path
                or any(character.isspace() or ord(character) < 32 or character in '\\"\'$;}' for character in str(path))):
            raise ReleaseRejected('Managed service paths require physical names without whitespace, dollar signs, quotes, backslashes, semicolons, or closing braces')


def service_files(request, generated):
    home, profile, installed = (Path(request[key]) for key in ('account_home', 'profile', 'installed'))
    _service_paths(home, profile, installed)
    definitions = {
        'hermes-gateway.service': (profile, [home / '.local/bin/hermes', 'gateway', 'run', '--external-supervisor']),
        'hermes-dashboard.service': (installed.parent, [home / '.local/bin/hermes', 'dashboard', '--isolated', '--no-open']),
        'com.lifeos.pulse.service': (installed / 'LIFEOS/PULSE',
            [home / '.local/bin/bun', '--no-install', installed / 'LIFEOS/PULSE/pulse.ts']),
    }
    files = {}
    for name, (working, command) in definitions.items():
        target = home / '.config/systemd/user' / name
        existing = fingerprint(target)
        if existing is not None:
            if existing['type'] != 'file':
                raise ReleaseRejected('Existing integration services require regular owner definitions')
            files[target] = target
            continue
        source = generated / name
        publish(source, ('# ABOUTME: Defines a reviewed integration service without enabling it.\n'
            '# ABOUTME: Selects fixed account launchers and the installed profile.\n'
            '[Unit]\nDescription=LifeOS integration ' + name + '\n[Service]\nType=simple\n'
            'WorkingDirectory=' + str(working).replace('%', '%%') + '\n'
            'Environment=' + _quoted('HERMES_HOME=' + str(profile)) + '\n'
            'Environment=' + _quoted('PATH=' + str(home / '.local/bin') + ':/usr/local/bin:/usr/bin:/bin') + '\n'
            'Environment=PYTHONDONTWRITEBYTECODE=1\nUMask=0077\n'
            'ExecStart=' + ' '.join(_quoted(value, command=True) for value in command) + '\n'
            'KillMode=control-group\nTimeoutStopSec=45s\nRestart=on-failure\n'
            '[Install]\nWantedBy=default.target\n').encode())
        files[target] = source
    return files


def fresh_services(current, profile, installed, *, installation_lease=None):
    require_fresh_services(current)
    return current.memory_module('profile_services').ProfileServices(profile, installed,
        installation_lease=installation_lease, first_installation=True)


def fresh_preview(current, profile, installed, *, installation_lease=None):
    _service_paths(Path.home(), profile, installed)
    services = fresh_services(current, profile, installed, installation_lease=installation_lease)
    preview = services.preview()
    values, _ = services._inspect('dashboard')
    match = re.search(r'\bpath=([^ ;}]+)', values['ExecStart'])
    launcher = Path(match.group(1)) if match is not None else None
    if (launcher != Path.home() / '.local/bin/hermes' or fingerprint(launcher) is None or not launcher.is_file()
            or values['FragmentPath'] != str(Path.home() / '.config/systemd/user/hermes-dashboard.service')
            or values['DropInPaths']):
        raise ReleaseRejected('Start the owner dashboard service with the account Hermes launcher before installation')
    check_dashboard_writers(profile, values['ControlGroup'])
    module = current.memory_module('profile_services')
    for role in ('gateway', 'pulse'):
        text = module._run('show', module.UNITS[role],
            '--property=LoadState,ActiveState,WorkingDirectory,FragmentPath,DropInPaths,KillMode,NeedDaemonReload,RootDirectory,RootImage,ExecStart', '--no-pager')
        properties = dict(line.split('=', 1) for line in text.splitlines() if '=' in line)
        if properties.get('LoadState') == 'not-found':
            continue
        expected = profile if role == 'gateway' else installed / 'LIFEOS/PULSE'
        target = Path.home() / '.config/systemd/user' / module.UNITS[role]
        executable = Path.home() / '.local/bin' / ('hermes' if role == 'gateway' else 'bun')
        match = re.search(r'\bpath=([^ ;}]+)', properties.get('ExecStart', ''))
        arguments = ('gateway run --external-supervisor' if role == 'gateway'
                     else '--no-install ' + str(installed / 'LIFEOS/PULSE/pulse.ts'))
        if (properties.get('LoadState') != 'loaded' or properties.get('ActiveState') != 'inactive'
                or Path(properties.get('WorkingDirectory', '')).resolve() != expected
                or properties.get('FragmentPath') != str(target) or properties.get('DropInPaths')
                or properties.get('NeedDaemonReload') != 'no' or properties.get('RootDirectory') or properties.get('RootImage')
                or properties.get('KillMode') not in {'mixed', 'control-group'}
                or match is None or match.group(1) != str(executable)
                or 'argv[]=' + str(executable) + ' ' + arguments + ' ;' not in properties['ExecStart']):
            raise ReleaseRejected('Fresh installation preserves an existing service from another deployment')
    return preview


def check_dashboard_writers(profile, group=''):
    # Procfs inspection fails closed. A foreground backend cannot be drained by an inactive unit.
    from hermes_cli.dashboard_procs import _hermes_home_for_pid
    from hermes_cli.update_cmd_windows import _hermes_holder_subcommand
    for process in Path('/proc').iterdir():
        if not process.name.isdecimal():
            continue
        try:
            if process.stat().st_uid != os.getuid():
                continue
            arguments = [value.decode() for value in (process / 'cmdline').read_bytes().split(b'\0') if value]
            if _hermes_holder_subcommand(shlex.join(arguments)) not in {'dashboard', 'serve'}:
                continue
            owner = _hermes_home_for_pid(int(process.name))
            if owner is None:
                raise ReleaseRejected('The running dashboard profile identity is unavailable')
            if Path(owner).resolve() != profile:
                continue
            groups = (process / 'cgroup').read_text().splitlines()
            if not group or '0::' + group not in groups:
                raise ReleaseRejected('Run this profile dashboard through its owner user service before installation')
        except FileNotFoundError:
            continue


def verify_installed_services(current, profile, installed, *, installation_lease=None):
    module = current.memory_module('profile_services')
    module._run('daemon-reload')
    module.ProfileServices(profile, installed, installation_lease=installation_lease).preview()
