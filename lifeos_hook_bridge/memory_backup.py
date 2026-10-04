# ABOUTME: Captures native USER_DATA and governance metadata under one cooperating writer lock.
# ABOUTME: Publishes private verified snapshots without replacing existing backups or live files.
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import stat
import tempfile

from .memory_access import HOT_FILES, MemoryUnavailable, SCHEMA_VERSION
from .memory_adoption import _owner
from .memory_transaction import publish
from .sqlite_snapshot import standalone


FILE_LIMIT = 64 * 1024 * 1024
TOTAL_LIMIT = 256 * 1024 * 1024
ENTRY_LIMIT = 100_000
DATABASE = 'MEMORY/STATE/memory-access.sqlite'
EXCLUDED = {DATABASE + suffix for suffix in ('-journal', '-wal', '-shm')}
EXCLUDED.add('MEMORY/STATE/memory-access.lock')


def _authorize(scope):
    if not _owner(scope):
        raise MemoryUnavailable('Native backup requires an unrestricted owner context')


def _directory(path, *, private=False):
    info = path.lstat()
    if (path.resolve() != path or not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid()
            or info.st_mode & (0o077 if private else 0o022)):
        raise MemoryUnavailable('The backup directory changes its physical path or owner permissions')


def _read(path, *, private=False):
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    except OSError as error:
        raise MemoryUnavailable('A backup file changes its physical path or is unavailable') from error
    with os.fdopen(descriptor, 'rb') as stream:
        before = os.fstat(stream.fileno())
        if (not stat.S_ISREG(before.st_mode) or before.st_uid != os.getuid() or before.st_size > FILE_LIMIT
                or private and before.st_mode & 0o077):
            raise MemoryUnavailable('Backup files require bounded regular owner files and permitted permissions')
        data = stream.read(FILE_LIMIT + 1)
        after = os.fstat(stream.fileno())
        current = path.lstat()
        stamp = lambda info: (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_mode)
        if len(data) > FILE_LIMIT or stamp(before) != stamp(after) or stamp(after) != stamp(current):
            raise MemoryUnavailable('A backup source changed during collection')
    return data, {'mode': stat.S_IMODE(after.st_mode), 'mtime_ns': after.st_mtime_ns}


def _collect(memory, connection, stage=None):
    user = memory.root.parent / '.config/LIFEOS/USER'
    _directory(user)
    database_info = memory.database.stat()
    database_identity = (database_info.st_dev, database_info.st_ino)
    files, directories = [], []
    total = 0
    visited = 0
    pending = [user]
    while pending:
        directory = pending.pop()
        _directory(directory)
        info = directory.stat()
        directories.append({'path': directory.relative_to(user).as_posix(),
                            'mode': stat.S_IMODE(info.st_mode), 'mtime_ns': info.st_mtime_ns})
        with os.scandir(directory) as entries:
            children = []
            for entry in entries:
                visited += 1
                if visited > ENTRY_LIMIT:
                    raise MemoryUnavailable('The native backup exceeds its source count limit')
                children.append(Path(entry.path))
        for path in sorted(children):
            relative = path.relative_to(user).as_posix()
            if path.is_symlink():
                raise MemoryUnavailable('A native backup source changes its physical path')
            if path.is_dir():
                pending.append(path)
                continue
            if relative in EXCLUDED:
                continue
            if relative == DATABASE:
                info = path.lstat()
                if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_size > FILE_LIMIT:
                    raise MemoryUnavailable('The native backup database requires a bounded regular owner file')
                metadata = {'mode': stat.S_IMODE(info.st_mode), 'mtime_ns': info.st_mtime_ns}
                # Direct descriptor closure would release this process's SQLite record locks.
                data = standalone(connection)
                current = path.lstat()
                if (info.st_dev, info.st_ino, info.st_mtime_ns, info.st_mode) != (
                        current.st_dev, current.st_ino, current.st_mtime_ns, current.st_mode):
                    raise MemoryUnavailable('The native backup database changed during collection')
            else:
                info = path.lstat()
                if (info.st_dev, info.st_ino) == database_identity:
                    raise MemoryUnavailable('A native backup source aliases its governance database')
                data, metadata = _read(path)
            total += len(data)
            if len(data) > FILE_LIMIT or total > TOTAL_LIMIT:
                raise MemoryUnavailable('The native backup exceeds its byte limit')
            item = {'path': relative, 'copy': len(files), 'size': len(data),
                    'digest': hashlib.sha256(data).hexdigest(), **metadata}
            files.append(item)
            if stage is not None:
                publish(stage / 'files' / str(item['copy']), data)
    if DATABASE not in {item['path'] for item in files}:
        raise MemoryUnavailable('The native backup has no governance metadata')
    return {'files': files, 'directories': sorted(directories, key=lambda item: item['path'])}


def _check_references(memory, connection):
    hot_entries = {memory._path(relative): memory._hot_snapshot(connection, category)['entries']
                   for category, relative in HOT_FILES.items()}
    for row in connection.execute("SELECT * FROM records WHERE status='active' ORDER BY id"):
        memory._content(row, hot_entries)


