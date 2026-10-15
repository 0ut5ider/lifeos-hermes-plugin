# ABOUTME: Journals reviewed Hermes and LifeOS ownership configuration changes.
# ABOUTME: Restores exact configuration from a verified profile backup without restoring native data.
from contextlib import contextmanager, nullcontext
import hashlib
import io
import json
import os
from pathlib import Path
import re
import sys

from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

from .installation_lock import installation_lock
from .memory_access import MemoryUnavailable
from .memory_access import NativeMemory
from .memory_backup import _directory, _read
from .memory_administration import _connector
from .memory_transaction import publish
from .mount_transaction import _read as read_target, _sync_directory
from .profile_backup import inspect


NAMES = ('config.yaml', 'lifeos-memory.json')
STATES = {'prepared', 'applying', 'committed', 'restoring', 'rolled_back'}


def _digest(data):
    return hashlib.sha256(data).hexdigest()


def _encoded(document):
    return (json.dumps(document, sort_keys=True, indent=2) + '\n').encode()


def _signature(value):
    return isinstance(value, str) and re.fullmatch('[0-9a-f]{64}', value) is not None


def connector_target(configuration):
    root=Path(configuration['root']).absolute()
    NativeMemory(root)._boundary()
    directory=root.parent/'.config/LIFEOS/USER/CONFIG'
    _directory(directory)
    return directory/'memory-access.json'


def _check_connector(configuration, selected, digest):
    connector,_=_read(connector_target(selected),private=True)
    if _digest(connector)!=digest:
        raise MemoryUnavailable('The reviewed native memory connector changes during ownership setup')
    _connector(configuration,selected)


