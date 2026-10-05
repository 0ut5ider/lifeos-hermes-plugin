# ABOUTME: Drains bound Hermes and native PULSE services through the owner user systemd manager.
# ABOUTME: Records durable stop intent and restores the original active services after interruption.
from contextlib import contextmanager
import fcntl
import hashlib
import json
import os
from pathlib import Path
import pwd
import re
import stat
import subprocess

from .installation_lock import installation_lock
from .memory_access import MemoryUnavailable
from .memory_backup import _directory, _read
from .memory_transaction import publish


UNITS = {'gateway': 'hermes-gateway.service', 'dashboard': 'hermes-dashboard.service',
         'pulse': 'com.lifeos.pulse.service'}
STOP_ORDER = ('gateway', 'pulse', 'dashboard')
START_ORDER = ('dashboard', 'pulse', 'gateway')
STATES = {'stopping', 'stopped', 'starting', 'active'}
PROPERTIES = ('Id', 'LoadState', 'ActiveState', 'MainPID', 'ControlGroup', 'WorkingDirectory',
    'FragmentPath', 'DropInPaths', 'ExecStart', 'KillMode', 'RootDirectory', 'RootImage', 'NeedDaemonReload')


def _run(*arguments):
    try:
        result = subprocess.run(['systemctl', '--user', *arguments], text=True,
            capture_output=True, timeout=45)
    except (OSError, subprocess.TimeoutExpired) as error:
        raise MemoryUnavailable('The owner service manager does not complete the selected operation') from error
    if result.returncode or result.stderr:
        raise MemoryUnavailable('The owner service manager refuses the selected operation')
    return result.stdout


