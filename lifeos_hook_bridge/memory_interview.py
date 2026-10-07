# ABOUTME: Supplies current admitted sources to native interview cadence calculations.
# ABOUTME: Journals completion state and verdict cache publication at fixed owner destinations.
import json
import os
from uuid import uuid4

from .memory_access import MemoryUnavailable, MemoryConflict
from .memory_evidence import _request, _collect as evidence_sources, _signature, _cache as evidence_cache, OUTPUT as EVIDENCE_CACHE
from .memory_freshness import _collect as freshness_sources
from .memory_sources import (_text_source, json_projection, _admit, authorize, CORPUS_LIMIT, SOURCE_LIMIT)
from .memory_transaction import publish


STATE = 'LIFEOS/MEMORY/STATE/interview.json'
CACHE = 'LIFEOS/USER/CACHE/interview-due.json'


def _target(memory, relative, path=None):
    if relative not in {STATE, CACHE} or path is not None and path != str(memory.root / relative):
        raise MemoryUnavailable('Interview publication requires its installed destination')
    target = memory._path(relative)
    physical = memory.root.parent / '.config/LIFEOS/USER' / relative.removeprefix(
        'LIFEOS/USER/' if relative.startswith('LIFEOS/USER/') else 'LIFEOS/')
    limit = SOURCE_LIMIT if relative == STATE else CORPUS_LIMIT
    if (target.resolve() != physical or target.is_symlink()
            or target.exists() and (not target.is_file() or target.stat().st_uid != os.getuid()
                                    or target.stat().st_size > limit)):
        raise MemoryUnavailable('The interview destination changes its permitted physical owner path')
    return target


def _last(memory, scope, connection):
    path = _target(memory, STATE)
    if not path.exists():
        return {'sources': [], 'signature': None}
    source, timestamp = _text_source(memory, scope, str(path), suffix='.json', evidence=True)
    result = {'sources': [], 'signature': _signature(source)}
    projection = json_projection(source['content'])
    if projection is None:
        return result
    valid = memory._native('validate_source_batch', contents=[projection + '\n' + source['path']])['accepted']
    if valid != [True] or _admit(memory, connection, scope, source['content'], STATE, timestamp,
                               projection=projection)['excluded']:
        return result
    return {'sources': [source], 'signature': result['signature']}


def _collect(memory, scope, connection, evidence_present):
    if type(evidence_present) is not bool:
        raise ValueError('Interview calculation requires a Boolean evidence selection')
    last = _last(memory, scope, connection)
    return {'context_sources': freshness_sources(memory, scope, connection, 'context', None),
            'state_sources': freshness_sources(memory, scope, connection, 'state', None),
            'evidence_sources': evidence_sources(memory, scope, connection, None) if evidence_present else None,
            'interview_sources': last['sources'], 'interview_signature': last['signature']}


def _render(memory, sources, now):
    result = memory._native('interview_due', now=now, **sources)
    if (set(result) != {'inputs', 'verdict', 'verdict_content'} or not isinstance(result['inputs'], dict)
            or not isinstance(result['verdict'], dict) or not isinstance(result['verdict_content'], str)
            or len(json.dumps(result).encode()) > CORPUS_LIMIT):
        raise MemoryUnavailable('Native interview rendering returns an invalid result')
    return result


def read(memory, scope, now, evidence_present, *, check_current):
    _request(scope, None, now)
    with memory._transaction() as connection:
        sources = _collect(memory, scope, connection, evidence_present)
        result = _render(memory, sources, now)
        if _collect(memory, scope, connection, evidence_present) != sources:
            raise MemoryUnavailable('Interview sources changed during calculation')
        check_current()
        return {'ok': True, 'value': result['inputs']}


def publication_paths(memory, scope, payload):
    authorize(scope)
    if not {'principal', 'assistant', 'project'} <= set(scope.write):
        raise MemoryUnavailable('Interview publication requires unrestricted owner write access')
    target = STATE if payload['operation'] == 'interview_due_mark' else CACHE
    _target(memory, target)
    return [target]


def write(memory, scope, path, now=None, verdict=None, *, check_current):
    operation = 'interview_due_cache_write' if verdict is not None else 'interview_due_mark'
    if verdict is not None:
        if not isinstance(verdict, dict) or len(json.dumps(verdict).encode()) > CORPUS_LIMIT:
            raise ValueError('Choose a bounded native interview verdict')
        now = verdict.get('computed_at')
    _request(scope, None, now)
    relative = CACHE if verdict is not None else STATE
    _target(memory, relative, path)
    payload = {'operation': operation}
    publication_paths(memory, scope, payload)
    with memory._transaction() as connection:
        evidence_present = evidence_cache(memory, str(memory.root / EVIDENCE_CACHE)).exists() if verdict is not None else False
        sources = _collect(memory, scope, connection, evidence_present) if verdict is not None else {'interview_sources': _last(memory, scope, connection)}
        signature = _signature(sources)
        payload['source_signature'] = signature

    def current_sources(connection):
        try:
            return (_collect(memory, scope, connection, evidence_present) if verdict is not None
                    else {'interview_sources': _last(memory, scope, connection)})
        except (MemoryUnavailable, OSError) as error:
            raise MemoryConflict('Interview source admission changed before publication') from error

    def apply(connection):
        current = current_sources(connection)
        if _signature(current) != signature:
            raise MemoryConflict('Interview sources changed before publication rendering')
        if verdict is not None:
            result = _render(memory, current, now)
            if result['verdict'] != verdict:
                raise MemoryConflict('The supplied verdict does not match current interview sources')
            content = result['verdict_content']
        else:
            result = memory._native('interview_completion', now=now)
            if set(result) != {'content'} or not isinstance(result['content'], str) or len(result['content'].encode()) > SOURCE_LIMIT:
                raise MemoryUnavailable('Native interview completion returns an invalid artifact')
            content = result['content']
        current = current_sources(connection)
        if _signature(current) != signature:
            raise MemoryConflict('Interview sources changed during publication rendering')
        try:
            if verdict is not None and evidence_cache(memory, str(memory.root / EVIDENCE_CACHE)).exists() != evidence_present:
                raise MemoryConflict('Interview evidence availability changed during publication rendering')
            check_current()
            publication_paths(memory, scope, payload)
            target = _target(memory, relative, path)
        except (MemoryUnavailable, OSError) as error:
            raise MemoryConflict(str(error)) from error
        publish(target, content.encode())
        return {'status': 'committed', 'artifacts': 1}

    receipt = memory._operation(scope, 'interview-' + uuid4().hex, payload, apply)
    return {'ok': receipt['status'] == 'committed'}
