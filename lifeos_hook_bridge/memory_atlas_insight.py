# ABOUTME: Admits current Atlas graph metrics before native insight generation.
# ABOUTME: Binds source and owner revisions and journals one fixed private narrative cache.
from datetime import datetime
import json
import hashlib
import re
from uuid import uuid4

from .memory_access import MemoryUnavailable, MemoryConflict, _now
from .memory_atlas import CACHE, _collect, _graph, source_path
from .memory_evidence import _signature
from .memory_policy import CATEGORIES
from .memory_sources import authorize, SOURCE_LIMIT, CORPUS_LIMIT, json_projection
from .memory_source_review import _retirement_digest
from .memory_transaction import publish


def _request(scope):
    authorize(scope)
    if not scope.principal or not CATEGORIES <= set(scope.write):
        raise MemoryUnavailable('Atlas publication requires the current unrestricted owner writer')


def publication_paths(memory, scope, payload):
    _request(scope)
    if payload != {'operation': 'atlas_insight'}:
        raise ValueError('Choose declared Atlas insight publication')
    path = source_path(memory, CACHE)
    if path.exists() and (not path.is_file() or path.stat().st_size > SOURCE_LIMIT):
        raise MemoryUnavailable('Atlas insight requires its bounded fixed cache')
    return [CACHE]


def _admit_output(memory, scope, connection, value):
    content = json.dumps(value, ensure_ascii=False, allow_nan=False)
    decoded = json_projection(content)
    if (len(content.encode()) > CORPUS_LIMIT or decoded is None
            or memory._native('validate_source_batch', contents=[decoded])['accepted'] != [True]
            or memory._filter_history(connection, scope, decoded, _now(), reviewed=True)['excluded']):
        raise MemoryUnavailable('Atlas insight output contains excluded text')


def _snapshot(memory, scope, connection, check_current):
    check_current()
    sources = _collect(memory, scope, connection, insights=True)
    graph = _graph(memory, scope, connection)
    metrics = graph[0]['metrics'] if graph else None
    plan = memory._native('atlas_insight_plan', metrics=metrics)
    if (not isinstance(plan, dict) or set(plan) != {'metrics', 'hash'} or plan['metrics'] != metrics
            or (plan['hash'] is not None if metrics is None else
                not isinstance(plan['hash'], str) or re.fullmatch('[0-9a-f]{16}', plan['hash']) is None)):
        raise MemoryUnavailable('Native Atlas generation changes its declared metrics and hash')
    _admit_output(memory, scope, connection, plan)
    check_current()
    if _collect(memory, scope, connection, insights=True) != sources or _graph(memory, scope, connection) != graph:
        raise MemoryConflict('Atlas sources change before generation preparation delivery')
    check_current()
    return {'sources': sources, 'graph': graph, 'plan': plan, 'retirement': _retirement_digest(connection),
        'root': str(memory.physical_root), 'scope': scope.signature}


def _value(memory, scope, connection, value, plan):
    if (plan['metrics'] is None or not isinstance(value, dict) or set(value) != {'hash', 'narrative', 'generated_at'}
            or value['hash'] != plan['hash'] or not isinstance(value['narrative'], str) or not value['narrative'].strip()
            or not isinstance(value['generated_at'], str) or len(json.dumps(value).encode()) > SOURCE_LIMIT):
        raise MemoryUnavailable('Atlas insight requires its bounded native cache fields')
    try:
        timestamp = datetime.fromisoformat(value['generated_at'].replace('Z', '+00:00'))
        if timestamp.tzinfo is None: raise ValueError('An Atlas generation timestamp requires its timezone')
    except ValueError as error:
        raise MemoryUnavailable('Atlas insight requires its native generation timestamp') from error
    _admit_output(memory, scope, connection, value)


def synthesis(memory, scope, operation, arguments, *, check_current):
    fields = set() if operation == 'atlas_insight_prepare' else {'signature'}
    if operation == 'atlas_insight_publish': fields.add('value')
    if set(arguments) != fields:
        raise ValueError('Choose declared native Atlas generation arguments')
    _request(scope)
    with memory._transaction() as connection:
        snapshot = _snapshot(memory, scope, connection, check_current)
        signature = _signature(snapshot)
        if operation == 'atlas_insight_prepare': return {'ok': True, 'signature': signature, 'plan': snapshot['plan']}
        if arguments['signature'] != signature:
            raise MemoryConflict('Atlas sources or authority change before generation publication')
        if operation == 'atlas_insight_check': return {'ok': True}
        value = arguments['value']
        _value(memory, scope, connection, value, snapshot['plan'])
        check_current()
    content = json.dumps(value, ensure_ascii=False, indent=2).encode()
    payload = {'operation': 'atlas_insight'}
    published_snapshot = snapshot
    def apply(connection):
        nonlocal published_snapshot
        check_current()
        if _snapshot(memory, scope, connection, check_current) != snapshot:
            raise MemoryConflict('Atlas generation preserves later source and cache changes')
        _value(memory, scope, connection, value, snapshot['plan'])
        check_current()
        publish(memory._publication_path(CACHE), content)
        check_current()
        try:
            published_snapshot = _snapshot(memory, scope, connection, check_current)
        except MemoryConflict as error:
            raise MemoryUnavailable('Atlas insight recheck requires publication recovery') from error
        for key in snapshot.keys() - {'sources'}:
            if published_snapshot[key] != snapshot[key]:
                raise MemoryUnavailable('Atlas generation inputs change during publication and require recovery')
        untouched = lambda record: [row for row in record['sources'][2] if row[0] != CACHE]
        if untouched(published_snapshot) != untouched(snapshot):
            raise MemoryUnavailable('Atlas sources change during cache publication and require recovery')
        if source_path(memory, CACHE).read_bytes() != content:
            raise MemoryUnavailable('Atlas insight destination changes during publication and requires recovery')
        check_current()
        return {'status': 'committed'}
    receipt = memory._operation(scope, 'atlas-insight-' + uuid4().hex, payload, apply,
        publication_digests={CACHE: hashlib.sha256(content).hexdigest()})
    if receipt['status'] != 'committed': raise MemoryUnavailable('Atlas insight publication needs recovery or a current retry')
    with memory._transaction() as connection:
        check_current()
        _admit_output(memory, scope, connection, value)
        if source_path(memory, CACHE).read_bytes() != content:
            raise MemoryConflict('Atlas insight cache changes before delivery')
        if _snapshot(memory, scope, connection, check_current) != published_snapshot:
            raise MemoryConflict('Atlas inputs change before generation delivery')
        check_current()
    return {'ok': True, 'value': value}
