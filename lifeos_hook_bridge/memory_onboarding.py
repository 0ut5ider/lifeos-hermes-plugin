# ABOUTME: Supplies admitted identity and personalization sources to native onboarding.
# ABOUTME: Rechecks source bytes, template marker presence, and current owner authority before delivery.
from datetime import datetime, timezone
import json

from .memory_access import MemoryUnavailable
from .memory_sources import (authorize, _markdown_source, _admit, markdown_projection,
                             _source_time, SOURCE_LIMIT, CORPUS_LIMIT)
from .memory_tab_freshness import _checked


MARKER = 'LIFEOS/USER/.template-mode'
SOURCES = frozenset('LIFEOS/USER/TELOS/' + name + '.md' for name in
    ('TELOS', 'MISSION', 'GOALS', 'PROBLEMS', 'STRATEGIES', 'CHALLENGES')) | frozenset({
        MARKER, 'LIFEOS/USER/DIGITAL_ASSISTANT/DA_IDENTITY.md'})


def _collect(memory, scope, connection):
    candidates, fingerprints = [], []
    total = 0
    keys = lambda info: (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns)
    for relative in sorted(SOURCES):
        path = _checked(memory, memory.root / relative)
        if not path.exists():
            fingerprints.append((relative, None))
            continue
        if not path.is_file():
            raise MemoryUnavailable('Onboarding sources require regular owner files')
        before = path.stat()
        if relative == MARKER:
            if before.st_size > SOURCE_LIMIT:
                raise MemoryUnavailable('The onboarding marker exceeds its byte limit')
            try:
                with path.open('rb') as stream: raw = stream.read(SOURCE_LIMIT + 1)
                if len(raw) > SOURCE_LIMIT:
                    raise MemoryUnavailable('The onboarding marker exceeds its byte limit')
                content = raw.decode('utf-8')
            except UnicodeError as error:
                raise MemoryUnavailable('The onboarding marker requires valid UTF-8') from error
            timestamp = _source_time(before)
            projection = content
        else:
            source, timestamp = _markdown_source(memory, scope, str(path))
            content = source['content']
            projection = markdown_projection(memory, relative, content)
        _checked(memory, path)
        after = path.stat()
        if keys(before) != keys(after):
            raise MemoryUnavailable('An onboarding source changes during collection')
        fingerprints.append((relative, keys(after), content))
        candidates.append((relative, content, timestamp, projection))
        total += len(content.encode()) + len((projection or '').encode())
        if total > CORPUS_LIMIT:
            raise MemoryUnavailable('Onboarding sources exceed their transport limit')
    checked = memory._native('validate_source_batch', contents=[(projection or '') + '\n' + relative
        for relative, _, _, projection in candidates])['accepted'] if candidates else []
    sources = [{'relative': relative, 'content': content}
        for (relative, content, timestamp, projection), accepted in zip(candidates, checked, strict=True)
        if projection is not None and accepted is True and not _admit(memory, connection, scope,
            content, relative, timestamp, projection=projection)['excluded']]
    if len(json.dumps(sources).encode()) > CORPUS_LIMIT:
        raise MemoryUnavailable('Onboarding sources exceed their encoded transport limit')
    return sources, fingerprints


def view(memory, scope, *, check_current=None):
    authorize(scope)
    if not scope.principal:
        raise MemoryUnavailable('Onboarding views require a bound owner')
    if check_current is not None: check_current()
    registry = memory._native('onboarding_sources').get('sources')
    if (not isinstance(registry, list) or len(registry) != len(SOURCES)
            or any(not isinstance(path, str) for path in registry) or set(registry) != SOURCES):
        raise MemoryUnavailable('Native onboarding sources change their declared registry')
    with memory._transaction() as connection:
        sources, fingerprints = _collect(memory, scope, connection)
        result = memory._native('onboarding_view', sources=sources)
        if check_current is not None: check_current()
        if _collect(memory, scope, connection) != (sources, fingerprints):
            raise MemoryUnavailable('Onboarding sources change during native rendering')
        if (not isinstance(result, dict) or set(result) != {'status', 'body'}
                or type(result['status']) is not int or result['status'] != 200
                or not isinstance(result['body'], dict) or len(json.dumps(result).encode()) > CORPUS_LIMIT):
            raise MemoryUnavailable('The native onboarding view changes its declared response')
        if memory._filter_history(connection, scope, json.dumps(result), datetime.now(timezone.utc).isoformat())['excluded']:
            raise MemoryUnavailable('The native onboarding view contains excluded source text')
        if check_current is not None: check_current()
        return result
