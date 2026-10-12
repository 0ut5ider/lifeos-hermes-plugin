# ABOUTME: Publishes complete-release program directories and fixed launcher files with a durable journal.
# ABOUTME: Restores retained programs after interruption and refuses later artifact edits.
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import tempfile
import uuid


class ProgramConflict(ValueError):
    pass


def publish(path, data, mode=0o600):
    path = Path(path)
    if path.parent.resolve() != path.parent:
        raise ProgramConflict('A program publication changes its physical directory')
    descriptor, name = tempfile.mkstemp(prefix='.release-', dir=path.parent)
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, 'wb') as output:
            os.fchmod(output.fileno(), mode)
            output.write(data)
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, path)
        sync_directory(path.parent)
    finally:
        temporary.unlink(missing_ok=True)


def sync_directory(path):
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def fingerprint(path, *, allow_links=False, excluded_root_entries=()):
    path = Path(path).absolute()
    if path.parent.resolve() != path.parent:
        raise ProgramConflict('A program artifact changes its physical directory')
    try:
        info = path.lstat()
    except FileNotFoundError:
        return None
    if info.st_uid != os.getuid() or info.st_mode & 0o022:
        raise ProgramConflict('A program artifact requires an owner file without shared write access')
    if stat.S_ISREG(info.st_mode):
        return {'type': 'file', 'mode': stat.S_IMODE(info.st_mode),
                'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
    if not stat.S_ISDIR(info.st_mode):
        raise ProgramConflict('Program artifacts must be regular files or directories')
    digest = hashlib.sha256()
    for parent, directories, files in os.walk(path, followlinks=False):
        if Path(parent) == path:
            directories[:] = [name for name in directories if name not in excluded_root_entries]
            files = [name for name in files if name not in excluded_root_entries]
        directories[:] = sorted(name for name in directories if name != '__pycache__')
        for name in (*directories, *sorted(files)):
            child = Path(parent) / name
            if child.suffix == '.pyc':
                continue
            child_info = child.lstat()
            if stat.S_ISLNK(child_info.st_mode) and allow_links:
                link = os.readlink(child)
                if (Path(link).is_absolute() or not child.resolve(strict=True).is_relative_to(path)
                        or child_info.st_uid != os.getuid()):
                    raise ProgramConflict('Dependency links must stay inside their package directory')
                digest.update(str(child.relative_to(path)).encode() + b'\0link\0' + link.encode() + b'\0')
                continue
            if (not (stat.S_ISREG(child_info.st_mode) or stat.S_ISDIR(child_info.st_mode))
                    or child_info.st_uid != os.getuid() or child_info.st_mode & 0o022):
                raise ProgramConflict('Program trees require regular owner artifacts without shared write access')
            digest.update(str(child.relative_to(path)).encode() + b'\0')
            digest.update(str(stat.S_IMODE(child_info.st_mode)).encode() + b'\0')
            if child.is_file():
                digest.update(hashlib.sha256(child.read_bytes()).digest())
    return {'type': 'directory', 'mode': stat.S_IMODE(info.st_mode), 'sha256': digest.hexdigest()}


class ProgramTransaction:
    def __init__(self, snapshot, *, expected_entries_sha256=None):
        self.snapshot = Path(snapshot).absolute()
        self.journal = self.snapshot / 'programs.json'
        self.expected_entries_sha256 = expected_entries_sha256

    def _record(self, value):
        publish(self.journal, (json.dumps(value, indent=2, sort_keys=True) + '\n').encode())

    def _load(self):
        if (self.snapshot.resolve() != self.snapshot or not self.snapshot.is_dir()
                or self.snapshot.stat().st_uid != os.getuid() or self.snapshot.stat().st_mode & 0o077
                or self.journal.is_symlink() or self.journal.stat().st_uid != os.getuid()
                or self.journal.stat().st_mode & 0o077):
            raise ProgramConflict('The program journal requires private owner storage')
        from .cli import read_private
        value = read_private(self.journal)
        if (not isinstance(value, dict) or set(value) != {'format', 'state', 'entries'}
                or type(value['format']) is not int or value['format'] != 1 or not isinstance(value['entries'], list)
                or len(value['entries']) > 20000):
            raise ProgramConflict('The program journal has an invalid structure')
        for entry in value['entries']:
            if (not isinstance(entry, dict) or set(entry) != {'target', 'source', 'before', 'after', 'kind', 'allow_links'}
                    or entry['kind'] not in {'file', 'directory'} or type(entry['allow_links']) is not bool
                    or not isinstance(entry['target'], str) or not Path(entry['target']).is_absolute()
                    or '..' in Path(entry['target']).parts
                    or entry['source'] is not None and (not isinstance(entry['source'], str)
                        or not Path(entry['source']).is_absolute() or '..' in Path(entry['source']).parts)):
                raise ProgramConflict('The program journal has invalid artifact paths or types')
            for state in ('before', 'after'):
                metadata = entry[state]
                if metadata is not None and (not isinstance(metadata, dict)
                        or set(metadata) != {'type', 'mode', 'sha256'} or metadata['type'] != entry['kind']
                        or type(metadata['mode']) is not int or not 0 <= metadata['mode'] <= 0o777
                        or not isinstance(metadata['sha256'], str) or len(metadata['sha256']) != 64
                        or any(c not in '0123456789abcdef' for c in metadata['sha256'])):
                    raise ProgramConflict('The program journal has invalid artifact identities')
        digest = self._entries_digest(value['entries'])
        if self.expected_entries_sha256 is not None and digest != self.expected_entries_sha256:
            raise ProgramConflict('The reviewed program entries change before publication or recovery')
        return value

    @staticmethod
    def _entries_digest(entries):
        return hashlib.sha256(json.dumps(entries, sort_keys=True, separators=(',', ':')).encode()).hexdigest()

    def entries_digest(self):
        return self._entries_digest(self._load()['entries'])

    def prepare(self, *, directories, files, dependencies=None, checkpoint=lambda point: None):
        dependencies = {} if dependencies is None else dependencies
        targets = [Path(path).absolute() for path in (*directories, *files, *dependencies)]
        if (len(targets) != len(set(targets)) or any(left.is_relative_to(right)
                for left in targets for right in targets if left != right)
                or any(self.snapshot.is_relative_to(target) for target in targets)):
            raise ProgramConflict('Program transaction targets must not overlap')
        entries = []
        for kind, sources, allow_links in (('directory', directories, False), ('file', files, False),
                                           ('directory', dependencies, True)):
            for target, incoming in sources.items():
                target = Path(target).absolute()
                incoming = None if incoming is None else Path(incoming).absolute()
                before = fingerprint(target, allow_links=allow_links)
                after = None if incoming is None else fingerprint(incoming, allow_links=allow_links)
                if (incoming is not None and (after is None or after['type'] != kind)
                        or before is not None and before['type'] != kind):
                    raise ProgramConflict('Program transaction targets require matching artifact types')
                if before is None and after is None:
                    continue
                entries.append({'target': str(target), 'source': None if incoming is None else str(incoming),
                    'before': before, 'after': after, 'kind': kind, 'allow_links': allow_links})
        if self.snapshot.exists() or self.snapshot.is_symlink():
            info = self.snapshot.lstat()
            if (not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077
                    or self.journal.exists() or self.journal.is_symlink()
                    or self.expected_entries_sha256 is not None):
                raise ProgramConflict('An existing program snapshot requires its recorded review')
            retained = self.snapshot.with_name(self.snapshot.name + '-incomplete-' + uuid.uuid4().hex)
            os.rename(self.snapshot, retained)
            sync_directory(self.snapshot.parent)
        self.snapshot.mkdir(mode=0o700)
        for index, entry in enumerate(entries):
            incoming = self.snapshot / ('incoming-' + str(index))
            source = None if entry['source'] is None else Path(entry['source'])
            if source is not None and entry['kind'] == 'directory':
                shutil.copytree(source, incoming, symlinks=entry['allow_links'],
                                ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
            elif source is not None:
                shutil.copy2(source, incoming)
            if entry['kind'] == 'file':
                if entry['before'] is not None:
                    shutil.copy2(entry['target'], self.snapshot / ('before-' + str(index)))
            if fingerprint(incoming, allow_links=entry['allow_links']) != entry['after']:
                raise ProgramConflict('The staged program copy differs from its source')
            checkpoint('artifact-staged')
        self._record({'format': 1, 'state': 'prepared', 'entries': entries})

    def apply(self, *, checkpoint=lambda point: None):
        value = self._load()
        self.check_prepared()
        value['state'] = 'applying'
        self._record(value)
        for index, entry in enumerate(value['entries']):
            target, incoming = Path(entry['target']), self.snapshot / ('incoming-' + str(index))
            if entry['kind'] == 'directory':
                if entry['before'] is not None:
                    os.replace(target, self.snapshot / ('before-' + str(index)))
                    sync_directory(target.parent)
                    sync_directory(self.snapshot)
                checkpoint('directory-retained')
                if entry['after'] is not None:
                    os.replace(incoming, target)
                sync_directory(target.parent)
                sync_directory(self.snapshot)
            else:
                if entry['after'] is None:
                    target.unlink()
                    sync_directory(target.parent)
                else:
                    publish(target, incoming.read_bytes(), entry['after']['mode'])
            checkpoint('artifact-published')
        value['state'] = 'applied'
        self._record(value)

    def check_prepared(self):
        value = self._load()
        if value['state'] != 'prepared':
            raise ProgramConflict('The program transaction is not prepared')
        for index, entry in enumerate(value['entries']):
            source_state = None if entry['source'] is None else fingerprint(entry['source'], allow_links=entry['allow_links'])
            if (source_state != entry['after']
                    or fingerprint(self.snapshot / ('incoming-' + str(index)), allow_links=entry['allow_links']) != entry['after']
                    or fingerprint(entry['target'], allow_links=entry['allow_links']) != entry['before']):
                raise ProgramConflict('A program target or source changes after preparation')

    def resume(self, *, checkpoint=lambda point: None):
        value = self._load()
        if value['state'] not in {'prepared', 'applying', 'applied'}:
            raise ProgramConflict('The program transaction cannot resume this state')
        for index, entry in enumerate(value['entries']):
            current = fingerprint(entry['target'], allow_links=entry['allow_links'])
            backup = self.snapshot / ('before-' + str(index))
            retained = fingerprint(backup, allow_links=entry['allow_links'])
            absent_swap = current is None and entry['kind'] == 'directory' and retained == entry['before'] and retained is not None
            if (current not in (entry['before'], entry['after']) and not absent_swap
                    or value['state'] == 'applied' and current != entry['after']):
                raise ProgramConflict('Program recovery preserves a later artifact edit')
            if retained is not None and retained != entry['before']:
                raise ProgramConflict('The retained program differs from its recorded identity')
            if current == entry['after']:
                if current != entry['before'] and entry['before'] is not None and retained != entry['before']:
                    raise ProgramConflict('Program recovery requires its retained prior artifact')
                continue
            source = None if entry['source'] is None else fingerprint(entry['source'], allow_links=entry['allow_links'])
            incoming = fingerprint(self.snapshot / ('incoming-' + str(index)), allow_links=entry['allow_links'])
            if source != entry['after'] or incoming != entry['after']:
                raise ProgramConflict('The staged program copy differs from its source')
        value['state'] = 'applying'
        self._record(value)
        for index, entry in enumerate(value['entries']):
            target, incoming = Path(entry['target']), self.snapshot / ('incoming-' + str(index))
            if fingerprint(target, allow_links=entry['allow_links']) == entry['after']:
                continue
            if entry['kind'] == 'directory':
                if target.exists():
                    os.replace(target, self.snapshot / ('before-' + str(index)))
                    sync_directory(target.parent)
                    sync_directory(self.snapshot)
                checkpoint('directory-retained')
                if entry['after'] is not None:
                    os.replace(incoming, target)
                sync_directory(target.parent)
                sync_directory(self.snapshot)
            elif entry['after'] is None:
                target.unlink()
                sync_directory(target.parent)
            else:
                publish(target, incoming.read_bytes(), entry['after']['mode'])
            checkpoint('artifact-published')
        value['state'] = 'applied'
        self._record(value)

    def restore(self):
        value = self._load()
        if value['state'] not in {'prepared', 'applying', 'applied', 'restoring', 'restored'}:
            raise ProgramConflict('The program transaction cannot restore this state')
        for index, entry in enumerate(value['entries']):
            current = fingerprint(entry['target'], allow_links=entry['allow_links'])
            if value['state'] == 'applied' and current != entry['after']:
                raise ProgramConflict('Program recovery preserves a later artifact edit')
            absent_swap = (current is None and entry['kind'] == 'directory'
                           and (self.snapshot / ('before-' + str(index))).exists())
            if current not in (entry['before'], entry['after']) and not absent_swap:
                raise ProgramConflict('Program recovery preserves a later artifact edit')
            backup = self.snapshot / ('before-' + str(index))
            if backup.exists() and fingerprint(backup, allow_links=entry['allow_links']) != entry['before']:
                raise ProgramConflict('The retained program differs from its recorded identity')
        value['state'] = 'restoring'
        self._record(value)
        for index, entry in reversed(list(enumerate(value['entries']))):
            target, backup = Path(entry['target']), self.snapshot / ('before-' + str(index))
            if fingerprint(target, allow_links=entry['allow_links']) == entry['before']:
                continue
            if entry['kind'] == 'directory':
                if target.exists():
                    os.replace(target, self.snapshot / ('selected-' + str(index)))
                if entry['before'] is not None:
                    os.replace(backup, target)
                sync_directory(target.parent)
                sync_directory(self.snapshot)
            elif entry['before'] is None:
                target.unlink(missing_ok=True)
                sync_directory(target.parent)
            else:
                publish(target, backup.read_bytes(), entry['before']['mode'])
        value['state'] = 'restored'
        self._record(value)
