# ABOUTME: Collects admitted local project, current focus, and algorithm session sources for native work views.
# ABOUTME: Rechecks fixed physical sources and owner authority before returning the complete native response.
from datetime import datetime, timezone
import json
from pathlib import Path

from .memory_access import MemoryUnavailable
from .memory_sources import authorize, _admit, _text_source, CORPUS_LIMIT, json_projection
from .memory_tab_freshness import _checked

SOURCES = ('LIFEOS/USER/PROJECTS.md', 'LIFEOS/USER/TELOS/TELOS.md',
           'LIFEOS/USER/TELOS/CURRENT.md', 'LIFEOS/MEMORY/STATE/work.json')


def _collect(memory, scope, connection):
    candidates, fingerprints = [], []
    total = 0
    for relative in SOURCES:
        path = _checked(memory, memory.root / relative)
        if not path.exists():
            fingerprints.append((relative, None))
            continue
        before = path.stat()
        source, timestamp = _text_source(memory, scope, str(path), suffix=Path(relative).suffix,
            evidence=relative.endswith('.json'), preserve_newlines=True)
        _checked(memory, path)
        after = path.stat()
        keys = lambda info: (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns)
        if keys(before) != keys(after):
            raise MemoryUnavailable('A local work source changes during collection')
        fingerprints.append((relative, keys(after), source['content']))
        projection = json_projection(source['content']) if relative.endswith('.json') else source['content']
        projection = source['content'] + '\n' + projection if projection is not None else None
        candidates.append((source, timestamp, projection))
        total += len(source['content'].encode()) + len((projection or '').encode())
        if total > CORPUS_LIMIT:
            raise MemoryUnavailable('Local work sources exceed their transport limit')
    checked = memory._native('validate_source_batch', contents=[(projection or '') + '\n' + source['relative']
        for source, _, projection in candidates])['accepted'] if candidates else []
    admitted = [{'relative': source['relative'], 'content': source['content']}
        for (source, timestamp, projection), accepted in zip(candidates, checked, strict=True)
        if projection is not None and accepted is True and not _admit(memory, connection, scope,
            source['content'], source['relative'], timestamp, projection=projection)['excluded']]
    return admitted, fingerprints


def view(memory, scope, *, check_current=None):
    authorize(scope)
    if not scope.principal:
        raise MemoryUnavailable('Local work views require a bound owner')
    if check_current is not None: check_current()
    with memory._transaction() as connection:
        sources, fingerprints = _collect(memory, scope, connection)
        result = memory._native('life_work_view', sources=sources)
        if check_current is not None: check_current()
        if _collect(memory, scope, connection) != (sources, fingerprints):
            raise MemoryUnavailable('Local work sources change during native rendering')
        if (not isinstance(result, dict) or set(result) != {'status', 'body'}
                or type(result['status']) is not int or result['status'] != 200
                or not isinstance(result['body'], dict) or len(json.dumps(result).encode()) > CORPUS_LIMIT):
            raise MemoryUnavailable('The native local work view changes its declared response')
        if memory._filter_history(connection, scope, json.dumps(result), datetime.now(timezone.utc).isoformat())['excluded']:
            raise MemoryUnavailable('The native local work view contains excluded source text')
        if check_current is not None: check_current()
        return result
