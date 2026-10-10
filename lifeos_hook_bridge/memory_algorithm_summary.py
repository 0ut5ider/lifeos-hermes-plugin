# ABOUTME: Admits complete thinking-chain inputs before native incremental summary generation.
# ABOUTME: Preserves completed cards through private recoverable publication under current owner authority.
from datetime import datetime
import hashlib
import json
import re
from uuid import uuid4

from .memory_access import MemoryConflict, MemoryUnavailable, _now
from .memory_algorithm_tab import CACHE, _catalog, _collect
from .memory_evidence import _signature
from .memory_policy import CATEGORIES
from .memory_source_review import _retirement_digest
from .memory_sources import authorize, SOURCE_LIMIT, CORPUS_LIMIT
from .memory_operational_views import projection
from .memory_tab_freshness import _checked
from .memory_transaction import publish


def _request(scope):
    authorize(scope)
    if not scope.principal or not CATEGORIES <= set(scope.write):
        raise MemoryUnavailable('Algorithm summaries require the current unrestricted owner writer')


def publication_paths(memory, scope, payload):
    _request(scope)
    if payload != {'operation': 'algorithm_summary'}:
        raise ValueError('Choose declared Algorithm summary publication')
    path = _checked(memory, memory._publication_path(CACHE))
    if path.exists() and (not path.is_file() or path.stat().st_size > SOURCE_LIMIT):
        raise MemoryUnavailable('Algorithm summaries require the bounded fixed cache')
    return [CACHE]


def _output(memory, scope, connection, value):
    content = json.dumps(value, ensure_ascii=False, allow_nan=False)
    decoded = projection(content, field_limit=CORPUS_LIMIT)
    if (len(content.encode()) > CORPUS_LIMIT or decoded is None
            or memory._native('validate_source_batch', contents=[decoded])['accepted'] != [True]
            or memory._filter_history(connection, scope, decoded, _now(), reviewed=True)['excluded']):
        raise MemoryUnavailable('Algorithm summary output contains excluded text')


def _snapshot(memory, scope, connection, check_current):
    _request(scope)
    check_current()
    catalog = _catalog(memory)
    admitted = _collect(memory, scope, connection, '/api/algorithm-tab', catalog)
    sources, fingerprints, metadata, versions, directory = admitted
    plan = memory._native('algorithm_summary_plan', sources=sources, metadata=metadata, versions=versions)
    if (not isinstance(plan, dict) or set(plan) != {'hash', 'files', 'overview', 'store'}
            or not isinstance(plan['hash'], str) or re.fullmatch('[0-9a-f]{64}', plan['hash']) is None
            or not isinstance(plan['files'], list) or len(plan['files']) > len(catalog)
            or any(not isinstance(row, dict) or set(row) != {'id', 'hash', 'system', 'user', 'level'}
                or not isinstance(row['id'], str) or row['id'] not in catalog or row['level'] != 'low'
                or not isinstance(row['hash'], str) or re.fullmatch('[0-9a-f]{64}', row['hash']) is None
                or not isinstance(row['system'], str) or not isinstance(row['user'], str) for row in plan['files'])
            or len({row['id'] for row in plan['files']}) != len(plan['files'])
            or not isinstance(plan['overview'], dict) or set(plan['overview']) != {'system', 'user', 'level'}
            or plan['overview']['level'] != 'high' or not isinstance(plan['overview']['system'], str)
            or not isinstance(plan['overview']['user'], str)
            or not isinstance(plan['store'], dict) or set(plan['store']) != {'overview', 'files'}
            or not isinstance(plan['store']['files'], dict)):
        raise MemoryUnavailable('Native Algorithm summaries change the declared plan')
    _output(memory, scope, connection, plan)
    check_current()
    if _collect(memory, scope, connection, '/api/algorithm-tab', catalog) != admitted:
        raise MemoryConflict('Algorithm sources change during native summary preparation')
    check_current()
    serialized = [list(row[:2]) + ([hashlib.sha256(row[2]).hexdigest()] if len(row) > 2 else [])
        for row in fingerprints]
    return {'inputs': {'sources': [row for row in sources if row['relative'] != CACHE],
                'fingerprints': [row for row in serialized if row[0] != CACHE],
                'metadata': {key: value for key, value in metadata.items() if key != CACHE},
                'versions': versions, 'directory': directory},
        'cache': [row for row in serialized if row[0] == CACHE], 'plan': plan,
        'scope': scope.signature, 'root': str(memory.physical_root), 'retirement': _retirement_digest(connection)}


