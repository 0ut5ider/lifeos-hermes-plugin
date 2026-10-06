# ABOUTME: Publishes staged native mount files through a private durable journal.
# ABOUTME: Recovers interrupted publication and refuses to overwrite later profile edits.
from contextlib import contextmanager
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
from uuid import uuid4

from .memory_transaction import publish
from .native_output import failure_message


FILES = ('config.yaml', 'SOUL.md', '.env', 'plugins/lifeos/__init__.py',
         'plugins/lifeos/guard.py', 'plugins/lifeos/plugin.yaml', 'plugins/lifeos/policy.json')
PENDING = {'prepared', 'applying', 'restoring'}
LIMIT = 4 * 1024 * 1024


class MountError(RuntimeError):
    pass


def _read(path):
    path = Path(path).absolute()
    if path.parent.resolve() != path.parent:
        raise MountError('A mount target changes its physical path')
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    except FileNotFoundError:
        return None, None
    except OSError as error:
        raise MountError('A mount target is unavailable') from error
    with os.fdopen(descriptor, 'rb') as stream:
        before = os.fstat(stream.fileno())
        if not stat.S_ISREG(before.st_mode) or before.st_uid != os.getuid() or before.st_size > LIMIT:
            raise MountError('Mount files must be bounded regular owner files')
        data = stream.read(LIMIT + 1)
        after = os.fstat(stream.fileno())
        current = path.lstat()
        stamp = lambda info: (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns)
        if len(data) > LIMIT or stamp(before) != stamp(after) or stamp(after) != stamp(current):
            raise MountError('A mount target changed during collection')
    return data, {'digest': hashlib.sha256(data).hexdigest(), 'mode': stat.S_IMODE(after.st_mode)}


def _json(path, value):
    publish(path, (json.dumps(value, sort_keys=True, indent=2) + '\n').encode())


def _sync_directory(path):
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _run(command, installed, environment, label):
    result = subprocess.run(command, cwd=installed.parent, env=environment, text=True,
                            capture_output=True, timeout=120)
    if result.returncode:
        raise MountError(failure_message(f'LifeOS {label}', result))
    return result.stdout


def _check_prepared_config(installed, environment, stage):
    from hermes_cli import _launchers
    source = Path(_launchers.__file__).resolve().parents[1]
    # Bootstrap the installed dependency environment before selecting the prepared config.
    code = ('from argparse import Namespace\n'
            'from hermes_constants import set_hermes_home_override\n'
            'set_hermes_home_override(sys.argv[1])\n'
            'from hermes_cli.config import config_command\n'
            'config_command(Namespace(config_command="check"))\n')
    command = _launchers.runtime_command(source, [str(stage)], code=code, python=sys.executable)
    return _run(command, installed, environment, 'Hermes prepared config check')


