# ABOUTME: Admits fixed session and event snapshots for native operational dashboard readers.
# ABOUTME: Rechecks physical sources and current owner authority without retaining native process caches.
from collections import deque
from contextlib import nullcontext
from datetime import datetime, timezone
import json

from .memory_access import MemoryUnavailable
from .memory_history import project_value
from .memory_sources import (authorize, _admit, _source_time, SOURCE_LIMIT,
                             SOURCE_COUNT_LIMIT, CORPUS_LIMIT)
from .memory_tab_freshness import _checked
from . import memory_operational_history as history


PREFIX = 'LIFEOS/MEMORY/'
ROUTES = {
    '/api/algorithm': ('STATE/work.json', 'STATE/work-events.jsonl', 'OBSERVABILITY/tool-activity.jsonl'),
    '/api/agents': ('OBSERVABILITY/subagent-events.jsonl',),
    '/api/events/recent': ('VOICE/voice-events.jsonl', 'OBSERVABILITY/tool-failures.jsonl',
                          'OBSERVABILITY/subagent-events.jsonl', 'OBSERVABILITY/tool-activity.jsonl'),
    '/api/observability/voice-events': ('VOICE/voice-events.jsonl',),
    '/api/observability/tool-failures': ('OBSERVABILITY/tool-failures.jsonl',),
    '/api/novelty': ('STATE/novelty-state.json',),
}
CAPABILITY_WINDOWS = {'/api/capabilities': 4_000_000, '/api/capabilities?window=60': 4_000_000,
                     '/api/capabilities?window=360': 10_000_000, '/api/capabilities?window=1440': 20_000_000}
ROUTES.update({target: ('OBSERVABILITY/tool-activity.jsonl', 'OBSERVABILITY/subagent-events.jsonl')
               for target in CAPABILITY_WINDOWS})
SOURCES = frozenset(PREFIX + name for names in ROUTES.values() for name in names)
TAIL_LIMIT = 1024 * 1024


PROJECTION_FIELD_LIMIT = 10000


def projection(content, *, field_limit=PROJECTION_FIELD_LIMIT):
    try:
        value = json.loads(content)
        strings = []
        def collect(text):
            if len(strings) >= field_limit:
                raise ValueError('Operational source projections exceed their field limit')
            strings.append(text)
            return False
        project_value(value, collect)
        result = '\n'.join((content, json.dumps(value, ensure_ascii=False, allow_nan=False), *strings))
        if len(result.encode()) > CORPUS_LIMIT: return None
        return result
    except (ValueError, RecursionError, UnicodeError):
        return None


def _timestamp(row, fallback):
    for key in ('timestamp', 'ts', 'updatedAt', 'started'):
        value = row.get(key)
        if not isinstance(value, str): continue
        try:
            if datetime.fromisoformat(value.replace('Z', '+00:00')).tzinfo is not None: return value
        except ValueError: pass
    return fallback