def _entry(value, *, overview=False):
    fields = {'generated_at', 'chain_hash', 'level', 'markdown'} if overview else {'generated_at', 'hash', 'markdown'}
    if (not isinstance(value, dict) or set(value) != fields
            or not isinstance(value['markdown'], str) or not value['markdown'].strip()
            or not isinstance(value['generated_at'], str) or len(value['generated_at']) > 64):
        raise MemoryUnavailable('Algorithm summaries require the native cache fields')
    try:
        timestamp = datetime.fromisoformat(value['generated_at'].replace('Z', '+00:00'))
        if timestamp.tzinfo is None: raise ValueError('A summary timestamp requires its timezone')
    except ValueError as error:
        raise MemoryUnavailable('Algorithm summaries require a valid generation timestamp') from error


def _value(memory, scope, connection, value, plan):
    if (not isinstance(value, dict) or set(value) != {'overview', 'files'} or not isinstance(value['files'], dict)
            or len(json.dumps(value, ensure_ascii=False).encode()) > SOURCE_LIMIT):
        raise MemoryUnavailable('Algorithm summaries require the bounded native cache')
    previous = plan['store']
    hashes = {row['id']: row['hash'] for row in plan['files']}
    if set(previous['files']) - set(value['files']):
        raise MemoryUnavailable('Algorithm generation preserves completed native cards')
    for identifier, entry in value['files'].items():
        if entry == previous['files'].get(identifier): continue
        _entry(entry)
        if identifier not in hashes or entry['hash'] != hashes[identifier]:
            raise MemoryUnavailable('Algorithm cards require their current native source hash')
    overview = value['overview']
    if overview != previous['overview']:
        _entry(overview, overview=True)
        if overview['chain_hash'] != plan['hash'] or overview['level'] != 'high':
            raise MemoryUnavailable('Algorithm overview requires its current native chain hash and level')
    _output(memory, scope, connection, value)


def synthesis(memory, scope, operation, arguments, *, check_current):
    fields = set() if operation == 'algorithm_summary_prepare' else {'signature'}
    if operation == 'algorithm_summary_publish': fields.add('value')
    if set(arguments) != fields: raise ValueError('Choose declared native Algorithm summary arguments')
    _request(scope)
    with memory._transaction() as connection:
        snapshot = _snapshot(memory, scope, connection, check_current)
        signature = _signature(snapshot)
        if operation == 'algorithm_summary_prepare': return {'ok': True, 'plan': snapshot['plan'], 'signature': signature}
        if arguments['signature'] != signature:
            raise MemoryConflict('Algorithm sources or authority change before summary publication')
        if operation == 'algorithm_summary_check': return {'ok': True}
        value = arguments['value']
        _value(memory, scope, connection, value, snapshot['plan'])
        check_current()
    content = json.dumps(value, ensure_ascii=False, indent=2).encode()
    payload = {'operation': 'algorithm_summary'}
    after = snapshot
    def apply(connection):
        nonlocal after
        check_current()
        if _snapshot(memory, scope, connection, check_current) != snapshot:
            raise MemoryConflict('Algorithm summaries preserve later source and destination changes')
        _value(memory, scope, connection, value, snapshot['plan'])
        publish(memory._publication_path(CACHE), content)
        try:
            after = _snapshot(memory, scope, connection, check_current)
        except MemoryConflict as error:
            raise MemoryUnavailable('Algorithm summary recheck requires publication recovery') from error
        if any(after[key] != snapshot[key] for key in ('inputs', 'scope', 'root', 'retirement')):
            raise MemoryUnavailable('Algorithm inputs change during summary publication and require recovery')
        if memory._publication_path(CACHE).read_bytes() != content:
            raise MemoryUnavailable('Algorithm summary destination changes during publication and requires recovery')
        check_current()
        return {'status': 'committed'}
    receipt = memory._operation(scope, 'algorithm-summary-' + uuid4().hex, payload, apply,
        publication_digests={CACHE: hashlib.sha256(content).hexdigest()})
    if receipt['status'] != 'committed': raise MemoryUnavailable('Algorithm summaries need recovery or a current retry')
    with memory._transaction() as connection:
        check_current()
        if _snapshot(memory, scope, connection, check_current) != after:
            raise MemoryConflict('Algorithm summary delivery preserves later source changes')
        check_current()
    return {'ok': True, 'signature': _signature(after)}
