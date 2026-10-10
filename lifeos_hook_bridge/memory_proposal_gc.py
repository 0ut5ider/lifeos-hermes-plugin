# ABOUTME: Admits native proposal cleanup sources and confines its owner publication paths.
# ABOUTME: Rechecks source revisions and caller permissions before a journaled cleanup.
from collections import Counter
from datetime import datetime, timezone
import json
import os
from pathlib import Path
from uuid import uuid4

from .memory_access import MemoryConflict, MemoryUnavailable
from .memory_sources import SOURCE_LIMIT, authorize, _text_source, _admit, markdown_projection
from .memory_transaction import publish


TARGETS = ('LIFEOS/USER/CONFIG/OPERATIONAL_RULES.md', 'LIFEOS/USER/PROJECTS.md',
    'LIFEOS/USER/PRINCIPAL/PRINCIPAL_IDENTITY.md', 'LIFEOS/USER/DIGITAL_ASSISTANT/DA_IDENTITY.md')
LOG = 'LIFEOS/MEMORY/OBSERVABILITY/proposal-gc.jsonl'


def _target(memory, relative):
    path = memory._publication_path(relative)
    prefix = 'LIFEOS/USER' if relative in TARGETS else 'LIFEOS'
    physical = memory.root.parent / '.config/LIFEOS/USER' / Path(relative).relative_to(prefix)
    if (path.resolve() != physical or path.is_symlink()
            or path.exists() and (not path.is_file() or path.stat().st_uid != os.getuid()
                                  or path.stat().st_nlink != 1 or path.stat().st_size > SOURCE_LIMIT)):
        raise MemoryUnavailable('Proposal cleanup changes its fixed owner destination')
    return path


def _collect(memory, scope, connection):
    authorize(scope)
    sources = []
    for relative in TARGETS:
        path = _target(memory, relative)
        if not path.exists():
            continue
        source, timestamp = _text_source(memory, scope, str(path), derived_sync=True, preserve_newlines=True)
        projection = markdown_projection(memory, relative, source['content'])
        accepted = memory._native('validate_source_batch', contents=[(projection or '') + '\n' + source['path']])['accepted']
        if (projection is None or accepted != [True]
                or _admit(memory, connection, scope, source['content'], relative, timestamp, projection=projection)['excluded']):
            raise MemoryUnavailable('Proposal cleanup contains an excluded source')
        sources.append(source)
    return sources


def publication_paths(memory, scope, payload):
    authorize(scope)
    if not {'principal', 'assistant', 'project'} <= set(scope.write):
        raise MemoryUnavailable('Proposal cleanup requires unrestricted owner write access')
    if not isinstance(payload.get('sources'), list):
        raise MemoryUnavailable('Proposal cleanup requires a reviewed source revision')
    for relative in (*TARGETS, LOG):
        _target(memory, relative)
    return [*TARGETS, LOG]


def _render(memory, sources, auto, route):
    result = memory._native('proposal_gc', sources={row['relative']:row['content'] for row in sources},
                           auto=auto, route=route)
    if (set(result) != {'removals', 'skipped', 'writes', 'routes'}
            or any(not isinstance(result[key], list) for key in result)
            or any(not isinstance(row, dict) or set(row) != {'file', 'content'}
                   or row['file'] not in TARGETS or not isinstance(row['content'], str)
                   or len(row['content'].encode()) > SOURCE_LIMIT for row in result['writes'])
            or len({row['file'] for row in result['writes']}) != len(result['writes'])):
        raise MemoryUnavailable('Native proposal cleanup changes its publication contract')
    return result


def run(memory, scope, *, apply, auto, route, check_current):
    if any(type(value) is not bool for value in (apply, auto, route)) or auto and not apply:
        raise ValueError('Choose supported native proposal cleanup modes')
    with memory._transaction() as connection:
        sources = _collect(memory, scope, connection)
        result = _render(memory, sources, auto, route)
        if _collect(memory, scope, connection) != sources:
            raise MemoryConflict('Proposal cleanup sources change during rendering')
        check_current()
    if not apply or route:
        return {'ok':True, 'removals':result['removals'], 'skipped':result['skipped'],
                'routes':result['routes'], 'artifacts':0}
    payload = {'operation':'proposal_gc', 'sources':sources, 'auto':auto}

    def commit(connection):
        if _collect(memory, scope, connection) != sources:
            raise MemoryConflict('Proposal cleanup sources change before publication')
        check_current()
        publication_paths(memory, scope, payload)
        for row in result['writes']:
            check_current()
            publish(_target(memory, row['file']), row['content'].encode())
        log = _target(memory, LOG)
        previous = log.read_bytes() if log.exists() else b''
        entry = {'ts':datetime.now(timezone.utc).isoformat(), 'applied':True, 'auto':auto,
                 'removed':len(result['removals']), 'byReason':dict(Counter(row['reason'] for row in result['removals'])),
                 'skipped':result['skipped']}
        content = previous + (json.dumps(entry) + '\n').encode()
        if len(content) > SOURCE_LIMIT:
            raise MemoryUnavailable('Proposal cleanup log exceeds its supported size')
        check_current()
        publish(log, content)
        check_current()
        return {'status':'committed', 'artifacts':len(result['writes'])}

    receipt = memory._operation(scope, 'proposal-gc-' + uuid4().hex, payload, commit)
    return {'ok':receipt['status'] == 'committed', 'removals':result['removals'],
            'skipped':result['skipped'], 'routes':result['routes'], 'artifacts':receipt.get('artifacts', 0)}
