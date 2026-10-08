# ABOUTME: Supplies admitted current TELOS and identity sources to the native overview.
# ABOUTME: Rechecks exact source snapshots and owner authority before delivering the rendered response.
from datetime import datetime, timezone
import json

from .memory_access import MemoryUnavailable
from .memory_sources import (STATE_SOURCES, authorize, _markdown_source, _admit,
                             markdown_projection, CORPUS_LIMIT)
from .memory_tab_freshness import _checked


SOURCES = frozenset('LIFEOS/USER/TELOS/' + name + '.md' for name in
    ('TELOS', 'CURRENT', 'MISSION', 'GOALS', 'STRATEGIES', 'CHALLENGES', 'BELIEFS',
     'MODELS', 'NARRATIVES', 'WISDOM', 'PROBLEMS', 'PREDICTIONS', 'FRAMES', 'WRONG',
     'LEARNED', 'IDEAS', 'SPARKS', '2036', 'AUTHORS', 'BOOKS', 'MOVIES', 'TRAUMAS',
     'STATUS', 'PROJECTS')) | STATE_SOURCES | frozenset({
        'LIFEOS/USER/TELOS/CURRENT_STATE/SNAPSHOT.md',
        'LIFEOS/USER/TELOS/IDEAL_STATE/FINANCES.md',
        'LIFEOS/USER/PRINCIPAL/PRINCIPAL_IDENTITY.md',
        'LIFEOS/USER/DIGITAL_ASSISTANT/DA_IDENTITY.md',
        'LIFEOS/USER/PROJECTS.md'})


def _collect(memory, scope, connection):
    candidates, fingerprints = [], []
    total = 0
    for relative in sorted(SOURCES):
        path = _checked(memory, memory.root / relative)
        if not path.exists():
            fingerprints.append((relative, None))
            continue
        before = path.stat()
        source, timestamp = _markdown_source(memory, scope, str(path))
        _checked(memory, path)
        after = path.stat()
        keys = lambda info: (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns)
        if keys(before) != keys(after):
            raise MemoryUnavailable('A TELOS overview source changes during collection')
        fingerprints.append((relative, keys(after), source['content']))
        projection = markdown_projection(memory, relative, source['content'])
        candidates.append((source, timestamp, projection))
        total += len(source['content'].encode()) + len((projection or '').encode())
        if total > CORPUS_LIMIT:
            raise MemoryUnavailable('TELOS overview sources exceed their transport limit')
    checked = memory._native('validate_source_batch', contents=[(projection or '') + '\n' + source['relative']
        for source, _, projection in candidates])['accepted'] if candidates else []
    sources = [{'relative': source['relative'], 'content': source['content']}
        for (source, timestamp, projection), accepted in zip(candidates, checked, strict=True)
        if projection is not None and accepted is True and not _admit(memory, connection, scope,
            source['content'], source['relative'], timestamp, projection=projection)['excluded']]
    if len(json.dumps(sources).encode()) > CORPUS_LIMIT:
        raise MemoryUnavailable('TELOS overview sources exceed their encoded transport limit')
    return sources, fingerprints


def view(memory, scope, *, check_current=None):
    authorize(scope)
    if not scope.principal:
        raise MemoryUnavailable('TELOS overviews require a bound owner')
    if check_current is not None: check_current()
    registry = memory._native('telos_overview_sources').get('sources')
    if (not isinstance(registry, list) or len(registry) != len(SOURCES)
            or any(not isinstance(path, str) for path in registry) or set(registry) != SOURCES):
        raise MemoryUnavailable('Native TELOS overview sources change their declared registry')
    with memory._transaction() as connection:
        sources, fingerprints = _collect(memory, scope, connection)
        result = memory._native('telos_overview', sources=sources)
        if check_current is not None: check_current()
        if _collect(memory, scope, connection) != (sources, fingerprints):
            raise MemoryUnavailable('TELOS overview sources change during native rendering')
        if (not isinstance(result, dict) or set(result) != {'status', 'body'}
                or type(result['status']) is not int or result['status'] != 200
                or not isinstance(result['body'], dict) or len(json.dumps(result).encode()) > CORPUS_LIMIT):
            raise MemoryUnavailable('The native TELOS overview changes its declared response')
        if memory._filter_history(connection, scope, json.dumps(result), datetime.now(timezone.utc).isoformat())['excluded']:
            raise MemoryUnavailable('The native TELOS overview contains excluded source text')
        if check_current is not None: check_current()
        return result
