# ABOUTME: Admits complete fixed Performance histories for native owner aggregates.
# ABOUTME: Rechecks history bytes, optional metadata, private descriptors, and authority before delivery.
from datetime import datetime, timezone
import json
import re
from urllib.parse import urlsplit

from .memory_access import MemoryUnavailable
from .memory_sources import authorize, _admit, _source_time, SOURCE_LIMIT, CORPUS_LIMIT
from .memory_operational_views import projection
from .memory_tab_freshness import _checked
from . import memory_operational_history as history


PREFIX = 'LIFEOS/MEMORY/OBSERVABILITY/'
ROUTES = {
    '/api/performance/cost': ('session-costs.jsonl',),
    '/api/performance/failures': ('tool-failures.jsonl', 'tool-activity.jsonl'),
    '/api/performance/summary': ('session-costs.jsonl', 'tool-failures.jsonl', 'tool-activity.jsonl'),
    '/api/performance/anthropic-cost': ('anthropic-cost.jsonl',),
}
METADATA = PREFIX + 'anthropic-call-sites.json'
SOURCES = frozenset(PREFIX + name for names in ROUTES.values() for name in names) | {METADATA}


def request_target(value):
    if not isinstance(value, str) or len(value) > 256:
        raise ValueError('Performance views require a bounded native route')
    url = urlsplit(value)
    if url.scheme or url.netloc or url.fragment or url.path not in ROUTES:
        raise ValueError('Choose a fixed Performance route')
    if url.query and not (url.path == '/api/performance/cost'
            and re.fullmatch(r'days=[1-9][0-9]{0,3}', url.query)
            and int(url.query[5:]) <= 3660):
        raise ValueError('Performance views require a declared day window')
    return url.path + ('?' + url.query if url.query else '')


def _metadata(memory, scope, connection):
    path = _checked(memory, memory.root / METADATA)
    if not path.exists(): return [], (METADATA, None)
    if not path.is_file(): raise MemoryUnavailable('Performance metadata requires a regular owner file')
    before = path.stat()
    if before.st_size > SOURCE_LIMIT: raise MemoryUnavailable('Performance metadata exceeds its byte limit')
    with path.open('rb') as stream: raw = stream.read(SOURCE_LIMIT + 1)
    if len(raw) > SOURCE_LIMIT: raise MemoryUnavailable('Performance metadata exceeds its byte limit')
    try: content = raw.decode('utf-8')
    except UnicodeError as error:
        raise MemoryUnavailable('Performance metadata requires valid UTF-8') from error
    after = path.stat()
    _checked(memory, path)
    keys = lambda info: (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns)
    if keys(before) != keys(after): raise MemoryUnavailable('Performance metadata changes during collection')
    decoded = projection(content)
    if (decoded is None or memory._native('validate_source_batch', contents=[decoded + '\n' + METADATA])['accepted'] != [True]
            or _admit(memory, connection, scope, content, METADATA, _source_time(after), projection=decoded)['excluded']):
        raise MemoryUnavailable('Performance metadata is excluded under current owner policy')
    return [{'relative': METADATA, 'content': content}], (METADATA, keys(after), raw)


def view(memory, scope, target, *, check_current=None):
    target = request_target(target)
    path = urlsplit(target).path
    authorize(scope)
    if not scope.principal: raise MemoryUnavailable('Performance views require a bound owner')
    if check_current is not None: check_current()
    streamed = {PREFIX + name: None for name in ROUTES[path]}
    with memory._transaction() as connection:
        sources, metadata = _metadata(memory, scope, connection) if path.endswith('/anthropic-cost') else ([], None)
        with history.snapshot(memory, scope, connection, check_current=check_current, sources=streamed,
                require_newline=False, objects_only=False, allow_unfinished_utf8=False) as (descriptor, fingerprints):
            result = memory._native('performance_view', target=target, sources=sources,
                history_descriptor=descriptor, source_descriptors=(descriptor,))
            if check_current is not None: check_current()
            if ([history.fingerprint(memory, relative, sources=streamed) for relative in streamed] != fingerprints
                    or metadata is not None and _metadata(memory, scope, connection) != (sources, metadata)):
                raise MemoryUnavailable('Performance sources change during native rendering')
        if (not isinstance(result, dict) or set(result) != {'status', 'body'}
                or type(result['status']) is not int or result['status'] != 200
                or not isinstance(result['body'], dict) or len(json.dumps(result).encode()) > CORPUS_LIMIT):
            raise MemoryUnavailable('The native Performance view changes its declared response')
        decoded = projection(json.dumps(result))
        if (decoded is None or memory._native('validate_source_batch', contents=[decoded])['accepted'] != [True]
                or memory._filter_history(connection, scope, decoded, datetime.now(timezone.utc).isoformat())['excluded']):
            raise MemoryUnavailable('The native Performance response contains excluded source text')
        if check_current is not None: check_current()
        return result
