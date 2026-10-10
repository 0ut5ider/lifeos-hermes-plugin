# ABOUTME: Admits fixed LocalIntelligence inputs and binds native refresh plans to current owner authority.
# ABOUTME: Rechecks source bytes and decoded output before delivering hometown and source selections.
from datetime import datetime, timezone
import json
import hashlib

from .memory_access import MemoryUnavailable, MemoryConflict, _now
from .memory_evidence import _signature
from .memory_local_intelligence import PRIMARY, FALLBACK, SOURCE_CONFIG
from .memory_operational_views import projection
from .memory_policy import CATEGORIES
from .memory_source_review import _retirement_digest
from .memory_sources import authorize, _admit, _source_time, SOURCE_LIMIT, CORPUS_LIMIT
from .memory_tab_freshness import _checked

IDENTITY = 'LIFEOS/USER/PRINCIPAL/PRINCIPAL_IDENTITY.md'
SOURCES = SOURCE_CONFIG
INPUTS = frozenset({IDENTITY, SOURCES})


def _collect(memory, scope, connection, names):
    contents, fingerprints, candidates, total = {}, [], [], 0
    keys = lambda info: (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns)
    for relative in sorted(names):
        path = _checked(memory, memory.root / relative)
        if not path.exists():
            contents[relative] = None
            fingerprints.append((relative, None))
            continue
        before = path.stat()
        if not path.is_file() or before.st_size > SOURCE_LIMIT:
            raise MemoryUnavailable('LocalIntelligence inputs require bounded regular owner files')
        with path.open('rb') as stream: raw = stream.read(SOURCE_LIMIT + 1)
        if len(raw) > SOURCE_LIMIT: raise MemoryUnavailable('A LocalIntelligence input exceeds its byte limit')
        try: content = raw.decode('utf-8')
        except UnicodeError as error: raise MemoryUnavailable('LocalIntelligence inputs require valid UTF-8') from error
        after = _checked(memory, path).stat()
        if keys(before) != keys(after): raise MemoryConflict('A LocalIntelligence input changes during collection')
        decoded = projection(content) if relative.endswith('.json') else content
        if decoded is None: raise MemoryUnavailable('A LocalIntelligence input requires complete JSON')
        total += len(raw) + len(decoded.encode())
        if total > CORPUS_LIMIT: raise MemoryUnavailable('LocalIntelligence inputs exceed their transport limit')
        contents[relative] = content
        fingerprints.append((relative, keys(after), hashlib.sha256(raw).hexdigest()))
        candidates.append((relative, content, decoded, _source_time(after)))
    accepted = memory._native('validate_source_batch', contents=[decoded + '\n' + relative
        for relative, _, decoded, _ in candidates])['accepted'] if candidates else []
    for (relative, content, decoded, timestamp), valid in zip(candidates, accepted, strict=True):
        if valid is not True or _admit(memory, connection, scope, content, relative, timestamp,
                projection=decoded)['excluded']:
            raise MemoryUnavailable('A LocalIntelligence input is excluded under current owner policy')
    return contents, fingerprints


def _output(memory, scope, connection, value):
    content = json.dumps(value, ensure_ascii=False, allow_nan=False)
    decoded = projection(content)
    if (len(content.encode()) > CORPUS_LIMIT or decoded is None
            or memory._native('validate_source_batch', contents=[decoded])['accepted'] != [True]
            or memory._filter_history(connection, scope, decoded, _now(), reviewed=True)['excluded']):
        raise MemoryUnavailable('LocalIntelligence output contains excluded text')


def inputs(memory, scope, operation, arguments, *, check_current):
    if (operation != 'local_inputs' or set(arguments) != {'kind'}
            or not isinstance(arguments['kind'], str) or arguments['kind'] not in {'hometown', 'sources'}):
        raise ValueError('Choose declared LocalIntelligence inputs')
    kind = arguments['kind']
    names = {IDENTITY} if kind == 'hometown' else {SOURCES}
    authorize(scope)
    if not scope.principal:
        raise MemoryUnavailable('LocalIntelligence inputs require the current bound owner')
    check_current()
    with memory._transaction() as connection:
        contents, fingerprints = _collect(memory, scope, connection, names)
        date = datetime.now(timezone.utc).date().isoformat()
        result = memory._native('local_refresh_inputs', kind=kind, contents=contents, date=date)
        _output(memory, scope, connection, result)
        check_current()
        if _collect(memory, scope, connection, names) != (contents, fingerprints):
            raise MemoryConflict('LocalIntelligence inputs change during native rendering')
        check_current()
        return {'ok': True, **result}


def _request(scope):
    authorize(scope)
    if not scope.principal or not CATEGORIES <= set(scope.write):
        raise MemoryUnavailable('LocalIntelligence refresh requires the current unrestricted owner writer')


def publication_paths(memory, scope, payload):
    from pathlib import Path
    _request(scope)
    if (set(payload) != {'operation', 'filename', 'latestSkipped'} or payload['operation'] != 'local_refresh'
            or not isinstance(payload['filename'], str) or type(payload['latestSkipped']) is not bool
            or len(payload['filename'].encode()) > 240 or Path(payload['filename']).name != payload['filename']
            or '\\' in payload['filename'] or not payload['filename'].endswith('_digest.json')):
        raise ValueError('Choose declared LocalIntelligence refresh publication')
    from .memory_local_intelligence import HISTORY
    paths = [HISTORY + '/' + payload['filename']] + ([] if payload['latestSkipped'] else [PRIMARY, FALLBACK])
    for relative in paths:
        path = _checked(memory, memory._publication_path(relative))
        if path.exists() and (not path.is_file() or path.stat().st_size > SOURCE_LIMIT):
            raise MemoryUnavailable('LocalIntelligence refresh requires bounded fixed destinations')
    return paths


