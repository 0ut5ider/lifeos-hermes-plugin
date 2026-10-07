# ABOUTME: Captures one selected Hermes profile and native data under configuration and SQLite writer barriers.
# ABOUTME: Preserves user state, internal links, and committed histories, and records each excluded regenerable entry.
from contextlib import ExitStack, closing
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sqlite3
import stat
import tempfile

from .installation_lock import installation_lock
from .memory_access import NativeMemory, MemoryUnavailable
from .memory_backup import FILE_LIMIT, TOTAL_LIMIT, ENTRY_LIMIT, _directory, _read, _relative, capture
from .memory_backup import inspect as inspect_native
from .memory_preferences import MemoryPreferences
from .memory_transaction import publish
from .sqlite_snapshot import standalone


# Top-level entries that Hermes or the plugin can create again. A backup records them and does not copy them.
EXCLUDED_TOP_LEVEL = {
    'installs': 'regenerable', 'tools': 'regenerable', 'cache': 'regenerable', 'image_cache': 'regenerable',
    'audio_cache': 'regenerable', 'logs': 'regenerable', 'hermes-agent': 'regenerable',
    'models_dev_cache.json': 'regenerable', 'models_dev_cache.etag': 'regenerable', 'profiles': 'other_profile',
}
EXCLUSION_REASONS = {'regenerable', 'other_profile', 'dependencies', 'runtime'}
RETAINED_LOCKFILES = {'bun.lock'}


class ProfileBackupTooLarge(MemoryUnavailable):
    def __init__(self, largest):
        self.largest = largest
        names = ', '.join(f'{name} ({size // (1024 * 1024)} MiB)' for name, size in largest)
        super().__init__('The profile backup exceeds its byte limit. Largest top-level entries: ' + names)


def _exclusion(relative, path):
    parts = relative.split('/')
    if len(parts) == 1:
        if relative in EXCLUDED_TOP_LEVEL:
            return EXCLUDED_TOP_LEVEL[relative]
        if relative.endswith(('.pid', '.sock')) or relative.endswith('.lock') and relative not in RETAINED_LOCKFILES:
            return 'runtime'
    elif parts[-1] == 'node_modules' and path.is_dir() and not path.is_symlink():
        return 'dependencies'
    return None


def _largest(profile, user):
    sizes = {}
    for path, kind, info, _ in _entries(profile, user):
        if kind == 'file':
            name = path.relative_to(profile).parts[0]
            sizes[name] = sizes.get(name, 0) + info.st_size
    return sorted(sizes.items(), key=lambda item: (-item[1], item[0]))[:5]


def _entries(profile, user, excluded=None):
    pending = [profile]
    entries = []
    while pending:
        directory = pending.pop()
        _directory(directory)
        info = directory.stat()
        entries.append((directory, 'directory', info, None))
        for path in sorted(directory.iterdir()):
            relative = path.relative_to(profile).as_posix()
            if relative == '.lifeos-installation/lock':
                continue
            reason = _exclusion(relative, path)
            if reason is None and stat.S_ISSOCK(path.lstat().st_mode):
                reason = 'runtime'
            if reason is not None:
                if excluded is not None:
                    excluded.append({'path': relative, 'reason': reason})
                continue
            info = path.lstat()
            if info.st_uid != os.getuid():
                raise MemoryUnavailable('A profile source belongs to another operating-system owner')
            if path.is_symlink():
                target = os.readlink(path)
                resolved = path.resolve()
                if len(target) > 4096 or not (resolved.is_relative_to(profile) or resolved.is_relative_to(user)):
                    raise MemoryUnavailable('An external profile link requires reviewed source coverage')
                entries.append((path, 'link', info, target))
            elif path.is_dir():
                pending.append(path)
            elif stat.S_ISREG(info.st_mode):
                entries.append((path, 'file', info, None))
            else:
                raise MemoryUnavailable('A profile backup source requires a regular file, directory, or covered link')
            if len(entries) + len(pending) > ENTRY_LIMIT:
                raise MemoryUnavailable('The profile backup exceeds its source count limit')
    return sorted(entries, key=lambda item: item[0].relative_to(profile).as_posix())


