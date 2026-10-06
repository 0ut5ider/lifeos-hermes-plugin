# ABOUTME: Supplies admitted sources to the native constitutional and state freshness migrations.
# ABOUTME: Publishes source changes and original-byte backups through one recoverable journal.
import hashlib
import json
import os
from pathlib import Path
from uuid import uuid4

from .memory_access import MemoryConflict, MemoryUnavailable
from .memory_freshness import CONTEXT, TELOS, SYSTEM_PUBLICATIONS, _collect, _source_signature
from .memory_sources import CORPUS_LIMIT, SOURCE_LIMIT, authorize, read_markdown
from .memory_transaction import publish


def backup_name(relative):
    path = Path(relative)
    return (path.parent / 'Backups' / (path.stem + '-2026-05-03-23-00-00.md')).as_posix()


SYSTEM_BACKUPS = frozenset(backup_name(relative) for relative in SYSTEM_PUBLICATIONS)


def is_system_backup(name):
    """Accept a fixed system backup name or its digest variant for a later migration."""
    if name in SYSTEM_BACKUPS:
        return True
    stem, _, digest = name[:-len('.md')].rpartition('-') if name.endswith('.md') else ('', '', '')
    return stem + '.md' in SYSTEM_BACKUPS and len(digest) == 12 and all(c in '0123456789abcdef' for c in digest)


def _backup_destinations(memory, sources):
    """Map each source to its backup; a fixed name that holds other bytes gets a digest suffix."""
    destinations = {}
    for source in sources:
        standard = backup_name(source['relative'])
        original = source['content'].encode()
        path = memory._publication_path(standard)
        if path.is_file() and path.read_bytes() != original:
            standard = standard[:-len('.md')] + '-' + hashlib.sha256(original).hexdigest()[:12] + '.md'
        destinations[source['relative']] = standard
    return destinations


def _request(scope, dry_run, state):
    if type(dry_run) is not bool or type(state) is not bool:
        raise ValueError('Choose boolean migration preview and state options')
    authorize(scope)
    if not dry_run and not {'principal', 'assistant', 'project'} <= set(scope.write):
        raise MemoryUnavailable('Freshness migration requires unrestricted owner write access')


def _sources(memory, scope, connection, state):
    if state:
        return _collect(memory, scope, connection, 'state', None)
    paths = [str(memory.root / relative) for relative in sorted(CONTEXT - {TELOS})
             if (memory.root / relative).exists() or (memory.root / relative).is_symlink()]
    return read_markdown(memory, scope, paths, connection=connection)


def _paths(memory, sources, state):
    relatives = {source['relative'] for source in sources}
    system = set(SYSTEM_PUBLICATIONS | SYSTEM_BACKUPS)
    if not state:
        destinations = _backup_destinations(memory, sources)
        relatives |= set(destinations.values())
        system |= {destinations[relative] for relative in destinations if relative in SYSTEM_PUBLICATIONS}
    total = 0
    for relative in relatives:
        path = memory._publication_path(relative)
        physical = (path.absolute() if relative in system else
                    memory.root.parent / '.config/LIFEOS/USER' / Path(relative).relative_to('LIFEOS/USER'))
        if (path.resolve() != physical or path.is_symlink()
                or path.exists() and (not path.is_file() or path.stat().st_uid != os.getuid()
                                      or path.stat().st_size > SOURCE_LIMIT)):
            raise MemoryUnavailable('A migration source or backup changes its permitted owner destination')
        total += path.stat().st_size if path.exists() else 0
    if total > 2 * CORPUS_LIMIT:
        raise MemoryUnavailable('The migration sources and retained backups exceed their journal limit')
    return sorted(relatives)


def publication_paths(memory, connection, scope, payload):
    _request(scope, False, payload['state'])
    sources = _sources(memory, scope, connection, payload['state'])
    if _source_signature(sources) != payload['source_signature']:
        raise MemoryConflict('The migration sources changed before publication preparation')
    return _paths(memory, sources, payload['state'])


def _render(memory, sources, dry_run, state):
    result = memory._native('freshness_migration', sources=sources, dry_run=dry_run, state=state)
    # Context migration returns each admitted body twice: its source and original-byte backup.
    publication_limit = 2 * len(json.dumps(sources).encode()) + CORPUS_LIMIT
    if (set(result) != {'status', 'stdout', 'stderr', 'publications'} or type(result['status']) is not int
            or result['status'] not in (0, 1) or not isinstance(result['stdout'], str)
            or not isinstance(result['stderr'], str) or not isinstance(result['publications'], list)
            or len(json.dumps(result).encode()) > publication_limit
            or len(json.dumps({name: result[name] for name in ('stdout', 'stderr')}).encode()) > CORPUS_LIMIT):
        raise MemoryUnavailable('Native freshness migration returns an invalid publication result')
    if result['status'] != 0 and not dry_run:
        raise MemoryConflict('The native migration preflight fails; no source or backup is published')
    permitted = {source['path'] for source in sources}
    if not state:
        permitted |= {str(memory.root / backup_name(source['relative'])) for source in sources}
    seen = set()
    for item in result['publications']:
        if (not isinstance(item, dict) or set(item) != {'path', 'content'} or not isinstance(item['path'], str)
                or item['path'] not in permitted or item['path'] in seen or not isinstance(item['content'], str)
                or len(item['content'].encode()) > SOURCE_LIMIT or dry_run):
            raise MemoryUnavailable('Native freshness migration changes its fixed publication destinations')
        seen.add(item['path'])
    return result


def run(memory, scope, dry_run, state, *, check_current):
    _request(scope, dry_run, state)
    with memory._transaction() as connection:
        sources = _sources(memory, scope, connection, state)
        signature = _source_signature(sources)
        if dry_run:
            result = _render(memory, sources, True, state)
            if _source_signature(_sources(memory, scope, connection, state)) != signature:
                raise MemoryUnavailable('The migration sources changed during preview')
            check_current()
            return {'ok': result['status'] == 0,
                    'result': {name: result[name] for name in ('status', 'stdout', 'stderr')}}
    output = []
    payload = {'operation': 'freshness_migration', 'state': state, 'source_signature': signature}

    def apply(connection):
        current = _sources(memory, scope, connection, state)
        if _source_signature(current) != signature:
            raise MemoryConflict('The migration sources changed before native rendering')
        result = _render(memory, current, False, state)
        if _source_signature(_sources(memory, scope, connection, state)) != signature:
            raise MemoryConflict('The migration sources changed during native rendering')
        try:
            check_current()
        except MemoryUnavailable as error:
            raise MemoryConflict(str(error)) from error
        publication_paths(memory, connection, scope, payload)
        redirect = ({} if state else {backup_name(source): backup for source, backup
                                      in _backup_destinations(memory, current).items()})
        for item in result['publications']:
            relative = Path(item['path']).relative_to(memory.root).as_posix()
            publish(memory._publication_path(redirect.get(relative, relative)), item['content'].encode())
        output.append({name: result[name] for name in ('status', 'stdout', 'stderr')})
        return {'status': 'committed' if result['publications'] else 'unchanged',
                'artifacts': len(result['publications'])}

    receipt = memory._operation(scope, 'freshness-migration-' + uuid4().hex, payload, apply)
    return {'ok': receipt['status'] in ('committed', 'unchanged'), 'result': output[0] if output else None}