def _snapshot(memory, scope, connection, check_current):
    from .memory_local_intelligence import HISTORY
    _request(scope)
    check_current()
    date = datetime.now(timezone.utc).date().isoformat()
    contents, fingerprints = _collect(memory, scope, connection, INPUTS | {PRIMARY, FALLBACK})
    plan = memory._native('local_refresh_inputs', kind='prepare', contents=contents, date=date)
    if (not isinstance(plan, dict) or set(plan) != {'home', 'sources', 'date', 'filename', 'latest'}
            or plan['date'] != date or not isinstance(plan['filename'], str)):
        raise MemoryUnavailable('Native LocalIntelligence preparation changes its declared plan')
    payload = {'operation': 'local_refresh', 'filename': plan['filename'], 'latestSkipped': False}
    publication_paths(memory, scope, payload)
    _output(memory, scope, connection, plan)
    names = INPUTS | {PRIMARY, FALLBACK, HISTORY + '/' + plan['filename']}
    complete, records = _collect(memory, scope, connection, names)
    if ({name: complete[name] for name in contents} != contents
            or [row for row in records if row[0] in contents] != fingerprints):
        raise MemoryConflict('LocalIntelligence inputs change during native preparation')
    check_current()
    if _collect(memory, scope, connection, names) != (complete, records):
        raise MemoryConflict('LocalIntelligence inputs change before preparation delivery')
    if datetime.now(timezone.utc).date().isoformat() != date:
        raise MemoryConflict('LocalIntelligence preparation crosses its native date')
    check_current()
    return {'sources': records, 'plan': plan, 'scope': scope.signature, 'root': str(memory.physical_root),
        'retirement': _retirement_digest(connection)}


def synthesis(memory, scope, operation, arguments, *, check_current):
    from uuid import uuid4
    from .memory_transaction import publish
    _request(scope)
    fields = set() if operation == 'local_refresh_prepare' else {'signature'}
    if operation == 'local_refresh_publish': fields.add('value')
    if set(arguments) != fields: raise ValueError('Choose declared LocalIntelligence refresh arguments')
    with memory._transaction() as connection:
        snapshot = _snapshot(memory, scope, connection, check_current)
        signature = _signature(snapshot)
        if operation == 'local_refresh_prepare': return {'ok': True, 'plan': snapshot['plan'], 'signature': signature}
        if arguments['signature'] != signature:
            raise MemoryConflict('LocalIntelligence inputs or authority change before publication')
        if operation == 'local_refresh_check': return {'ok': True}
        value = arguments['value']
        _output(memory, scope, connection, value)
        result = memory._native('local_refresh_publication', plan=snapshot['plan'], value=value)
        if (not isinstance(result, dict) or set(result) != {'filename', 'content', 'latestSkipped', 'totalItems'}
                or result['filename'] != snapshot['plan']['filename'] or not isinstance(result['content'], str)
                or type(result['latestSkipped']) is not bool or type(result['totalItems']) is not int
                or result['totalItems'] < 0 or len(result['content'].encode()) > SOURCE_LIMIT
                or json.loads(result['content']) != value):
            raise MemoryUnavailable('Native LocalIntelligence publication changes its declared digest')
        _output(memory, scope, connection, result)
        check_current()
    payload = {'operation': 'local_refresh', 'filename': result['filename'], 'latestSkipped': result['latestSkipped']}
    paths = publication_paths(memory, scope, payload)
    content = result['content'].encode()
    published_snapshot = snapshot
    def apply(connection):
        nonlocal published_snapshot
        check_current()
        if _snapshot(memory, scope, connection, check_current) != snapshot:
            raise MemoryConflict('LocalIntelligence publication preserves later source and destination changes')
        _output(memory, scope, connection, value)
        for relative in paths:
            check_current()
            publish(memory._publication_path(relative), content)
        try:
            published_snapshot = _snapshot(memory, scope, connection, check_current)
        except MemoryConflict as error:
            raise MemoryUnavailable('LocalIntelligence recheck requires publication recovery') from error
        for key in snapshot.keys() - {'sources', 'plan'}:
            if published_snapshot[key] != snapshot[key]: raise MemoryUnavailable('LocalIntelligence authority changes during publication and requires recovery')
        for key in snapshot['plan'].keys() - {'latest'}:
            if published_snapshot['plan'][key] != snapshot['plan'][key]:
                raise MemoryUnavailable('LocalIntelligence inputs change during publication and require recovery')
        untouched = lambda record: [row for row in record['sources'] if row[0] not in paths]
        if untouched(published_snapshot) != untouched(snapshot):
            raise MemoryUnavailable('LocalIntelligence inputs change during publication and require recovery')
        for relative in paths:
            if memory._publication_path(relative).read_bytes() != content:
                raise MemoryUnavailable('LocalIntelligence destination changes during publication and requires recovery')
        check_current()
        return {'status': 'committed'}
    receipt = memory._operation(scope, 'local-refresh-' + uuid4().hex, payload, apply,
        publication_digests={relative: hashlib.sha256(content).hexdigest() for relative in paths})
    if receipt['status'] != 'committed': raise MemoryUnavailable('LocalIntelligence publication requires recovery or a current retry')
    with memory._transaction() as connection:
        check_current()
        _output(memory, scope, connection, result)
        if _snapshot(memory, scope, connection, check_current) != published_snapshot:
            raise MemoryConflict('LocalIntelligence publication changes before delivery')
        check_current()
    return {'ok': True, 'summary': {key: result[key] for key in ('filename', 'latestSkipped', 'totalItems')}}
