# ABOUTME: Reconstructs verified native snapshots in separate private recovery trees.
# ABOUTME: Checks current references without replacing live data or selecting memory ownership.
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import tempfile

from .memory_access import NativeMemory, MemoryUnavailable
from .memory_backup import _authorize, _check_references, _directory, _read, inspect
from .memory_transaction import publish


def _sync_tree(root):
    for directory, _, files in os.walk(root, followlinks=False):
        parent = Path(directory)
        for name in files:
            path = parent / name
            if path.is_symlink():
                continue
            descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
            try:
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
        descriptor = os.open(parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)


def recover(memory, scope, backup, signature, destination):
    _authorize(scope)
    if not isinstance(signature, str) or re.fullmatch('[0-9a-f]{64}', signature) is None:
        raise MemoryUnavailable('Native recovery requires the reviewed backup signature')
    backup = Path(backup).absolute()
    manifest = inspect(memory, scope, backup, signature)
    destination = Path(destination).absolute()
    user = memory.root.parent / '.config/LIFEOS/USER'
    if any(destination.resolve().is_relative_to(path.resolve()) for path in (memory.root, user, backup)):
        raise MemoryUnavailable('Native recovery must remain outside the live program, data, and backup trees')
    if destination.exists() or destination.is_symlink():
        raise MemoryUnavailable('An existing native recovery tree cannot be replaced')
    if destination.parent.resolve() != destination.parent:
        raise MemoryUnavailable('The native recovery destination changes its physical path')
    tools = memory.root / 'LIFEOS/TOOLS'
    if not (tools / 'MemorySystem.ts').is_file():
        raise MemoryUnavailable('Native recovery needs the installed memory tools')
    destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    _directory(destination.parent)
    stage = Path(tempfile.mkdtemp(prefix='.recovery-', dir=destination.parent))
    try:
        data_root = stage / '.config/LIFEOS/USER'
        data_root.mkdir(parents=True, mode=0o700)
        for entry in sorted(manifest['directories'], key=lambda item: len(Path(item['path']).parts)):
            (data_root / entry['path']).mkdir(parents=True, exist_ok=True, mode=0o700)
        for entry in manifest['files']:
            data, _ = _read(backup / 'files' / str(entry['copy']), private=True)
            if hashlib.sha256(data).hexdigest() != entry['digest'] or len(data) != entry['size']:
                raise MemoryUnavailable('A native recovery source changed after verification')
            target = data_root / entry['path']
            publish(target, data)
            target.chmod(entry['mode'])
            os.utime(target, ns=(entry['mtime_ns'], entry['mtime_ns']))
        root = stage / '.claude'
        (root / 'LIFEOS').mkdir(parents=True, mode=0o700)
        (root / 'LIFEOS/USER').symlink_to('../../.config/LIFEOS/USER', target_is_directory=True)
        (root / 'LIFEOS/MEMORY').symlink_to('../../.config/LIFEOS/USER/MEMORY', target_is_directory=True)
        (root / 'LIFEOS/TOOLS').symlink_to(tools.resolve(), target_is_directory=True)
        candidate = NativeMemory(root, bun=memory.bun)
        with candidate._transaction() as connection:
            _check_references(candidate, connection)
            active = connection.execute("SELECT COUNT(*) FROM records WHERE status='active'").fetchone()[0]
            retired = connection.execute("SELECT COUNT(*) FROM records WHERE status!='active'").fetchone()[0]
        inspect(memory, scope, backup, signature)
        for entry in sorted(manifest['directories'], key=lambda item: len(Path(item['path']).parts), reverse=True):
            target = data_root / entry['path']
            target.chmod(entry['mode'])
            os.utime(target, ns=(entry['mtime_ns'], entry['mtime_ns']))
        recovery = {'version': 1, 'source_root': str(memory.root), 'principal': scope.principal,
                    'backup': str(backup), 'signature': signature, 'destination': str(destination),
                    'active_facts': active, 'retired_facts': retired, 'ownership_enabled': False}
        publish(stage / '.native-recovery.json', (json.dumps(recovery, sort_keys=True, indent=2) + '\n').encode())
        _sync_tree(stage)
        _directory(destination.parent)
        if destination.exists() or destination.is_symlink():
            raise MemoryUnavailable('An existing native recovery tree cannot be replaced')
        os.rename(stage, destination)
        descriptor = os.open(destination.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
        return {'status': 'recovered', 'root': str(destination / '.claude'), 'signature': signature,
                'files': len(manifest['files']), 'active_facts': active, 'retired_facts': retired,
                'ownership_enabled': False, 'program_tools': str(tools.resolve()),
                'recovery_manifest': str(destination / '.native-recovery.json')}
    finally:
        if stage.exists():
            shutil.rmtree(stage)