def _databases(profile, user, stack):
    databases = {}
    sources = []
    identities = set()
    for path, kind, _, _ in _entries(profile, user):
        if kind != 'file':
            continue
        data, _ = _read(path)
        if data[:16] != b'SQLite format 3\x00':
            continue
        before = path.lstat()
        identity = (before.st_dev, before.st_ino)
        if identity in identities:
            raise MemoryUnavailable('A profile database has repeated physical sources')
        identities.add(identity)
        sources.append((path, identity))
    for path, identity in sources:
        connection = sqlite3.connect(path.as_uri() + '?mode=rw', uri=True, timeout=5)
        stack.callback(connection.close)
        if hasattr(sqlite3, 'SQLITE_DBCONFIG_NO_CKPT_ON_CLOSE'):
            connection.setconfig(sqlite3.SQLITE_DBCONFIG_NO_CKPT_ON_CLOSE, True)
        connection.execute('BEGIN IMMEDIATE')
        after = path.lstat()
        if identity != (after.st_dev, after.st_ino):
            raise MemoryUnavailable('A profile database changed its physical identity during admission')
        databases[path] = (connection, (after.st_dev, after.st_ino))
    return databases


def _collect_profile(profile, user, databases, stage=None):
    files, directories, links = [], [], []
    total = 0
    database_identities = {identity for _, identity in databases.values()}
    sidecars = {path.with_name(path.name + suffix) for path in databases for suffix in ('-wal', '-shm', '-journal')}
    excluded = []
    for path, kind, info, target in _entries(profile, user, excluded):
        relative = path.relative_to(profile).as_posix()
        metadata = {'mode': stat.S_IMODE(info.st_mode), 'mtime_ns': info.st_mtime_ns}
        if kind == 'directory':
            directories.append({'path': relative, **metadata})
        elif kind == 'link':
            links.append({'path': relative, 'target': target, 'mtime_ns': info.st_mtime_ns})
        elif path not in sidecars:
            if path in databases:
                connection, identity = databases[path]
                if ((info.st_dev, info.st_ino) != identity or not stat.S_ISREG(info.st_mode)
                        or info.st_uid != os.getuid() or info.st_size > FILE_LIMIT):
                    raise MemoryUnavailable('A profile database changed its physical identity during collection')
                # Closing another descriptor for this inode releases the process's SQLite record locks.
                data = standalone(connection)
                current = path.lstat()
                if (current.st_dev, current.st_ino) != identity:
                    raise MemoryUnavailable('A profile database changed its physical identity during collection')
            else:
                if (info.st_dev, info.st_ino) in database_identities:
                    raise MemoryUnavailable('A profile source aliases an admitted database')
                data, metadata = _read(path)
                if data[:16] == b'SQLite format 3\x00':
                    raise MemoryUnavailable('A profile database has no admitted writer barrier')
            total += len(data)
            if total > TOTAL_LIMIT:
                raise ProfileBackupTooLarge(_largest(profile, user))
            if len(data) > FILE_LIMIT:
                raise MemoryUnavailable('The profile backup exceeds its byte limit')
            files.append({'path': relative, 'copy': len(files), 'size': len(data),
                          'digest': hashlib.sha256(data).hexdigest(), 'sqlite': path in databases, **metadata})
            if stage is not None:
                publish(stage / 'files' / str(files[-1]['copy']), data)
    return {'files': files, 'directories': directories, 'links': links,
            'excluded': sorted(excluded, key=lambda item: item['path'])}