def capture(memory, scope, connection, stage):
    _authorize(scope)
    _check_references(memory, connection)
    snapshot = _collect(memory, connection, stage)
    _check_references(memory, connection)
    if _collect(memory, connection) != snapshot:
        raise MemoryUnavailable('The native backup sources changed during collection')
    manifest = {'version': 1, 'root': str(memory.root), 'principal': scope.principal,
                'schema': SCHEMA_VERSION, 'created': datetime.now(timezone.utc).isoformat(), **snapshot}
    data = (json.dumps(manifest, sort_keys=True, indent=2) + '\n').encode()
    publish(stage / 'manifest.json', data)
    signature = hashlib.sha256(data).hexdigest()
    inspect(memory, scope, stage, signature)
    return manifest, signature


def create(memory, scope, destination):
    _authorize(scope)
    destination = Path(destination).absolute()
    user = memory.root.parent / '.config/LIFEOS/USER'
    if destination.is_relative_to(user) or destination.is_relative_to(memory.root):
        raise MemoryUnavailable('A native backup must remain outside the live data and program trees')
    if destination.exists() or destination.is_symlink():
        raise MemoryUnavailable('An existing native backup cannot be replaced')
    destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    _directory(destination.parent)
    stage = Path(tempfile.mkdtemp(prefix='.backup-', dir=destination.parent))
    try:
        with memory._transaction() as connection:
            manifest, signature = capture(memory, scope, connection, stage)
            _directory(destination.parent)
            if destination.exists() or destination.is_symlink():
                raise MemoryUnavailable('An existing native backup cannot be replaced')
            os.rename(stage, destination)
            descriptor = os.open(destination.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
            try:
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
        return {'status': 'committed', 'snapshot': str(destination), 'signature': signature,
                'files': len(manifest['files']), 'schema': SCHEMA_VERSION}
    finally:
        if stage.exists():
            shutil.rmtree(stage)


def _relative(value, *, directory=False):
    if (not isinstance(value, str) or not value or Path(value).is_absolute()
            or '..' in Path(value).parts or Path(value).as_posix() != value or value == '.' and not directory):
        raise MemoryUnavailable('The native backup contains an invalid source path')


def inspect(memory, scope, destination, signature=None):
    _authorize(scope)
    destination = Path(destination).absolute()
    _directory(destination, private=True)
    _directory(destination / 'files', private=True)
    data, _ = _read(destination / 'manifest.json', private=True)
    if signature is not None and hashlib.sha256(data).hexdigest() != signature:
        raise MemoryUnavailable('The native backup manifest fails its reviewed integrity check')
    manifest = json.loads(data)
    if (not isinstance(manifest, dict) or set(manifest) != {'version', 'root', 'principal', 'schema', 'created', 'files', 'directories'}
            or manifest['version'] != 1 or manifest['schema'] != SCHEMA_VERSION
            or manifest['root'] != str(memory.root) or manifest['principal'] != scope.principal):
        raise MemoryUnavailable('The native backup belongs to another installation or has unsupported metadata')
    files, directories = manifest['files'], manifest['directories']
    if (not isinstance(files, list) or not isinstance(directories, list) or not files or not directories
            or len(files) + len(directories) > ENTRY_LIMIT + 1):
        raise MemoryUnavailable('The native backup source list is invalid')
    total, seen = 0, set()
    database = None
    for index, item in enumerate(files):
        if (not isinstance(item, dict) or set(item) != {'path', 'copy', 'size', 'digest', 'mode', 'mtime_ns'}
                or type(item['copy']) is not int or item['copy'] != index
                or type(item['size']) is not int or not 0 <= item['size'] <= FILE_LIMIT
                or type(item['mode']) is not int or not 0 <= item['mode'] <= 0o777
                or type(item['mtime_ns']) is not int):
            raise MemoryUnavailable('The native backup file metadata is invalid')
        _relative(item['path'])
        if item['path'] in seen or item['path'] in EXCLUDED:
            raise MemoryUnavailable('The native backup repeats or includes an excluded source')
        seen.add(item['path'])
        content, _ = _read(destination / 'files' / str(index), private=True)
        total += len(content)
        if total > TOTAL_LIMIT or len(content) != item['size'] or hashlib.sha256(content).hexdigest() != item['digest']:
            raise MemoryUnavailable('The native backup copy fails its integrity check')
        if item['path'] == DATABASE:
            database = content
    seen = set()
    for item in directories:
        if (not isinstance(item, dict) or set(item) != {'path', 'mode', 'mtime_ns'}
                or type(item['mode']) is not int or not 0 <= item['mode'] <= 0o777
                or type(item['mtime_ns']) is not int):
            raise MemoryUnavailable('The native backup directory metadata is invalid')
        _relative(item['path'], directory=True)
        if item['path'] in seen:
            raise MemoryUnavailable('The native backup repeats a directory')
        seen.add(item['path'])
    if '.' not in seen or database is None:
        raise MemoryUnavailable('The native backup lacks its data root or governance metadata')
    connection = sqlite3.connect(':memory:')
    try:
        connection.deserialize(database)
        if (connection.execute('PRAGMA integrity_check').fetchall() != [('ok',)]
                or connection.execute('PRAGMA user_version').fetchone()[0] != SCHEMA_VERSION):
            raise MemoryUnavailable('The native backup database fails its integrity check')
    except sqlite3.Error as error:
        raise MemoryUnavailable('The native backup database fails its integrity check') from error
    finally:
        connection.close()
    return manifest
