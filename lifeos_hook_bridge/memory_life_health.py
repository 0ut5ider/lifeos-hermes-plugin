# ABOUTME: Collects admitted health markdown and lab filenames within the selected owner directory.
# ABOUTME: Preserves native health rendering while checking source metadata and authority before response delivery.
from datetime import datetime, timezone
from itertools import islice
import json

from .memory_access import MemoryUnavailable
from .memory_sources import authorize, _admit, _source_time, SOURCE_LIMIT, CORPUS_LIMIT, SOURCE_COUNT_LIMIT
from .memory_tab_freshness import _checked


def _collect(memory, scope, connection):
    directory = _checked(memory, memory.root / 'LIFEOS/USER/HEALTH')
    if directory.exists() and not directory.is_dir():
        raise MemoryUnavailable('Health sources require the fixed owner directory')
    entries = list(islice(directory.iterdir(), SOURCE_COUNT_LIMIT + 1)) if directory.exists() else []
    if len(entries) > SOURCE_COUNT_LIMIT:
        raise MemoryUnavailable('Health discovery exceeds its source count limit')
    fingerprints = [tuple(str(path) for path in entries)]
    sources = []
    times = []
    total = 0
    for path in entries:
        if not (path.name.endswith('.md') and path.name != 'README.md' or path.name.startswith('lab_results')):
            continue
        _checked(memory, path)
        before = path.stat()
        content = ''
        if path.is_file() and path.suffix == '.md':
            if before.st_size > SOURCE_LIMIT:
                raise MemoryUnavailable('A health source exceeds its byte limit')
            content = path.read_text(encoding='utf-8')
            total += len(content.encode())
            if total > CORPUS_LIMIT:
                raise MemoryUnavailable('Health sources exceed their transport limit')
        after = path.stat()
        keys = lambda info: (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns)
        if keys(before) != keys(after):
            raise MemoryUnavailable('A health source changes during collection')
        _checked(memory, path)
        fingerprints.append((str(path), keys(after), content))
        sources.append({'filename': path.name, 'content': content})
        times.append(_source_time(after))
    if len(json.dumps(sources).encode()) > CORPUS_LIMIT:
        raise MemoryUnavailable('Health sources exceed their transport limit')
    checked = memory._native('validate_source_batch', contents=[source['content'] + '\n' + source['filename']
        for source in sources])['accepted'] if sources else []
    admitted = [source for source, timestamp, accepted in zip(sources, times, checked, strict=True)
        if accepted is True and not _admit(memory, connection, scope, source['content'],
            'LIFEOS/USER/HEALTH/' + source['filename'], timestamp)['excluded']]
    return admitted, fingerprints


def view(memory, scope, *, check_current=None):
    authorize(scope)
    if not scope.principal:
        raise MemoryUnavailable('Health views require a bound owner')
    if check_current is not None: check_current()
    with memory._transaction() as connection:
        sources, fingerprints = _collect(memory, scope, connection)
        result = memory._native('life_health_view', sources=sources)
        if check_current is not None: check_current()
        if _collect(memory, scope, connection) != (sources, fingerprints):
            raise MemoryUnavailable('Health sources change during native rendering')
        if (not isinstance(result, dict) or set(result) != {'status', 'body'}
                or type(result['status']) is not int or result['status'] != 200
                or not isinstance(result['body'], dict) or len(json.dumps(result).encode()) > CORPUS_LIMIT):
            raise MemoryUnavailable('The native health view changes its declared response')
        if memory._filter_history(connection, scope, json.dumps(result), datetime.now(timezone.utc).isoformat())['excluded']:
            raise MemoryUnavailable('The native health view contains excluded source text')
        if check_current is not None: check_current()
        return result