def _collect(memory, scope, connection, target, *, admit=True):
    fingerprints, candidates = [], []
    keys = lambda info: (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns)
    for name in ROUTES[target]:
        relative = PREFIX + name
        if (target == '/api/algorithm' and relative in history.SOURCES) or target in CAPABILITY_WINDOWS: continue
        path = _checked(memory, memory.root / relative)
        if not path.exists():
            fingerprints.append((relative, None))
            continue
        if not path.is_file():
            raise MemoryUnavailable('Operational sources require regular owner files')
        before = path.stat()
        full = name.endswith('.json')
        limit = SOURCE_LIMIT if name.endswith('.json') else TAIL_LIMIT
        if full and before.st_size > limit:
            raise MemoryUnavailable('An operational source exceeds its complete snapshot limit')
        offset = 0 if full else max(0, before.st_size - TAIL_LIMIT)
        with path.open('rb') as stream:
            stream.seek(offset)
            raw = stream.read(before.st_size - offset + 1)
        if len(raw) != before.st_size - offset:
            raise MemoryUnavailable('An operational source changes during its byte read')
        after = path.stat()
        _checked(memory, path)
        if keys(before) != keys(after):
            raise MemoryUnavailable('An operational source changes during collection')
        fingerprints.append((relative, keys(after), raw))
        if not admit: continue
        if offset:
            newline = raw.find(b'\n')
            raw = raw[newline + 1:] if newline >= 0 else b''
        try: content = raw.decode('utf-8')
        except UnicodeError as error:
            raise MemoryUnavailable('Operational sources require valid UTF-8') from error
        if name.endswith('.json'):
            try: value = json.loads(content)
            except (ValueError, RecursionError): continue
            if isinstance(value, dict) or target == '/api/novelty':
                candidates.append((relative, content, _source_time(after), projection(content), content))
            continue
        maximum = 100 if target != '/api/events/recent' or name == 'OBSERVABILITY/tool-activity.jsonl' else 50
        rows = deque(maxlen=maximum)
        for line in content.split('\n'):
            if not line: continue
            try: row = json.loads(line)
            except (ValueError, RecursionError): continue
            if not isinstance(row, dict): continue
            rows.append((row, line))
        for row, line in rows:
            if len(line.encode()) > SOURCE_LIMIT:
                raise MemoryUnavailable('An operational event exceeds its byte limit')
            candidates.append((relative, line, _timestamp(row, _source_time(after)), projection(line), content))
    if len(candidates) > SOURCE_COUNT_LIMIT:
        raise MemoryUnavailable('Operational sources exceed their total record limit')
    contents = [(decoded or '') + '\n' + relative for relative, _, _, decoded, _ in candidates]
    if len(json.dumps(contents).encode()) > CORPUS_LIMIT:
        raise MemoryUnavailable('Operational projections exceed their transport limit')
    checked = memory._native('validate_source_batch', contents=contents)['accepted'] if candidates else []
    admitted = {}
    for (relative, content, timestamp, decoded, original), accepted in zip(candidates, checked, strict=True):
        if decoded is not None and accepted is True and not _admit(memory, connection, scope,
                content, relative, timestamp, projection=decoded, review_content=original)['excluded']:
            admitted.setdefault(relative, []).append(content)
    sources = [{'relative': relative, 'content': '\n'.join(lines) + ('\n' if relative.endswith('.jsonl') else '')}
               for relative, lines in admitted.items()]
    if len(json.dumps(sources).encode()) > CORPUS_LIMIT:
        raise MemoryUnavailable('Operational source snapshots exceed their transport limit')
    return sources, fingerprints


def view(memory, scope, target, *, check_current=None):
    if target not in ROUTES: raise ValueError('Choose a fixed operational read route')
    authorize(scope)
    if not scope.principal: raise MemoryUnavailable('Operational views require a bound owner')
    if check_current is not None: check_current()
    with memory._transaction() as connection:
        streamed = history.SOURCES if target == '/api/algorithm' else ({
            PREFIX + 'OBSERVABILITY/tool-activity.jsonl': CAPABILITY_WINDOWS[target],
            PREFIX + 'OBSERVABILITY/subagent-events.jsonl': 500_000} if target in CAPABILITY_WINDOWS else None)
        current = history.snapshot(memory, scope, connection, check_current=check_current,
            sources=streamed, require_newline=target == '/api/algorithm') if streamed is not None else nullcontext((None, []))
        with current as (descriptor, history_fingerprints):
            sources, fingerprints = _collect(memory, scope, connection, target)
            arguments = {} if descriptor is None else {'history_descriptor': descriptor}
            result = memory._native('operational_view', target=target, sources=sources,
                source_descriptors=() if descriptor is None else (descriptor,), **arguments)
            if check_current is not None: check_current()
            if (_collect(memory, scope, connection, target, admit=False)[1] != fingerprints
                    or streamed is not None and
                    [history.fingerprint(memory, relative, sources=streamed) for relative in streamed] != history_fingerprints):
                raise MemoryUnavailable('Operational sources change during native rendering')
        if (not isinstance(result, dict) or set(result) != {'status', 'body'}
                or type(result['status']) is not int or result['status'] != 200
                or target != '/api/novelty' and not isinstance(result['body'], (dict, list))
                or len(json.dumps(result).encode()) > CORPUS_LIMIT):
            raise MemoryUnavailable('The native operational view changes its declared response')
        if memory._filter_history(connection, scope, json.dumps(result), datetime.now(timezone.utc).isoformat())['excluded']:
            raise MemoryUnavailable('The native operational view contains excluded source text')
        if check_current is not None: check_current()
        return result