def create(configuration, destination, *, account=None, installation_lease=None):
    profile = configuration.path.parent.absolute()
    destination = Path(destination).absolute()
    with installation_lock(profile, lease=installation_lease), configuration._lock(), ExitStack() as stack:
        config = configuration.load()
        configuration.check_owner(config, account)
        memory = NativeMemory(Path(config['root']))
        user = (memory.root.parent / '.config/LIFEOS/USER').resolve()
        if any(destination.resolve().is_relative_to(path.resolve()) for path in (profile, memory.root, user)):
            raise MemoryUnavailable('A profile backup must remain outside its live program and data trees')
        if destination.exists() or destination.is_symlink():
            raise MemoryUnavailable('An existing profile backup cannot be replaced')
        if destination.parent.resolve() != destination.parent:
            raise MemoryUnavailable('A profile backup destination changes its physical path')
        databases = _databases(profile, user, stack)
        destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        _directory(destination.parent)
        stage = Path(tempfile.mkdtemp(prefix='.profile-backup-', dir=destination.parent))
        try:
            scope = MemoryPreferences._owner_scope(config)
            with memory._transaction() as connection:
                (stage / 'native').mkdir(mode=0o700)
                (stage / 'profile').mkdir(mode=0o700)
                native, native_signature = capture(memory, scope, connection, stage / 'native')
                snapshot = _collect_profile(profile, user, databases, stage / 'profile')
                if _collect_profile(profile, user, databases) != snapshot or configuration.load() != config:
                    raise MemoryUnavailable('The selected profile changed during backup collection')
                manifest = {'version': 2, 'profile': str(profile), 'native_root': str(memory.root),
                            'principal': config['principal'], 'created': datetime.now(timezone.utc).isoformat(),
                            'native_signature': native_signature, **snapshot}
                data = (json.dumps(manifest, sort_keys=True, indent=2) + '\n').encode()
                signature = hashlib.sha256(data).hexdigest()
                publish(stage / 'manifest.json', data)
                inspect(configuration, stage, signature, account=account)
                _directory(destination.parent)
                if destination.exists() or destination.is_symlink():
                    raise MemoryUnavailable('An existing profile backup cannot be replaced')
                os.rename(stage, destination)
                descriptor = os.open(destination.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
                try:
                    os.fsync(descriptor)
                finally:
                    os.close(descriptor)
            return {'status': 'committed', 'snapshot': str(destination), 'signature': signature,
                    'profile_files': len(snapshot['files']), 'native_files': len(native['files']),
                    'excluded_entries': len(snapshot['excluded'])}
        finally:
            if stage.exists():
                shutil.rmtree(stage)


def inspect(configuration, destination, signature=None, *, account=None):
    config = configuration.load()
    configuration.check_owner(config, account)
    destination = Path(destination).absolute()
    _directory(destination, private=True)
    _directory(destination / 'profile', private=True)
    _directory(destination / 'profile/files', private=True)
    data, _ = _read(destination / 'manifest.json', private=True)
    if signature is not None and hashlib.sha256(data).hexdigest() != signature:
        raise MemoryUnavailable('The profile backup fails its reviewed manifest signature')
    try:
        manifest = json.loads(data)
    except (ValueError, UnicodeError) as error:
        raise MemoryUnavailable('The profile backup has invalid manifest content') from error
    if (not isinstance(manifest, dict) or set(manifest) != {'version', 'profile', 'native_root', 'principal', 'created',
            'native_signature', 'files', 'directories', 'links', 'excluded'}
            or type(manifest['version']) is not int or manifest['version'] != 2
            or manifest['profile'] != str(configuration.path.parent.absolute()) or manifest['native_root'] != config['root']
            or manifest['principal'] != config['principal'] or not isinstance(manifest['native_signature'], str)
            or re.fullmatch('[0-9a-f]{64}', manifest['native_signature']) is None):
        raise MemoryUnavailable('The profile backup belongs to another profile or has unsupported metadata')
    lists = [manifest[key] for key in ('files', 'directories', 'links', 'excluded')]
    if (any(not isinstance(items, list) for items in lists) or not manifest['files']
            or not manifest['directories'] or sum(map(len, lists)) > ENTRY_LIMIT + 1):
        raise MemoryUnavailable('The profile backup has invalid source lists')
    seen, total = set(), 0
    for index, item in enumerate(manifest['files']):
        if (not isinstance(item, dict) or set(item) != {'path', 'copy', 'size', 'digest', 'sqlite', 'mode', 'mtime_ns'}
                or type(item['copy']) is not int or item['copy'] != index or type(item['size']) is not int
                or not 0 <= item['size'] <= FILE_LIMIT or type(item['sqlite']) is not bool
                or type(item['mode']) is not int or not 0 <= item['mode'] <= 0o777
                or type(item['mtime_ns']) is not int or not isinstance(item['digest'], str)):
            raise MemoryUnavailable('The profile backup has invalid file metadata')
        _relative(item['path'])
        if item['path'] in seen:
            raise MemoryUnavailable('The profile backup repeats a source path')
        seen.add(item['path'])
        content, _ = _read(destination / 'profile/files' / str(index), private=True)
        total += len(content)
        if total > TOTAL_LIMIT or len(content) != item['size'] or hashlib.sha256(content).hexdigest() != item['digest']:
            raise MemoryUnavailable('The profile backup copy fails its integrity check')
        if item['sqlite']:
            try:
                with closing(sqlite3.connect(':memory:')) as database:
                    database.deserialize(content)
                    if database.execute('PRAGMA integrity_check').fetchall() != [('ok',)]:
                        raise MemoryUnavailable('The profile backup database fails its integrity check')
            except sqlite3.Error as error:
                raise MemoryUnavailable('The profile backup database fails its integrity check') from error
    directories = set()
    for item in manifest['directories']:
        if (not isinstance(item, dict) or set(item) != {'path', 'mode', 'mtime_ns'}
                or type(item['mode']) is not int or not 0 <= item['mode'] <= 0o777
                or type(item['mtime_ns']) is not int):
            raise MemoryUnavailable('The profile backup has invalid directory metadata')
        _relative(item['path'], directory=True)
        if item['path'] in seen:
            raise MemoryUnavailable('The profile backup repeats a source path')
        seen.add(item['path'])
        directories.add(item['path'])
    profile = configuration.path.parent.absolute()
    user = (Path(config['root']).parent / '.config/LIFEOS/USER').resolve()
    for item in manifest['links']:
        if (not isinstance(item, dict) or set(item) != {'path', 'target', 'mtime_ns'}
                or type(item['mtime_ns']) is not int or not isinstance(item['target'], str)
                or not item['target'] or '\x00' in item['target'] or len(item['target']) > 4096):
            raise MemoryUnavailable('The profile backup has invalid link metadata')
        _relative(item['path'])
        if item['path'] in seen:
            raise MemoryUnavailable('The profile backup repeats a source path')
        seen.add(item['path'])
        target = Path(os.path.abspath(profile / Path(item['path']).parent / item['target']))
        if not (target.is_relative_to(profile) or target.is_relative_to(user)):
            raise MemoryUnavailable('The profile backup has an unreviewed external link')
    excluded = set()
    for item in manifest['excluded']:
        if (not isinstance(item, dict) or set(item) != {'path', 'reason'}
                or item['reason'] not in EXCLUSION_REASONS or not isinstance(item['path'], str)):
            raise MemoryUnavailable('The profile backup has invalid exclusion metadata')
        _relative(item['path'])
        if item['path'] in seen or item['path'] in excluded or _exclusion(item['path'], profile / item['path']) not in (
                item['reason'], None if item['reason'] in ('dependencies', 'runtime') else item['reason']):
            raise MemoryUnavailable('The profile backup has invalid exclusion metadata')
        excluded.add(item['path'])
    if any(any(path == name or path.startswith(name + '/') for name in excluded) for path in seen):
        raise MemoryUnavailable('The profile backup copies a path inside an excluded entry')
    if '.' not in directories or configuration.path.name not in {item['path'] for item in manifest['files']}:
        raise MemoryUnavailable('The profile backup lacks its data root or ownership configuration')
    if any(Path(path).parent.as_posix() not in directories for path in seen if path != '.'):
        raise MemoryUnavailable('The profile backup lacks a source parent directory')
    inspect_native(NativeMemory(Path(config['root'])), MemoryPreferences._owner_scope(config),
                   destination / 'native', manifest['native_signature'])
    return manifest
