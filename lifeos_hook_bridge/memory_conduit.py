# ABOUTME: Admits fixed Conduit records and complete events for native owner views.
# ABOUTME: Rechecks source selection and authority and journals native first-read defaults.
from datetime import datetime, timezone
from itertools import islice
import json
import hashlib
import os
import re
from urllib.parse import urlsplit, parse_qs, urlencode
from uuid import uuid4

from .memory_access import MemoryUnavailable, MemoryConflict
from .memory_policy import CATEGORIES
from .memory_sources import authorize, _admit, _source_time, SOURCE_LIMIT, SOURCE_COUNT_LIMIT, CORPUS_LIMIT
from .memory_operational_views import projection
from .memory_tab_freshness import _checked
from .memory_transaction import publish
from . import memory_operational_history as history

PREFIX = 'LIFEOS/USER/CONDUIT/'
CONFIG = PREFIX + 'config.json'
ROUTES = frozenset('/api/conduit' + suffix for suffix in
    ('', '/', '/today', '/recent', '/sources', '/status', '/health', '/insight', '/insight/build'))
INITIALIZING = frozenset({'/api/conduit', '/api/conduit/', '/api/conduit/today', '/api/conduit/sources'})
EVENT_ROUTES = INITIALIZING | {'/api/conduit/status', '/api/conduit/health'}


def request_target(value):
    if not isinstance(value, str) or len(value) > 256:
        raise ValueError('Conduit views require a bounded native route')
    url = urlsplit(value)
    if url.scheme or url.netloc or url.fragment or url.path not in ROUTES:
        raise ValueError('Choose a fixed Conduit route')
    query = parse_qs(url.query, keep_blank_values=True, strict_parsing=True)
    if set(query) - {'days', 'running', 'building'} or any(len(v) != 1 for v in query.values()):
        raise ValueError('Choose declared Conduit state and selectors')
    for key in ('running', 'building'):
        if key in query and query[key][0] not in {'0', '1'}:
            raise ValueError('Choose declared Conduit runtime state')
    if 'days' in query and (url.path != '/api/conduit/recent'
            or re.fullmatch('[1-9][0-9]?', query['days'][0]) is None or int(query['days'][0]) > 90):
        raise ValueError('Choose a Conduit day window from 1 through 90')
    return url.path + ('?' + urlencode({k: v[0] for k, v in query.items()}) if query else '')


def _directory(memory, name):
    path = _checked(memory, memory.root / PREFIX / name)
    if not path.exists(): return [], None
    if not path.is_dir(): raise MemoryUnavailable('Conduit discovery requires its fixed owner directory')
    before = path.stat()
    entries = list(islice(path.iterdir(), SOURCE_COUNT_LIMIT + 1))
    if len(entries) > SOURCE_COUNT_LIMIT: raise MemoryUnavailable('Conduit discovery exceeds its entry limit')
    names = [entry.name for entry in entries]
    after = path.stat()
    _checked(memory, path)
    keys = lambda info: (info.st_dev, info.st_ino, info.st_mtime_ns)
    if keys(before) != keys(after): raise MemoryUnavailable('Conduit discovery changes during selection')
    return names, (keys(after), tuple(names))


def _selection(memory, target, date):
    url = urlsplit(target)
    if url.path == '/api/conduit/insight/build':
        return [CONFIG, PREFIX + 'insights/' + date + '.json'], None
    if url.path in INITIALIZING: return [CONFIG], None
    if url.path == '/api/conduit/recent':
        entries, fingerprint = _directory(memory, 'daily')
        days = int(parse_qs(url.query).get('days', ['7'])[0])
        names = sorted((name for name in entries if name.endswith('.json')),
            key=lambda value: value.encode('utf-16-be', 'surrogatepass'), reverse=True)[:days]
        return [PREFIX + 'daily/' + name for name in names], fingerprint
    if url.path == '/api/conduit/insight':
        today = PREFIX + 'insights/' + date + '.json'
        present = _checked(memory, memory.root / today).exists()
        entries, fingerprint = _directory(memory, 'insights')
        names = sorted(name for name in entries if re.fullmatch(r'\d{4}-\d{2}-\d{2}\.json', name))
        selected = today if present else PREFIX + 'insights/' + names[-1] if names else None
        # Keep the missing current-day file in the fingerprint even when an older read is selected.
        return list(dict.fromkeys([today] + ([selected] if selected else []))), fingerprint
    return [], None