class MountTransaction:
    def __init__(self, installed, profile, baseline=None):
        self.installed, self.profile = Path(installed).absolute(), Path(profile).absolute()
        self.baseline = Path(baseline).absolute() if baseline is not None else None
        self.state = self.profile / '.lifeos-mount'
        self.journal = self.state / 'operation.json'

    @contextmanager
    def _lock(self):
        info = self.profile.stat()
        if self.profile.resolve() != self.profile or info.st_uid != os.getuid() or info.st_mode & 0o022:
            raise MountError('Mounting requires the installed owner profile')
        self.state.mkdir(mode=0o700, exist_ok=True)
        info = self.state.lstat()
        if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
            raise MountError('Mount state requires private owner permissions')
        descriptor = os.open(self.state / 'lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        try:
            info = os.fstat(descriptor)
            if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
                raise MountError('The mount lock requires private owner permissions')
            try:
                fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as error:
                raise MountError('Another mount operation is running') from error
            self._prune_snapshots()
            try:
                yield
            finally:
                self._prune_snapshots()
        finally:
            os.close(descriptor)

    def _manifest(self):
        data, info = _read(self.journal)
        if data is None:
            return None
        if info['mode'] & 0o077:
            raise MountError('The mount journal requires private owner permissions')
        value = json.loads(data)
        if (not isinstance(value, dict) or value.get('version') != 1 or value.get('profile') != str(self.profile)
                or value.get('state') not in PENDING | {'committed', 'rolled_back'}):
            raise MountError('The mount journal belongs to another installation or is invalid')
        if (value.get('installed') != str(self.installed)
                or value.get('baseline') != (str(self.baseline) if self.baseline is not None else None)):
            if value['state'] in PENDING:
                raise MountError('The mount journal belongs to another installation or is invalid')
            # A finished operation of the previously selected LifeOS home leaves nothing to recover.
            return None
        directory = Path(value['snapshot'])
        if (directory.parent != self.state or directory.resolve() != directory or directory.is_symlink()
                or len(directory.name) != 32 or any(letter not in '0123456789abcdef' for letter in directory.name)):
            raise MountError('The mount snapshot is invalid')
        try:
            info = directory.stat()
        except FileNotFoundError:
            if value['state'] in PENDING:
                raise MountError('The mount recovery snapshot is missing')
        else:
            if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
                raise MountError('The mount snapshot requires private owner permissions')
        allowed = {str(self.profile / name) for name in FILES}
        if self.baseline is not None:
            allowed.add(str(self.baseline))
        entries = value.get('entries')
        if (not isinstance(entries, list) or not entries or len(entries) > len(FILES) + 1
                or any(not isinstance(entry, dict) or set(entry) != {'target', 'before', 'after', 'copy'}
                       or entry['target'] not in allowed or type(entry['copy']) is not int
                       or entry['copy'] != index for index, entry in enumerate(entries))
                or len({entry['target'] for entry in entries}) != len(entries)):
            raise MountError('The mount snapshot targets are invalid')
        for entry in entries:
            for key in ('before', 'after'):
                metadata = entry[key]
                if metadata is None and key == 'before':
                    continue
                if (not isinstance(metadata, dict) or set(metadata) != {'digest', 'mode'}
                        or not isinstance(metadata['digest'], str) or len(metadata['digest']) != 64
                        or any(letter not in '0123456789abcdef' for letter in metadata['digest'])
                        or type(metadata['mode']) is not int or not 0 <= metadata['mode'] <= 0o777):
                    raise MountError('The mount snapshot metadata is invalid')
        if (not isinstance(value.get('absent_directories'), list)
                or any(name not in ('plugins', 'plugins/lifeos', 'workspace')
                       for name in value['absent_directories'])):
            raise MountError('The mount directory metadata is invalid')
        self._workspace(value.get('workspace'))
        return value

    def _snapshot_identity(self):
        return {'version': 1, 'profile': str(self.profile), 'installed': str(self.installed)}

    def _prune_snapshots(self):
        manifest = self._manifest()
        active = Path(manifest['snapshot']) if manifest is not None else None
        for directory in self.state.iterdir():
            if (len(directory.name) != 32 or any(letter not in '0123456789abcdef' for letter in directory.name)
                    or directory.is_symlink() or not directory.is_dir()):
                continue
            if directory == active and manifest['state'] in PENDING:
                continue
            info = directory.stat()
            if info.st_uid != os.getuid() or info.st_mode & 0o077:
                continue
            if directory != active:
                try:
                    data, metadata = _read(directory / 'identity.json')
                    if data is None or metadata['mode'] & 0o077 or json.loads(data) != self._snapshot_identity():
                        continue
                except (MountError, OSError, ValueError):
                    continue
            shutil.rmtree(directory)
            _sync_directory(self.state)

    def _workspace(self, value):
        if not isinstance(value, str):
            raise MountError('The mount workspace is invalid')
        workspace = Path(value)
        homes = {self.installed.parent}
        from .lifeos_installation import selection
        if selection(self.profile).configured:
            # A selected LifeOS home keeps the workspace in the account home that holds the profile.
            homes.add(self.profile.parent)
        if (not workspace.is_absolute() or workspace.resolve() != workspace or workspace in homes
                or not any(workspace.is_relative_to(home) for home in homes)):
            raise MountError('The mount workspace must belong to the installed owner home')
        return workspace

    def status(self):
        with self._lock():
            manifest = self._manifest()
            return {'state': manifest['state'] if manifest else 'none',
                    'recovery_required': manifest is not None and manifest['state'] in PENDING}

    def _source_stamp(self):
        names = ['LIFEOS/HERMES/Mount.ts', 'LIFEOS/HERMES/Policy.ts',
                 'LIFEOS/HERMES/RenderSoul.ts', 'LIFEOS/LIFEOS_SYSTEM_PROMPT.md',
                 'LIFEOS/USER/DIGITAL_ASSISTANT/DA_IDENTITY.md', 'LIFEOS/USER/PRINCIPAL/PRINCIPAL_IDENTITY.md',
                 'LIFEOS/USER/TELOS/PRINCIPAL_TELOS.md', 'LIFEOS/USER/PROJECTS.md',
                 'LIFEOS/USER/PRINCIPAL/PRINCIPAL_MEMORY.md', 'LIFEOS/USER/DIGITAL_ASSISTANT/DA_MEMORY.md',
                 'LIFEOS/USER/CONFIG/hermes-trusted-domains.json']
        names += ['LIFEOS/HERMES/plugin/' + name for name in ('__init__.py', 'guard.py', 'plugin.yaml')]
        skills = self.installed / 'skills'
        if skills.is_symlink():
            raise MountError('Mount skills must use the installed directory')
        if skills.is_dir():
            with os.scandir(skills) as entries:
                for index, entry in enumerate(entries):
                    if index >= 2048:
                        raise MountError('Mount skill discovery exceeds its limit')
                    if entry.is_symlink():
                        raise MountError('Mount skills change their physical paths')
                    if entry.is_dir():
                        names.append('skills/' + entry.name + '/SKILL.md')
        result = {}
        for name in sorted(names):
            path = self.installed / name
            # USER and MEMORY use the native linked owner tree. The final file cannot redirect.
            if path.is_symlink():
                raise MountError('A mount source changes its physical path')
            if path.is_file():
                with path.open('rb') as stream:
                    data = stream.read(LIMIT + 1)
                if len(data) > LIMIT:
                    raise MountError('A mount source exceeds its size limit')
                result[name] = hashlib.sha256(data).hexdigest()
            else:
                result[name] = None
        return result

    def _checks(self, entries, acceptable, *, restoring=False):
        for entry in entries:
            _, current = _read(Path(entry['target']))
            expected = [entry[name] for name in acceptable]
            if restoring and entry['before'] is not None:
                expected.append({**entry['before'], 'mode': 0o600})
            if current not in expected:
                raise MountError('A mount target changed. Recovery will preserve the later edit.')

    def _restore(self, manifest):
        if manifest['state'] not in PENDING:
            raise MountError('There is no interrupted mount to recover')
        self._checks(manifest['entries'], ('before', 'after'), restoring=manifest['state'] == 'restoring')
        snapshot = Path(manifest['snapshot'])
        copies = []
        for entry in manifest['entries']:
            if entry['before'] is not None:
                data, _ = _read(snapshot / 'previous' / str(entry['copy']))
                if data is None or hashlib.sha256(data).hexdigest() != entry['before']['digest']:
                    raise MountError('The mount recovery copy changed')
                copies.append((entry, data))
            else:
                copies.append((entry, None))
        manifest['state'] = 'restoring'
        _json(self.journal, manifest)
        for entry, data in copies:
            self._checks([entry], ('before', 'after'), restoring=True)
            path = Path(entry['target'])
            if data is None:
                path.unlink(missing_ok=True)
                if path.parent.exists():
                    _sync_directory(path.parent)
            else:
                publish(path, data)
                os.chmod(path, entry['before']['mode'])
                with path.open('rb') as stream:
                    os.fsync(stream.fileno())
        for name in ('plugins/lifeos', 'plugins', 'workspace'):
            path = self._workspace(manifest['workspace']) if name == 'workspace' else self.profile / name
            if name in manifest['absent_directories']:
                try:
                    path.rmdir()
                    _sync_directory(path.parent)
                except FileNotFoundError:
                    pass
                except OSError:
                    if not path.is_dir() or path.is_symlink():
                        raise
        manifest['state'] = 'rolled_back'
        _json(self.journal, manifest)
        return {'state': 'rolled_back'}

    def recover(self):
        with self._lock():
            manifest = self._manifest()
            if manifest is None:
                raise MountError('There is no interrupted mount to recover')
            return self._restore(manifest)

    def _publish(self, manifest):
        self._checks(manifest['entries'], ('before',))
        manifest['state'] = 'applying'
        _json(self.journal, manifest)
        snapshot = Path(manifest['snapshot'])
        for entry in manifest['entries']:
            self._checks([entry], ('before',))
            data, _ = _read(snapshot / 'selected' / str(entry['copy']))
            if data is None or hashlib.sha256(data).hexdigest() != entry['after']['digest']:
                raise MountError('The prepared mount output changed')
            publish(Path(entry['target']), data)
            parent = Path(entry['target']).parent
            while parent.is_relative_to(self.installed.parent):
                _sync_directory(parent)
                parent = parent.parent

    def execute(self, environment, bun, hermes, *, baseline_data=None, binding=None):
        from .memory_administration import ENVIRONMENT, mount_environment, validate
        from .memory_service import MemoryConfiguration
        with self._lock():
            previous = self._manifest()
            if previous is not None and previous['state'] in PENDING:
                raise MountError('Recover the interrupted mount before mounting again')
            native = self.installed / 'LIFEOS/HERMES/Mount.ts'
            if 'LIFEOS_MOUNT_DESTINATION' not in native.read_text():
                raise MountError('The installed native mount does not support prepared output')
            grant = environment.get(ENVIRONMENT)
            checked = mount_environment(self.installed, self.profile, grant, binding=binding)
            environment = {**environment, **{name: checked[name] for name in ('HOME', 'HERMES_HOME')}}
            environment.pop('LIFEOS_MEMORY_INTERNAL', None)
            environment.pop('LIFEOS_MEMORY_CONTEXT', None)
            environment.pop('LIFEOS_MOUNT_DESTINATION', None)
            if 'HERMES_WORKSPACE' not in environment:
                from .lifeos_installation import selection
                selected = selection(self.profile)
                # A selected LifeOS home keeps the account workspace that the profile records.
                environment['HERMES_WORKSPACE'] = str(selected.workspace if selected.configured
                                                      else self.installed.parent / 'HermesWorkspace')
            workspace = self._workspace(environment['HERMES_WORKSPACE'])
            snapshot = self.state / uuid4().hex
            snapshot.mkdir(mode=0o700)
            _json(snapshot / 'identity.json', self._snapshot_identity())
            stage = snapshot / 'stage'
            stage.mkdir(mode=0o700)
            (snapshot / 'previous').mkdir(mode=0o700)
            (snapshot / 'selected').mkdir(mode=0o700)
            sources = self._source_stamp()
            originals = {name: _read(self.profile / name) for name in FILES}
            output = _run([bun, '--no-install', str(native)], self.installed,
                {**environment, 'LIFEOS_MOUNT_DESTINATION': str(stage)}, 'Mount preparation')
            if self._source_stamp() != sources:
                raise MountError('Mount sources changed during preparation')
            plan = json.loads((stage / 'mount-plan.json').read_text())
            if (set(plan) != {'version', 'home', 'keepOutputFormat', 'signature', 'previous_digest'}
                    or plan['version'] != 1 or plan['home'] != str(self.profile) or type(plan['keepOutputFormat']) is not bool):
                raise MountError('The native mount plan is invalid')
            entries = []
            outputs = [(self.profile / name, *originals[name], _read(stage / name)[0]) for name in FILES]
            if baseline_data is not None:
                if self.baseline is None or not self.baseline.is_relative_to(self.installed.parent):
                    raise MountError('The mount baseline must belong to the installation')
                outputs.append((self.baseline, *_read(self.baseline), baseline_data))
            for index, (target, before_data, before, selected) in enumerate(outputs):
                if not isinstance(selected, bytes):
                    raise MountError('The native mount output is incomplete')
                if before_data is not None:
                    publish(snapshot / 'previous' / str(index), before_data)
                publish(snapshot / 'selected' / str(index), selected)
                entries.append({'target': str(target), 'before': before, 'after': {
                    'digest': hashlib.sha256(selected).hexdigest(), 'mode': 0o600}, 'copy': index})
            checker_environment = {key: value for key, value in environment.items() if key != ENVIRONMENT}
            _check_prepared_config(self.installed, checker_environment, stage)
            manifest = {'version': 1, 'installed': str(self.installed), 'profile': str(self.profile),
                'baseline': str(self.baseline) if self.baseline is not None else None,
                'snapshot': str(snapshot), 'state': 'prepared', 'entries': entries,
                'workspace': str(workspace),
                'absent_directories': [name for name in ('plugins', 'plugins/lifeos')
                                       if not (self.profile / name).exists()] + ([] if workspace.exists() else ['workspace'])}
            _sync_directory(snapshot)
            _json(self.journal, manifest)
            try:
                if grant is not None:
                    from .memory_access import NativeMemory
                    from .memory_prompt import _collect
                    configuration = MemoryConfiguration(self.profile / 'lifeos-memory.json')
                    with configuration._lock():
                        config, scope = validate(configuration, grant, check_binding=True, binding=binding)
                        memory = NativeMemory(Path(config['root']))
                        with memory._transaction() as connection:
                            current = _collect(memory, scope, connection, plan['keepOutputFormat'])
                            if (current['signature'] != plan['signature']
                                    or current['bundle']['soul'].encode() != (stage / 'SOUL.md').read_bytes()
                                    or self._source_stamp() != sources):
                                raise MountError('Mount sources changed before publication')
                            validate(configuration, grant, check_binding=True, binding=binding)
                            self._publish(manifest)
                else:
                    if plan['signature'] is not None or self._source_stamp() != sources:
                        raise MountError('Mount sources changed before publication')
                    self._publish(manifest)
                _run([bun, '--no-install', str(native), '--check'], self.installed, environment, 'Mount check')
                _run([hermes, 'config', 'check'], self.installed, checker_environment, 'Hermes config check')
                self._checks(entries, ('after',))
                workspace.mkdir(parents=True, exist_ok=True, mode=0o700)
                _sync_directory(workspace.parent)
                manifest['state'] = 'committed'
                _json(self.journal, manifest)
            except BaseException:
                self._restore(manifest)
                raise
            return {'mounted': True, 'snapshot': str(snapshot), 'restart_required': True,
                    'state': 'committed', 'output': output}
