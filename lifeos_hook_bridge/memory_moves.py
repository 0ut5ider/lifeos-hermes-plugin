# ABOUTME: Journals fixed owner file moves without copying media into recovery metadata.
# ABOUTME: Preserves later edits and uses atomic Linux renames that cannot replace a destination.
import ctypes
import hashlib
import os
import shutil
import stat


def _identity(value):
    return (value.st_dev, value.st_ino, value.st_mode, value.st_uid, value.st_nlink,
            value.st_size, value.st_mtime_ns, value.st_ctime_ns)


def fingerprint(path):
    from .memory_access import MemoryUnavailable
    if not path.exists() and not path.is_symlink():
        return None
    entries = [path]
    if path.is_dir() and not path.is_symlink():
        entries.extend(sorted(path.rglob('*')))
    if len(entries) > 10000:
        raise MemoryUnavailable('Content artifact disposal exceeds its bounded file inventory')
    digest = hashlib.sha256()
    observed = {}
    for entry in entries:
        before = entry.lstat()
        observed[entry] = _identity(before)
        if (before.st_uid != os.getuid() or not (stat.S_ISREG(before.st_mode) or stat.S_ISDIR(before.st_mode))
                or stat.S_ISREG(before.st_mode) and before.st_nlink != 1):
            raise MemoryUnavailable('Content disposal requires physical owner files and directories')
        data = [entry.relative_to(path).as_posix(), before.st_dev, before.st_ino,
                before.st_mode, before.st_size, before.st_mtime_ns, before.st_uid]
        digest.update(repr(data).encode())
        if stat.S_ISREG(before.st_mode):
            descriptor = os.open(entry, os.O_RDONLY | os.O_NOFOLLOW)
            with os.fdopen(descriptor, 'rb') as stream:
                opened = os.fstat(stream.fileno())
                if _identity(opened) != _identity(before):
                    raise MemoryUnavailable('Content media changes before disposal admission')
                for chunk in iter(lambda: stream.read(1024 * 1024), b''):
                    digest.update(chunk)
                if _identity(os.fstat(stream.fileno())) != _identity(before):
                    raise MemoryUnavailable('Content media changes during disposal admission')
        if _identity(entry.lstat()) != _identity(before):
            raise MemoryUnavailable('Content artifacts change during disposal admission')
    current = [path] + (sorted(path.rglob('*')) if path.is_dir() else [])
    if current != entries or any(_identity(entry.lstat()) != observed[entry] for entry in entries):
        raise MemoryUnavailable('Content artifacts change after disposal admission')
    return digest.hexdigest()



def inventory(path):
    from .memory_access import MemoryUnavailable
    if fingerprint(path) is None:
        return []
    entries = [path] + (sorted(path.rglob('*')) if path.is_dir() else [])
    result = []
    observed = {}
    for entry in entries:
        before = entry.lstat()
        observed[entry] = _identity(before)
        directory = stat.S_ISDIR(before.st_mode)
        digest = None
        if not directory:
            descriptor = os.open(entry, os.O_RDONLY | os.O_NOFOLLOW)
            with os.fdopen(descriptor, 'rb') as stream:
                if _identity(os.fstat(stream.fileno())) != observed[entry]:
                    raise MemoryUnavailable('Content cleanup inventory changes its owner file')
                value = hashlib.sha256()
                for chunk in iter(lambda: stream.read(1024 * 1024), b''):
                    value.update(chunk)
                if _identity(os.fstat(stream.fileno())) != observed[entry]:
                    raise MemoryUnavailable('Content cleanup inventory changes during its read')
                digest = value.hexdigest()
        result.append({'path': entry.relative_to(path).as_posix(),
            'identity': [before.st_dev, before.st_ino, before.st_mode, before.st_uid,
                         None if directory else before.st_size, None if directory else before.st_mtime_ns],
            'digest': digest})
    current = [path] + (sorted(path.rglob('*')) if path.is_dir() else [])
    if current != entries or any(_identity(entry.lstat()) != observed[entry] for entry in entries):
        raise MemoryUnavailable('Content cleanup inventory changes after its read')
    return result


def _validate_inventory(value):
    from .memory_access import MemoryUnavailable
    if not isinstance(value, list) or not 1 <= len(value) <= 10000:
        raise MemoryUnavailable('Content cleanup requires a bounded original inventory')
    seen = set()
    for entry in value:
        if (not isinstance(entry, dict) or set(entry) != {'path', 'identity', 'digest'}
                or not isinstance(entry['path'], str) or not entry['path'] or entry['path'] in seen
                or entry['path'].startswith('/') or '..' in entry['path'].split('/')
                or not isinstance(entry['identity'], list) or len(entry['identity']) != 6
                or any(type(part) is not int or part < 0 for part in entry['identity'][:4])):
            raise MemoryUnavailable('Content cleanup has invalid inventory metadata')
        seen.add(entry['path'])
        directory = stat.S_ISDIR(entry['identity'][2])
        if directory:
            valid = entry['identity'][4:] == [None, None] and entry['digest'] is None
        else:
            valid = (stat.S_ISREG(entry['identity'][2])
                and all(type(part) is int for part in entry['identity'][4:]) and entry['identity'][4] >= 0
                and isinstance(entry['digest'], str) and len(entry['digest']) == 64
                and all(part in '0123456789abcdef' for part in entry['digest']))
        if not valid:
            raise MemoryUnavailable('Content cleanup has invalid original file metadata')
    if value[0]['path'] != '.' or not stat.S_ISDIR(value[0]['identity'][2]):
        raise MemoryUnavailable('Content cleanup has no selected original directory')


