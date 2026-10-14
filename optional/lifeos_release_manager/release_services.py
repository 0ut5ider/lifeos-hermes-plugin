# ABOUTME: Stages fixed inactive user services for the first complete integration installation.
# ABOUTME: Binds the stock dashboard writer to its owner service before publishing programs.
from pathlib import Path
import inspect
import os
import re
import shlex

from .release_catalog import ReleaseRejected
from .release_accounts import account_home
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
    profile = Path(profile).absolute()
    module = current.memory_module('profile_services')
    class DashboardServices(module.ProfileServices):
        def _inspect(self, role):
            values, definition = super()._inspect(role)
            binding = dashboard_binding(module, profile, values)
            return values, module._digest({'definition': definition, 'dashboard': binding})
    return DashboardServices(profile, installed,
        installation_lease=installation_lease, first_installation=True)


def dashboard_command(arguments):
    from hermes_cli.update_cmd_windows import _hermes_holder_subcommand
    # The pinned Hermes bundle enters main in this process; other inline source keeps trailing arguments as data.
    bundled = "import os, site, sys; sys.argv[0]='hermes'; site.addsitedir(os.environ['HERMES_SITE']); from hermes_cli.main import main; sys.exit(main())"
    if len(arguments) >= 5 and arguments[1:4] == ['-P', '-c', bundled]:
        arguments = ['hermes', *arguments[4:]]
    return _hermes_holder_subcommand(shlex.join(arguments))


def dashboard_binding(module, profile, values):
    from hermes_cli.dashboard_procs import _hermes_home_for_pid, _profile_flag_value
    from hermes_cli.profiles import get_active_profile, normalize_profile_name, profile_root_for_env_home
    from .release_operation import process_stamp
    pid = int(values['MainPID'])
    if pid:
        try:
            stamp = process_stamp(pid)
            process = Path('/proc') / str(pid)
            arguments = [value.decode() for value in (process / 'cmdline').read_bytes().split(b'\0') if value]
            owner = _hermes_home_for_pid(pid)
            valid_process = (process.stat().st_uid == os.getuid()
                and stamp is not None and process_stamp(pid) == stamp
                and dashboard_command(arguments) in {'dashboard', 'serve'})
        except (OSError, UnicodeError, ValueError) as error:
            raise ReleaseRejected('The dashboard process profile identity is unavailable') from error
        if not valid_process or owner is None or Path(owner).resolve() != profile:
            raise ReleaseRejected('The active dashboard process belongs to another profile or command')
    configured = re.search(r'\bargv\[\]=(.*?) ;', values['ExecStart'])
    try:
        arguments = shlex.split(configured.group(1)) if configured is not None else []
        properties = dict(line.split('=', 1) for line in module._run('show', module.UNITS['dashboard'],
            '--property=Environment,EnvironmentFiles', '--no-pager').splitlines() if '=' in line)
        environment = dict(value.split('=', 1) for value in shlex.split(properties['Environment']))
    except (KeyError, ValueError) as error:
        raise ReleaseRejected('The dashboard service profile binding is unavailable') from error
    command = dashboard_command(arguments)
    declared = environment.get('HERMES_HOME', '')
    if (command not in {'dashboard', 'serve'} or not set(properties) <= {'Environment', 'EnvironmentFiles'}
            or properties.get('EnvironmentFiles') or not declared or Path(declared) != profile
            or Path(declared).resolve() != profile):
        raise ReleaseRejected('The dashboard service requires an explicit selected profile and dashboard command')
    explicit = _profile_flag_value(arguments)
    if explicit is not None:
        root = profile_root_for_env_home(declared, profile)
        name = normalize_profile_name(explicit)
        selected = root if name == 'default' else root / 'profiles' / name
        if selected != profile:
            raise ReleaseRejected('The dashboard command selects another profile')
    elif (profile.parent.name != 'profiles' and environment.get('HERMES_UPDATE_POST_SWAP') != '1'
            and not any(environment.get(key) for key in ('HERMES_SUPERVISED_CHILD', 'HERMES_S6_SUPERVISED_CHILD',
                'HERMES_GATEWAY_EXTERNAL_SUPERVISOR'))):
        if normalize_profile_name(get_active_profile(profile)) != 'default':
            raise ReleaseRejected('The dashboard service selects another active profile')
    return {'profile': str(profile), 'command': command}


def fresh_preview(current, profile, installed, *, installation_lease=None):
    home = account_home(profile)
    _service_paths(home, profile, installed)
    services = fresh_services(current, profile, installed, installation_lease=installation_lease)
    preview = services.preview()
    values, _ = services._inspect('dashboard')
    match = re.search(r'\bpath=([^ ;}]+)', values['ExecStart'])
    launcher = Path(match.group(1)) if match is not None else None
    if (launcher != home / '.local/bin/hermes' or fingerprint(launcher) is None or not launcher.is_file()
            or values['FragmentPath'] != str(home / '.config/systemd/user/hermes-dashboard.service')
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
        target = home / '.config/systemd/user' / module.UNITS[role]
        executable = home / '.local/bin' / ('hermes' if role == 'gateway' else 'bun')
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
    for process in Path('/proc').iterdir():
        if not process.name.isdecimal():
            continue
        try:
            if process.stat().st_uid != os.getuid():
                continue
            arguments = [value.decode() for value in (process / 'cmdline').read_bytes().split(b'\0') if value]
            if dashboard_command(arguments) not in {'dashboard', 'serve'}:
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
