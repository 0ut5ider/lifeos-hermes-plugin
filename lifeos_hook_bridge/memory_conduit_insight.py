# ABOUTME: Admits complete daily Conduit history before native insight generation.
# ABOUTME: Binds source and authority revisions and journals fixed insight and default publication.
from datetime import date as calendar_date
import hashlib
import json
import math
import re
from uuid import uuid4

from .memory_access import MemoryUnavailable, MemoryConflict, _now
from .memory_conduit import PREFIX, CONFIG, _collect, _descriptor_digest
from .memory_evidence import _signature
from .memory_policy import CATEGORIES
from .memory_source_review import _retirement_digest
from .memory_sources import authorize, SOURCE_LIMIT, CORPUS_LIMIT, json_projection
from .memory_tab_freshness import _checked
from .memory_transaction import publish
from . import memory_operational_history as history

TARGET = '/api/conduit/insight/build'


def _request(scope, date, initialize):
    authorize(scope)
    if not scope.principal or not CATEGORIES <= set(scope.write):
        raise MemoryUnavailable('Conduit insight requires the current unrestricted owner writer')
    if not isinstance(date, str) or re.fullmatch(r'\d{4}-\d{2}-\d{2}', date) is None:
        raise ValueError('Choose a native Conduit calendar date')
    calendar_date.fromisoformat(date)
    if type(initialize) is not bool:
        raise ValueError('Choose declared Conduit initialization')


def publication_paths(memory, scope, payload):
    if set(payload) != {'operation', 'date', 'initialize', 'reuse'} or type(payload['reuse']) is not bool:
        raise ValueError('Choose declared Conduit insight publication')
    _request(scope, payload['date'], payload['initialize'])
    paths = [] if payload['reuse'] else [PREFIX + 'insights/' + payload['date'] + '.json']
    if payload['initialize'] and not _checked(memory, memory.root / CONFIG).exists():
        paths.append(CONFIG)
    for relative in paths:
        path = _checked(memory, memory._publication_path(relative))
        if path.exists() and (not path.is_file() or path.stat().st_size > SOURCE_LIMIT):
            raise MemoryUnavailable('Conduit insight changes its bounded fixed destination')
    return paths


def _snapshot(memory, scope, connection, date, initialize, check_current):
    sources, fingerprints = _collect(memory, scope, connection, TARGET, date)
    streamed = {PREFIX + 'events/' + date + '.jsonl': None}
    with history.snapshot(memory, scope, connection, check_current=check_current, sources=streamed,
            require_newline=False, objects_only=False, allow_unfinished_utf8=False,
            require_all_admitted=True) as (descriptor, events):
        admitted = _descriptor_digest(descriptor)
        existing = next((source['content'] for source in sources if source['relative'] != CONFIG), None)
        result = memory._native('conduit_prepare', history_descriptor=descriptor,
            source_descriptors=(descriptor,), content=existing)
        check_current()
        if (_collect(memory, scope, connection, TARGET, date) != (sources, fingerprints)
                or [history.fingerprint(memory, relative, sources=streamed) for relative in streamed] != events):
            raise MemoryConflict('Conduit insight sources change during preparation')
    plan = result.get('plan')
    if (not isinstance(plan, dict) or set(plan) != {'text', 'since', 'eventsConsidered', 'existing', 'existingWasReal'}
            or not isinstance(plan['text'], str) or type(plan['eventsConsidered']) is not int
            or plan['eventsConsidered'] < 0 or type(plan['existingWasReal']) is not bool
            or plan['since'] is not None and not isinstance(plan['since'], str)
            or plan['existing'] is not None and not isinstance(plan['existing'], dict)
            or len(json.dumps(plan).encode()) > CORPUS_LIMIT):
        raise MemoryUnavailable('Native Conduit preparation changes its declared result')
    _admit_output(memory, scope, connection, plan)
    check_current()
    if (_collect(memory, scope, connection, TARGET, date) != (sources, fingerprints)
            or [history.fingerprint(memory, relative, sources=streamed) for relative in streamed] != events):
        raise MemoryConflict('Conduit insight sources change before preparation delivery')
    check_current()
    records = [(row[0], row[1], hashlib.sha256(row[2]).hexdigest()) if len(row) == 3 else row
               for row in fingerprints[1]]
    snapshot = {'sources': records,
        'events': events, 'admitted': admitted, 'retirement': _retirement_digest(connection),
        'root': str(memory.physical_root), 'plan': plan, 'scope': scope.signature,
        'date': date, 'initialize': initialize}
    return snapshot


def _admit_output(memory, scope, connection, value):
    content = json.dumps(value, ensure_ascii=False, allow_nan=False)
    decoded = json_projection(content)
    if (len(content.encode()) > CORPUS_LIMIT or decoded is None
            or memory._native('validate_source_batch', contents=[decoded])['accepted'] != [True]
            or memory._filter_history(connection, scope, decoded, _now(), reviewed=True)['excluded']):
        raise MemoryUnavailable('Conduit insight output contains excluded text')