class OwnershipTransaction:
    def __init__(self, configuration, *, installation_lease=None, verify_writers=None, publication_barrier=None):
        self.configuration = configuration
        self.installation_lease = installation_lease
        if verify_writers is not None and not callable(verify_writers):
            raise ValueError('Ownership publication requires a callable writer barrier')
        self.verify_writers = verify_writers
        if publication_barrier is not None and not callable(publication_barrier):
            raise ValueError('Ownership publication requires a callable native barrier')
        self.publication_barrier = publication_barrier
        self.profile = configuration.path.parent.absolute()
        if configuration.path.absolute() != self.profile / 'lifeos-memory.json':
            raise MemoryUnavailable('Ownership setup requires the fixed profile configuration')
        self.state = self.profile / '.lifeos-ownership'
        self.journal = self.state / 'operation.json'

    def _owner(self, account):
        if not isinstance(account, str) or not account.startswith('dashboard:'):
            raise PermissionError('An authenticated installation owner must review ownership setup')
        configuration = self.configuration.load()
        self.configuration.check_owner(configuration, account)
        return configuration

    @contextmanager
    def _lock(self, account):
        with installation_lock(self.profile, lease=self.installation_lease), self.configuration._lock():
            configuration = self._owner(account)
            self.state.mkdir(mode=0o700, exist_ok=True)
            _directory(self.state, private=True)
            yield configuration

    def _load(self, configuration):
        if not self.journal.exists() and not self.journal.is_symlink():
            return None
        data, _ = _read(self.journal, private=True)
        try:
            document = json.loads(data)
        except (ValueError, UnicodeError, RecursionError) as error:
            raise MemoryUnavailable('The ownership journal has invalid content') from error
        fields = {'version', 'profile', 'root', 'principal', 'state', 'backup', 'backup_signature',
            'signature', 'connector_digest', 'entries'}
        if (not isinstance(document, dict) or set(document) != fields
                or type(document['version']) is not int or document['version'] != 1
                or document['profile'] != str(self.profile) or document['root'] != configuration['root']
                or document['principal'] != configuration['principal']
                or not isinstance(document['state'], str) or document['state'] not in STATES
                or not isinstance(document['backup'], str) or not Path(document['backup']).is_absolute()
                or not _signature(document['backup_signature']) or not _signature(document['signature'])
                or not _signature(document['connector_digest'])
                or not isinstance(document['entries'], list) or len(document['entries']) != len(NAMES)):
            raise MemoryUnavailable('The ownership journal belongs to another profile or has invalid metadata')
        for name, entry in zip(NAMES, document['entries']):
            if (not isinstance(entry, dict) or set(entry) != {'name', 'copy', 'before', 'after'}
                    or entry['name'] != name or type(entry['copy']) is not int or entry['copy'] < 0):
                raise MemoryUnavailable('The ownership journal has invalid configuration targets')
            for key in ('before', 'after'):
                metadata = entry[key]
                if (not isinstance(metadata, dict) or set(metadata) != {'digest', 'mode'}
                        or not _signature(metadata['digest']) or type(metadata['mode']) is not int
                        or not 0 <= metadata['mode'] <= 0o777):
                    raise MemoryUnavailable('The ownership journal has invalid configuration metadata')
        return document

    def _plan(self, configuration, backup, backup_signature, account):
        if configuration.get('ownership_enabled', False) or configuration.get('sharing_enabled', False):
            raise MemoryUnavailable('Fresh ownership setup requires ownership and sharing to be disabled')
        if not _signature(backup_signature):
            raise MemoryUnavailable('Ownership setup requires the reviewed profile backup signature')
        backup = Path(backup).absolute()
        manifest = inspect(self.configuration, backup, backup_signature, account=account)
        native_data, _ = _read(backup / 'native/manifest.json', private=True)
        if _digest(native_data) != manifest['native_signature']:
            raise MemoryUnavailable('The ownership native backup manifest changes after verification')
        native = json.loads(native_data)
        captured_connector = next((entry for entry in native['files'] if entry['path'] == 'CONFIG/memory-access.json'), None)
        target=connector_target(configuration)
        current,_=read_target(target)
        if captured_connector is None:
            if current is not None:
                raise MemoryUnavailable('Ownership setup preserves a later native memory connector')
            connector=_encoded({'version':1,'command':[sys.executable,str(Path(__file__).with_name('memory_rpc.py').absolute()),
                '--configuration',str(self.configuration.path.absolute())]})
        else:
            _connector(self.configuration, configuration)
            connector, _ = _read(target, private=True)
            if captured_connector['digest'] != _digest(connector):
                raise MemoryUnavailable('Ownership setup requires the current reviewed native memory connector')
        captured = {entry['path']: entry for entry in manifest['files']}
        targets = {}
        targets['connector']=connector if captured_connector is None else None
        entries = []
        for name in NAMES:
            data, metadata = read_target(self.profile / name)
            original = captured.get(name)
            if data is None or original is None or metadata != {'digest': original['digest'], 'mode': original['mode']}:
                raise MemoryUnavailable('Ownership configuration changes require a current reviewed profile backup')
            targets[name] = data
            entries.append({'name': name, 'copy': original['copy'], 'before': metadata})
        try:
            yaml = YAML()
            yaml.preserve_quotes = True
            hermes = yaml.load(targets['config.yaml'].decode())
            if not isinstance(hermes, dict):
                raise MemoryUnavailable('Hermes ownership setup requires a configuration mapping')
            if 'memory' in hermes and not isinstance(hermes['memory'], dict):
                raise MemoryUnavailable('Hermes ownership setup requires unambiguous memory settings')
            memory = hermes.setdefault('memory', {})
            if any(getattr(mapping, 'merge', None) or getattr(getattr(mapping, 'anchor', None), 'value', None)
                   for mapping in (hermes, memory)):
                raise MemoryUnavailable('Shared or merged ownership settings require configuration review')
            memory.update(provider='lifeos-hook-bridge', memory_enabled=False, user_profile_enabled=False)
            stream = io.StringIO()
            yaml.dump(hermes, stream)
            targets['config.yaml'] = stream.getvalue().encode()
        except (YAMLError, UnicodeError, RecursionError) as error:
            raise MemoryUnavailable('Hermes ownership configuration cannot be parsed safely') from error
        selected = {**configuration, 'ownership_enabled': True}
        self.configuration.validate(selected)
        targets['lifeos-memory.json'] = (json.dumps(selected, indent=2) + '\n').encode()
        for entry in entries:
            entry['after'] = {'digest': _digest(targets[entry['name']]), 'mode': 0o600}
        plan = {'version': 1, 'profile': str(self.profile), 'root': configuration['root'],
            'principal': configuration['principal'], 'backup': str(backup), 'backup_signature': backup_signature,
            'connector_digest': _digest(connector), 'entries': entries}
        return {**plan, 'signature': _digest(_encoded(plan))}, targets

    def preview(self, backup, backup_signature, *, account=None):
        with self._lock(account) as configuration:
            previous = self._load(configuration)
            if previous is not None and previous['state'] != 'rolled_back':
                raise MemoryUnavailable('Recover or return the existing ownership configuration before setup')
            plan, _ = self._plan(configuration, backup, backup_signature, account)
            return {'signature': plan['signature'], 'backup': plan['backup'],
                'backup_signature': backup_signature, 'configuration_files': list(NAMES),
                'restart_required': True, 'service_verified': False}

    def _check_targets(self, document, acceptable, *, restoring=False):
        for entry in document['entries']:
            _, metadata = read_target(self.profile / entry['name'])
            expected = [entry[key] for key in acceptable]
            if restoring:
                expected.append({**entry['before'], 'mode': 0o600})
            if metadata not in expected:
                raise MemoryUnavailable('Ownership recovery preserves later configuration edits')

    def apply(self, backup, backup_signature, signature, *, account=None):
        with self._lock(account) as configuration, (self.publication_barrier() if self.publication_barrier else nullcontext()):
            previous = self._load(configuration)
            if previous is not None and previous['state'] != 'rolled_back':
                raise MemoryUnavailable('Recover or return the existing ownership configuration before setup')
            plan, targets = self._plan(configuration, backup, backup_signature, account)
            if not _signature(signature) or signature != plan['signature']:
                raise MemoryUnavailable('Ownership setup requires the current reviewed configuration plan')
            document = {**plan, 'state': 'prepared'}
            publish(self.journal, _encoded(document))
            self._check_targets(document, ('before',))
            document['state'] = 'applying'
            publish(self.journal, _encoded(document))
            if targets['connector'] is not None:
                if self.verify_writers is not None:self.verify_writers()
                target=connector_target(configuration)
                if read_target(target)!=(None,None):
                    raise MemoryUnavailable('Ownership setup preserves a later native memory connector')
                publish(target,targets['connector'])
            # The built-in stores are disabled before the native provider becomes available.
            for index, entry in enumerate(document['entries']):
                inspect(self.configuration, Path(plan['backup']), backup_signature, account=account)
                if self.verify_writers is not None:
                    self.verify_writers()
                _check_connector(self.configuration,configuration,plan['connector_digest'])
                self._check_targets({'entries': document['entries'][:index]}, ('after',))
                _, metadata = read_target(self.profile / entry['name'])
                if metadata != entry['before']:
                    raise MemoryUnavailable('Ownership setup preserves a configuration change during publication')
                publish(self.profile / entry['name'], targets[entry['name']])
            self._check_targets(document, ('after',))
            _check_connector(self.configuration,configuration,plan['connector_digest'])
            document['state'] = 'committed'
            publish(self.journal, _encoded(document))
            return {'state': 'committed', 'signature': signature, 'restart_required': True, 'service_verified': False}

    def status(self, *, account=None):
        with self._lock(account) as configuration:
            document = self._load(configuration)
            state = document['state'] if document is not None else 'none'
            return {'state': state, 'recovery_required': state in {'prepared', 'applying', 'restoring'},
                'restart_required': state != 'none', 'service_verified': False,
                'signature': document['signature'] if document is not None else None}

    def rollback(self, *, account=None):
        with self._lock(account) as configuration:
            document = self._load(configuration)
            if document is None:
                raise MemoryUnavailable('There is no ownership configuration to recover')
            if document['state'] == 'rolled_back':
                self._check_targets(document, ('before',))
                return {'state': 'rolled_back', 'restart_required': True, 'service_verified': False}
            manifest = inspect(self.configuration, Path(document['backup']), document['backup_signature'], account=account)
            native_data,_=_read(Path(document['backup'])/'native/manifest.json',private=True)
            if _digest(native_data)!=manifest['native_signature']:
                raise MemoryUnavailable('The ownership native backup manifest changes after verification')
            missing_connector=not any(item['path']=='CONFIG/memory-access.json' for item in json.loads(native_data)['files'])
            target=connector_target(configuration)
            connector_after={'digest':document['connector_digest'],'mode':0o600}
            if missing_connector and read_target(target)[1] not in (None,connector_after):
                raise MemoryUnavailable('Ownership recovery preserves a later native memory connector')
            copies = []
            for entry in document['entries']:
                original = next((item for item in manifest['files'] if item['path'] == entry['name']), None)
                if (original is None or entry['copy'] != original['copy']
                        or entry['before'] != {'digest': original['digest'], 'mode': original['mode']}):
                    raise MemoryUnavailable('The ownership recovery backup has different configuration metadata')
                content, _ = _read(Path(document['backup']) / 'profile/files' / str(entry['copy']), private=True)
                if _digest(content) != entry['before']['digest']:
                    raise MemoryUnavailable('An ownership recovery copy changes after verification')
                copies.append((entry, content))
            acceptable = ('before', 'after')
            # An interrupted atomic publication can precede restoration of the original mode.
            self._check_targets(document, acceptable, restoring=document['state'] == 'restoring')
            document['state'] = 'restoring'
            publish(self.journal, _encoded(document))
            # Revoke native ownership before either built-in store can resume.
            for entry, content in reversed(copies):
                if self.verify_writers is not None:
                    self.verify_writers()
                self._check_targets({'entries': [entry]}, acceptable, restoring=True)
                publish(self.profile / entry['name'], content)
                (self.profile / entry['name']).chmod(entry['before']['mode'])
                with (self.profile / entry['name']).open('rb') as stream:
                    os.fsync(stream.fileno())
                _sync_directory(self.profile)
            if missing_connector:
                if self.verify_writers is not None:self.verify_writers()
                if read_target(target)[1] not in (None,connector_after):
                    raise MemoryUnavailable('Ownership recovery preserves a later native memory connector')
                target.unlink(missing_ok=True);_sync_directory(target.parent)
            self._check_targets(document, ('before',))
            document['state'] = 'rolled_back'
            publish(self.journal, _encoded(document))
            return {'state': 'rolled_back', 'restart_required': True, 'service_verified': False}