def _collect(memory, scope, connection, target, date):
    names, directory = _selection(memory, target, date)
    sources, fingerprints, total = [], [], 0
    keys = lambda info: (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns)
    for relative in names:
        path = _checked(memory, memory.root / relative)
        if not path.exists():
            fingerprints.append((relative, None))
            continue
        if not path.is_file(): raise MemoryUnavailable('Conduit records require regular owner files')
        before = path.stat()
        if before.st_size > SOURCE_LIMIT: raise MemoryUnavailable('A Conduit record exceeds its byte limit')
        with path.open('rb') as stream: raw = stream.read(SOURCE_LIMIT + 1)
        if len(raw) > SOURCE_LIMIT: raise MemoryUnavailable('A Conduit record exceeds its byte limit')
        try: content = raw.decode('utf-8')
        except UnicodeError as error: raise MemoryUnavailable('Conduit records require valid UTF-8') from error
        after = path.stat()
        _checked(memory, path)
        if keys(before) != keys(after): raise MemoryUnavailable('A Conduit record changes during collection')
        decoded = projection(content)
        if decoded is None: raise MemoryUnavailable('Conduit records require complete JSON')
        total += len(raw) + len(decoded.encode())
        if total > CORPUS_LIMIT: raise MemoryUnavailable('Conduit records exceed their transport limit')
        if (memory._native('validate_source_batch', contents=[decoded + '\n' + relative])['accepted'] != [True]
                or _admit(memory, connection, scope, content, relative, _source_time(after), projection=decoded)['excluded']):
            raise MemoryUnavailable('A Conduit record is excluded under current owner policy')
        sources.append({'relative': relative, 'content': content})
        fingerprints.append((relative, keys(after), raw))
    if _selection(memory, target, date) != (names, directory):
        raise MemoryUnavailable('Conduit record selection changes during collection')
    return sources, (directory, fingerprints)


def _descriptor_digest(descriptor):
    digest = hashlib.sha256()
    offset = 0
    while chunk := os.pread(descriptor, 128 * 1024, offset):
        digest.update(chunk)
        offset += len(chunk)
    return digest.hexdigest()


def publication_paths(memory, scope, payload):
    authorize(scope)
    if not scope.principal or not CATEGORIES <= set(scope.write):
        raise MemoryUnavailable('Conduit initialization requires the current unrestricted owner writer')
    if payload != {'operation': 'conduit_initialize'}:
        raise MemoryUnavailable('Choose native Conduit default initialization')
    _checked(memory, memory._publication_path(CONFIG))
    return [CONFIG]


def _initialize(memory, scope, target, date, sources, fingerprints, streamed, event_fingerprints, admitted_digest, check_current):
    defaults = memory._native('conduit_defaults').get('content')
    if not isinstance(defaults, str) or len(defaults.encode()) > SOURCE_LIMIT:
        raise MemoryUnavailable('Native Conduit defaults change their declared response')
    current = None
    def apply(connection):
        nonlocal current
        if check_current is not None: check_current()
        if (_collect(memory, scope, connection, target, date) != (sources, fingerprints)
                or [history.fingerprint(memory, relative, sources=streamed) for relative in streamed] != event_fingerprints):
            raise MemoryConflict('Conduit sources change before initialization')
        publication_paths(memory, scope, {'operation': 'conduit_initialize'})
        decoded = projection(defaults)
        if (decoded is None or memory._native('validate_source_batch', contents=[decoded])['accepted'] != [True]
                or memory._filter_history(connection, scope, decoded, datetime.now(timezone.utc).isoformat())['excluded']):
            raise MemoryUnavailable('Native Conduit defaults contain excluded text')
        if check_current is not None: check_current()
        with history.snapshot(memory, scope, connection, check_current=check_current, sources=streamed,
                require_newline=False, objects_only=False, allow_unfinished_utf8=False) as (descriptor, _):
            if _descriptor_digest(descriptor) != admitted_digest:
                raise MemoryConflict('Conduit event admission changes before initialization')
            if check_current is not None: check_current()
            publish(memory._publication_path(CONFIG), defaults.encode())
        if check_current is not None: check_current()
        current = _collect(memory, scope, connection, target, date)
        if current[0] != [{'relative': CONFIG, 'content': defaults}]:
            raise MemoryUnavailable('The published Conduit defaults change before delivery')
        return {'status': 'committed', 'artifacts': 1}
    receipt = memory._operation(scope, 'conduit-initialize-' + uuid4().hex,
        {'operation': 'conduit_initialize'}, apply,
        publication_digests={CONFIG: hashlib.sha256(defaults.encode()).hexdigest()})
    if receipt['status'] != 'committed' or current is None:
        raise MemoryUnavailable('Native Conduit initialization needs recovery or a current retry')
    return current