def _value(memory, scope, connection, value, plan, date, reuse):
    if type(reuse) is not bool:
        raise ValueError('Choose declared native insight reuse')
    if reuse:
        if not plan['existingWasReal'] or value != plan['existing']:
            raise MemoryUnavailable('Conduit insight reuse requires its admitted prior good result')
        _admit_output(memory, scope, connection, value)
        return
    fields = {'date', 'generatedAt', 'conduitVersion', 'level', 'model', 'since',
              'eventsConsidered', 'narrative', 'contentTypes'}
    if (not isinstance(value, dict) or set(value) not in (fields, fields | {'skipped'})
            or value['date'] != date or value['level'] != 'low' or value['since'] != plan['since']
            or type(value['eventsConsidered']) is not int or value['eventsConsidered'] != plan['eventsConsidered']
            or any(not isinstance(value[key], str) for key in ('generatedAt', 'conduitVersion', 'model', 'narrative'))
            or value['model'] not in {'(none)', '(failed)', 'haiku-tier'} or len(value['narrative']) > 320
            or not isinstance(value['contentTypes'], list) or len(value['contentTypes']) > 6
            or 'skipped' in value and value['skipped'] is not True):
        raise MemoryUnavailable('Conduit insight requires its bounded native metadata')
    for row in value['contentTypes']:
        if (not isinstance(row, dict) or set(row) != {'label', 'share', 'evidence'}
                or not isinstance(row['label'], str) or not 1 <= len(row['label']) <= 40
                or not isinstance(row['evidence'], str) or len(row['evidence']) > 120
                or type(row['share']) not in (float, int) or not math.isfinite(row['share'])
                or not 0 <= row['share'] <= 1):
            raise MemoryUnavailable('Conduit insight requires bounded native content types')
    if plan['eventsConsidered'] == 0:
        if (value['model'] != '(none)' or value.get('skipped') is not True or value['contentTypes']
                or value['narrative'] != 'No activity captured yet today.'):
            raise MemoryUnavailable('An idle Conduit insight must preserve its native empty result')
    elif value['model'] == '(none)' or 'skipped' in value:
        raise MemoryUnavailable('An active Conduit insight cannot claim an idle result')
    if value['model'] == '(failed)' and (plan['existingWasReal'] or value['contentTypes']
            or value['narrative'] != 'Could not generate a read this hour (inference unavailable).'):
        raise MemoryUnavailable('Conduit inference failure must preserve an admitted prior good result')
    if len(json.dumps(value).encode()) > SOURCE_LIMIT:
        raise MemoryUnavailable('Conduit insight exceeds its native record limit')
    _admit_output(memory, scope, connection, value)


def synthesis(memory, scope, operation, arguments, *, check_current):
    fields = {'date', 'initialize'}
    if operation != 'conduit_prepare': fields.add('signature')
    if operation == 'conduit_publish': fields |= {'value', 'reuse'}
    if set(arguments) != fields:
        raise ValueError('Choose declared native Conduit insight arguments')
    date, initialize = arguments['date'], arguments['initialize']
    _request(scope, date, initialize)
    with memory._transaction() as connection:
        snapshot = _snapshot(memory, scope, connection, date, initialize, check_current)
        signature = _signature(snapshot)
        if operation == 'conduit_prepare':
            return {'ok': True, 'signature': signature, 'plan': snapshot['plan']}
        if arguments['signature'] != signature:
            raise MemoryConflict('Conduit insight sources or authority changed before publication')
        if operation == 'conduit_check': return {'ok': True}
        value, reuse = arguments['value'], arguments['reuse']
        _value(memory, scope, connection, value, snapshot['plan'], date, reuse)
        payload = {'operation': 'conduit_insight', 'date': date, 'initialize': initialize, 'reuse': reuse}
        paths = publication_paths(memory, scope, payload)
        contents = {PREFIX + 'insights/' + date + '.json': json.dumps(value, ensure_ascii=False, indent=2)}
        if CONFIG in paths:
            contents[CONFIG] = memory._native('conduit_defaults')['content']
            _admit_output(memory, scope, connection, json.loads(contents[CONFIG]))
        check_current()
    published_snapshot = snapshot
    if paths:
        def apply(connection):
            nonlocal published_snapshot
            check_current()
            if (_snapshot(memory, scope, connection, date, initialize, check_current) != snapshot
                    or publication_paths(memory, scope, payload) != paths):
                raise MemoryConflict('Conduit insight preserves later source and destination changes')
            _value(memory, scope, connection, value, snapshot['plan'], date, reuse)
            for relative in paths:
                if relative == CONFIG: _admit_output(memory, scope, connection, json.loads(contents[CONFIG]))
                check_current()
                publish(memory._publication_path(relative), contents[relative].encode())
            check_current()
            try:
                published_snapshot = _snapshot(memory, scope, connection, date, initialize, check_current)
            except MemoryConflict as error:
                raise MemoryUnavailable('Conduit insight recheck requires publication recovery') from error
            for key in snapshot.keys() - {'sources', 'plan'}:
                if published_snapshot[key] != snapshot[key]:
                    raise MemoryUnavailable('Conduit insight inputs change during publication and require recovery')
            untouched = lambda value: [row for row in value['sources'] if row[0] not in paths]
            if untouched(published_snapshot) != untouched(snapshot):
                raise MemoryUnavailable('Conduit insight sources change during publication and require recovery')
            for relative in paths:
                if memory._publication_path(relative).read_bytes() != contents[relative].encode():
                    raise MemoryUnavailable('Conduit insight destination changes during publication and requires recovery')
            check_current()
            return {'status': 'committed'}
        receipt = memory._operation(scope, 'conduit-insight-' + uuid4().hex, payload, apply,
            publication_digests={relative: hashlib.sha256(contents[relative].encode()).hexdigest() for relative in paths})
        if receipt['status'] != 'committed':
            raise MemoryUnavailable('Conduit insight publication needs recovery or a current retry')
    with memory._transaction() as connection:
        check_current()
        _admit_output(memory, scope, connection, value)
        for relative in paths:
            if _checked(memory, memory.root / relative).read_bytes() != contents[relative].encode():
                raise MemoryConflict('Conduit insight destinations change before delivery')
        if _snapshot(memory, scope, connection, date, initialize, check_current) != published_snapshot:
            raise MemoryConflict('Conduit insight inputs change before delivery')
        check_current()
    return {'ok': True, 'value': value}