def _digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def _definition_file(path):
    declared = Path(path)
    if not declared.is_absolute():
        raise MemoryUnavailable('The profile service definition needs an absolute file')
    physical = declared.resolve(strict=True)
    descriptor = os.open(physical, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    with os.fdopen(descriptor, 'rb') as stream:
        before = os.fstat(stream.fileno())
        if (not stat.S_ISREG(before.st_mode) or before.st_uid not in {0, os.getuid()}
                or before.st_mode & 0o022 or before.st_size > 256 * 1024):
            raise MemoryUnavailable('The service definition needs a bounded trusted owner file')
        data = stream.read(256 * 1024 + 1)
        after = os.fstat(stream.fileno())
        stamp = lambda value: (value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns, value.st_mode)
        if (len(data) > 256 * 1024 or stamp(before) != stamp(after) or stamp(after) != stamp(physical.stat())
                or declared.resolve() != physical):
            raise MemoryUnavailable('The profile service definition changes during inspection')
    return {'declared': str(declared), 'physical': str(physical), 'sha256': hashlib.sha256(data).hexdigest()}


class ProfileServices:
    def __init__(self, profile, installed, *, units=None, installation_lease=None):
        self.profile, self.installed = Path(profile).absolute(), Path(installed).absolute()
        self.installation_lease = installation_lease
        try:
            self.physical_root = self.installed.resolve(strict=True)
        except (OSError, RuntimeError) as error:
            raise MemoryUnavailable('The installed profile service root is unavailable') from error
        if not self.physical_root.is_dir():
            raise MemoryUnavailable('The installed profile services require a program directory')
        if units is not None and not isinstance(units, dict):
            raise MemoryUnavailable('Profile services require a fixed role-to-service mapping')
        self.units = dict(UNITS if units is None else units)
        if (set(self.units) != set(UNITS)
                or any(not isinstance(unit, str) or re.fullmatch('[a-zA-Z0-9_.-]+\\.service', unit) is None
                       for unit in self.units.values()) or len(set(self.units.values())) != len(UNITS)):
            raise MemoryUnavailable('Profile services require three distinct fixed service bindings')
        self.state = self.profile / '.lifeos-services'
        self.journal = self.state / 'operation.json'
        self.directories = {'gateway': self.profile, 'dashboard': self.installed.parent.resolve(),
            'pulse': self.physical_root / 'LIFEOS/PULSE'}

    @contextmanager
    def _lock(self):
        with installation_lock(self.profile, lease=self.installation_lease):
            self.state.mkdir(mode=0o700, exist_ok=True)
            _directory(self.state, private=True)
            descriptor = os.open(self.state / 'lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
            try:
                info = os.fstat(descriptor)
                if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
                    raise MemoryUnavailable('The profile service lock requires private owner permissions')
                fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
                yield
            finally:
                os.close(descriptor)

    def _publish(self, document):
        publish(self.journal, (json.dumps(document, sort_keys=True, indent=2) + '\n').encode())

    def _load(self):
        if not self.journal.exists() and not self.journal.is_symlink():
            return None
        data, _ = _read(self.journal, private=True)
        try:
            document = json.loads(data)
        except (ValueError, UnicodeError, RecursionError) as error:
            raise MemoryUnavailable('The profile service journal has invalid content') from error
        if (not isinstance(document, dict) or set(document) != {'version', 'profile', 'installed', 'installed_physical', 'state', 'services'}
                or type(document['version']) is not int or document['version'] != 1
                or document['profile'] != str(self.profile) or document['installed'] != str(self.installed)
                or document['installed_physical'] != str(self.physical_root)
                or not isinstance(document['state'], str) or document['state'] not in STATES
                or not isinstance(document['services'], dict) or set(document['services']) != set(UNITS)):
            raise MemoryUnavailable('The profile service journal belongs to another profile or has invalid metadata')
        for role, item in document['services'].items():
            if (not isinstance(item, dict) or set(item) != {'unit', 'definition', 'active', 'control_group'}
                    or item['unit'] != self.units[role] or type(item['active']) is not bool
                    or not isinstance(item['definition'], str)
                    or re.fullmatch('[0-9a-f]{64}', item['definition']) is None):
                raise MemoryUnavailable('The profile service journal has invalid service bindings')
            self._group(item['control_group'])
        return document

    @staticmethod
    def _group(value):
        if not isinstance(value, str):
            raise MemoryUnavailable('A profile service has an invalid control group')
        if value == '':
            return None
        path = Path(value)
        namespace = f'/user.slice/user-{os.getuid()}.slice/user@{os.getuid()}.service/'
        if (not value.startswith(namespace) or '..' in path.parts or '.' in path.parts
                or '\x00' in value or str(path) != value):
            raise MemoryUnavailable('A profile service has an unreviewed control group')
        return Path('/sys/fs/cgroup') / value.lstrip('/')

    def _inspect(self, role):
        if self.installed.resolve() != self.physical_root:
            raise MemoryUnavailable('The installed profile service root alias changes during the operation')
        output = _run('show', self.units[role], '--property=' + ','.join(PROPERTIES), '--no-pager')
        values = {}
        for line in output.splitlines():
            if '=' not in line:
                raise MemoryUnavailable('The profile service manager returns unsupported properties')
            key, value = line.split('=', 1)
            if key in values:
                raise MemoryUnavailable('The profile service manager repeats a property')
            values[key] = value
        if (set(values) != set(PROPERTIES) or values['Id'] != self.units[role] or values['LoadState'] != 'loaded'
                or values['NeedDaemonReload'] != 'no' or values['RootDirectory'] or values['RootImage']
                or values['KillMode'] not in {'mixed', 'control-group'}
                or not values['MainPID'].isdigit()):
            raise MemoryUnavailable('The profile service has unreviewed program or process properties')
        working = values['WorkingDirectory'].removeprefix('!')
        if working == '~':
            working = pwd.getpwuid(os.getuid()).pw_dir
        expected = self.directories[role]
        if (not Path(working).is_absolute() or Path(working).resolve() != expected
                or expected.resolve() != expected or not expected.is_dir()):
            raise MemoryUnavailable('The service working directory belongs to another profile')
        drop_ins = values['DropInPaths'].split()
        if len(drop_ins) > 128 or any(any(character in path for character in ('\\', '\"', "'")) for path in drop_ins):
            raise MemoryUnavailable('Escaped profile service definition paths require review')
        definition = {key: values[key] for key in PROPERTIES
            if key not in {'ActiveState', 'MainPID', 'ControlGroup', 'ExecStart', 'DropInPaths'}}
        definition['files'] = [_definition_file(path) for path in (values['FragmentPath'], *drop_ins)]
        self._group(values['ControlGroup'])
        return values, _digest(definition)

    def _check_definition(self, document, role):
        values, definition = self._inspect(role)
        if definition != document['services'][role]['definition']:
            raise MemoryUnavailable('The bound profile service definition changes during recovery')
        return values

    def _empty(self, document, role):
        values = self._check_definition(document, role)
        if values['ActiveState'] not in {'inactive', 'failed'} or values['MainPID'] != '0':
            raise MemoryUnavailable('The profile service still has an active process')
        groups = {values['ControlGroup'], document['services'][role]['control_group']}
        for name in groups:
            group = self._group(name)
            if group is None:
                continue
            events = group / 'cgroup.events'
            try:
                data = events.read_text()
            except FileNotFoundError:
                if group.exists():
                    raise MemoryUnavailable('The profile service control group has no verifiable process state')
                continue
            if 'populated 0' not in data.splitlines():
                raise MemoryUnavailable('The profile service still contains child writers')

    def _drain_unit(self, document, role):
        values = self._check_definition(document, role)
        if values['ActiveState'] not in {'inactive', 'failed'} or values['MainPID'] != '0':
            _run('stop', self.units[role])
        self._empty(document, role)

    def _drain(self, document):
        for role in STOP_ORDER:
            self._drain_unit(document, role)
        for role in STOP_ORDER:
            self._empty(document, role)
        document['state'] = 'stopped'
        self._publish(document)

    def drain(self):
        with self._lock():
            previous = self._load()
            if previous is not None and previous['state'] != 'active':
                raise MemoryUnavailable('Recover the interrupted profile service operation before another drain')
            services = {}
            for role in STOP_ORDER:
                values, definition = self._inspect(role)
                if values['ActiveState'] not in {'active', 'inactive'}:
                    raise MemoryUnavailable('Profile services require a stable active or inactive state before draining')
                if values['ActiveState'] == 'active' and int(values['MainPID']) == 0:
                    raise MemoryUnavailable('The active profile service has no verifiable main process')
                services[role] = {'unit': self.units[role], 'definition': definition,
                    'active': values['ActiveState'] == 'active', 'control_group': values['ControlGroup']}
            document = {'version': 1, 'profile': str(self.profile), 'installed': str(self.installed),
                'installed_physical': str(self.physical_root),
                'state': 'stopping', 'services': services}
            self._publish(document)
            self._drain(document)
            return {'state': 'stopped', 'services_stopped': list(STOP_ORDER), 'owner_turn_verified': False}

    def verify_stopped(self):
        with self._lock():
            document = self._load()
            if document is None or document['state'] != 'stopped':
                raise MemoryUnavailable('The selected profile services have no completed drain')
            for role in STOP_ORDER:
                self._empty(document, role)
            return {'state': 'stopped', 'owner_turn_verified': False}

    def resume(self):
        with self._lock():
            document = self._load()
            if document is None:
                raise MemoryUnavailable('The selected profile services have no recovery state')
            if document['state'] == 'stopping':
                self._drain(document)
            for role in START_ORDER:
                self._check_definition(document, role)
            document['state'] = 'starting'
            self._publish(document)
            started = []
            for role in START_ORDER:
                self._check_definition(document, role)
                if document['services'][role]['active']:
                    _run('start', self.units[role])
                    started.append(role)
            for role in START_ORDER:
                values = self._check_definition(document, role)
                if document['services'][role]['active']:
                    if values['ActiveState'] != 'active' or int(values['MainPID']) == 0:
                        raise MemoryUnavailable('The selected profile service does not restart')
                else:
                    self._empty(document, role)
            document['state'] = 'active'
            self._publish(document)
            return {'state': 'active', 'services_started': started, 'owner_turn_verified': False}

    def status(self):
        with self._lock():
            document = self._load()
            state = document['state'] if document is not None else 'none'
            return {'state': state, 'recovery_required': state in {'stopping', 'stopped', 'starting'},
                'owner_turn_verified': False}