def view(memory, scope, target, *, check_current=None):
    target = request_target(target)
    url = urlsplit(target)
    authorize(scope)
    if not scope.principal: raise MemoryUnavailable('Conduit views require a bound owner')
    if check_current is not None: check_current()
    if url.path == '/api/conduit/insight/build':
        raise MemoryUnavailable('Conduit generation requires governed background job publication')
    date = datetime.now().strftime('%Y-%m-%d')
    streamed = {PREFIX + 'events/' + date + '.jsonl': None} if url.path in EVENT_ROUTES else {}
    query = parse_qs(url.query)
    native_target = url.path + ('?days=' + query['days'][0] if 'days' in query else '')
    with memory._transaction() as connection:
        sources, fingerprints = _collect(memory, scope, connection, target, date)
        with history.snapshot(memory, scope, connection, check_current=check_current, sources=streamed,
                require_newline=False, objects_only=False, allow_unfinished_utf8=False) as (descriptor, event_fingerprints):
            admitted_digest = _descriptor_digest(descriptor)
            result = memory._native('conduit_view', sources=sources, target=native_target, date=date,
                running=query.get('running') == ['1'], building=query.get('building') == ['1'],
                history_descriptor=descriptor, source_descriptors=(descriptor,))
            if check_current is not None: check_current()
            if (_collect(memory, scope, connection, target, date) != (sources, fingerprints)
                    or [history.fingerprint(memory, relative, sources=streamed) for relative in streamed] != event_fingerprints):
                raise MemoryUnavailable('Conduit sources change during native rendering')
        if (not isinstance(result, dict) or set(result) != {'status', 'body'} or type(result['status']) is not int
                or result['status'] != 200 or not isinstance(result['body'], (dict, list))
                or len(json.dumps(result).encode()) > CORPUS_LIMIT):
            raise MemoryUnavailable('The native Conduit view changes its declared response')
        decoded = projection(json.dumps(result))
        if (decoded is None or memory._native('validate_source_batch', contents=[decoded])['accepted'] != [True]
                or memory._filter_history(connection, scope, decoded, datetime.now(timezone.utc).isoformat())['excluded']):
            raise MemoryUnavailable('The native Conduit response contains excluded text')
        if check_current is not None: check_current()
    if url.path in INITIALIZING and not any(source['relative'] == CONFIG for source in sources):
        sources, fingerprints = _initialize(memory, scope, target, date, sources, fingerprints,
            streamed, event_fingerprints, admitted_digest, check_current)
    with memory._transaction() as connection:
        if check_current is not None: check_current()
        if (_collect(memory, scope, connection, target, date) != (sources, fingerprints)
                or [history.fingerprint(memory, relative, sources=streamed) for relative in streamed] != event_fingerprints
                or datetime.now().strftime('%Y-%m-%d') != date):
            raise MemoryUnavailable('Conduit sources change before delivery')
        with history.snapshot(memory, scope, connection, check_current=check_current, sources=streamed,
                require_newline=False, objects_only=False, allow_unfinished_utf8=False) as (descriptor, _):
            if _descriptor_digest(descriptor) != admitted_digest:
                raise MemoryUnavailable('Conduit event admission changes before delivery')
        if memory._filter_history(connection, scope, decoded, datetime.now(timezone.utc).isoformat())['excluded']:
            raise MemoryUnavailable('Conduit response authority changes before delivery')
        if check_current is not None: check_current()
    return result