def move(source, destination):
    from .memory_access import MemoryUnavailable
    library = ctypes.CDLL(None, use_errno=True)
    rename = getattr(library, 'renameat2', None)
    if rename is None:
        raise MemoryUnavailable('Content disposal requires Linux atomic no-replacement renames')
    rename.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
    rename.restype = ctypes.c_int
    descriptors = []
    try:
        for path in (source.parent, destination.parent):
            descriptors.append(os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW))
        if rename(descriptors[0], os.fsencode(source.name), descriptors[1], os.fsencode(destination.name), 1):
            error = ctypes.get_errno()
            raise OSError(error, os.strerror(error))
        for descriptor in descriptors:
            os.fsync(descriptor)
    finally:
        for descriptor in descriptors:
            os.close(descriptor)


class MemoryMoves:
    def __init__(self, resolve):
        self.resolve = resolve

    def validate(self, entries):
        from .memory_access import MemoryUnavailable
        if not isinstance(entries, list) or len(entries) > 3:
            raise MemoryUnavailable('Content move recovery has invalid targets')
        seen = set()
        for entry in entries:
            if (not isinstance(entry, dict) or set(entry) not in ({'source', 'destination', 'digest', 'remove'},
                    {'source', 'destination', 'digest', 'remove', 'inventory'})
                    or not all(isinstance(entry[key], str) for key in ('source', 'destination', 'digest'))
                    or type(entry['remove']) is not bool or len(entry['digest']) != 64
                    or any(c not in '0123456789abcdef' for c in entry['digest'])):
                raise MemoryUnavailable('Content move recovery has invalid metadata')
            if entry['remove']:
                _validate_inventory(entry.get('inventory'))
            elif 'inventory' in entry:
                raise MemoryUnavailable('Content trash cannot select derivative cleanup')
            source = self.resolve(entry['source'])
            destination = self.resolve(entry['destination'])
            if source == destination or str(source) in seen or str(destination) in seen:
                raise MemoryUnavailable('Content move recovery duplicates a target')
            seen.update((str(source), str(destination)))
            if entry['remove'] != (entry['source'].startswith('artifacts:') and entry['destination'].startswith('quarantine:')):
                raise MemoryUnavailable('Content move recovery changes its cleanup target')
            if not entry['remove'] and (not entry['source'].startswith('inbox:')
                    or entry['destination'] != 'trash:' + entry['source'].removeprefix('inbox:')):
                raise MemoryUnavailable('Content move recovery changes its trash target')

    def before(self, entries):
        from .memory_access import MemoryUnavailable
        self.validate(entries)
        for entry in entries:
            if (fingerprint(self.resolve(entry['source'])) != entry['digest']
                    or fingerprint(self.resolve(entry['destination'])) is not None):
                raise MemoryUnavailable('Content disposal preserves changed sources and existing trash')
            if entry['remove'] and inventory(self.resolve(entry['source'])) != entry['inventory']:
                raise MemoryUnavailable('Content disposal changes its derivative cleanup inventory')

    def apply(self, entries):
        self.before(entries)
        for entry in entries:
            source = self.resolve(entry['source'])
            destination = self.resolve(entry['destination'])
            destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            self.resolve(entry['destination'])
            if fingerprint(source) != entry['digest']:
                from .memory_access import MemoryUnavailable
                raise MemoryUnavailable('Content disposal preserves a later media edit')
            move(source, destination)

    def recovery_check(self, entries):
        from .memory_access import MemoryUnavailable
        self.validate(entries)
        for entry in entries:
            source = fingerprint(self.resolve(entry['source']))
            destination = fingerprint(self.resolve(entry['destination']))
            if (source, destination) not in ((entry['digest'], None), (None, entry['digest'])):
                raise MemoryUnavailable('Content move recovery preserves later owner files')

    def recover(self, entries):
        self.recovery_check(entries)
        for entry in reversed(entries):
            self.recovery_check(entries)
            source = self.resolve(entry['source'])
            destination = self.resolve(entry['destination'])
            if destination.exists():
                move(destination, source)

    def cleanup_check(self, entry):
        from .memory_access import MemoryUnavailable
        expected = {part['path']: part for part in entry['inventory']}
        current = inventory(self.resolve(entry['destination']))
        if any(part != expected.get(part['path']) for part in current):
            raise MemoryUnavailable('Content cleanup preserves later owner artifacts')

    def finish(self, entries):
        from .memory_access import MemoryUnavailable
        self.validate(entries)
        for entry in entries:
            if entry['remove']:
                self.cleanup_check(entry)
            elif fingerprint(self.resolve(entry['destination'])) != entry['digest']:
                raise MemoryUnavailable('Content cleanup preserves later owner files')
        for entry in entries:
            if entry['remove']:
                destination = self.resolve(entry['destination'])
                if destination.exists():
                    self.cleanup_check(entry)
                    shutil.rmtree(destination)
                    descriptor = os.open(destination.parent, os.O_RDONLY | os.O_DIRECTORY)
                    try:
                        os.fsync(descriptor)
                    finally:
                        os.close(descriptor)
