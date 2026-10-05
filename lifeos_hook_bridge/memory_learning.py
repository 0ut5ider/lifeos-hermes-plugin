# ABOUTME: Admits current native rating rows before learning analysis.
# ABOUTME: Publishes fixed native synthesis reports with current authority and recovery receipts.
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re

from .memory_access import MemoryConflict, MemoryUnavailable
from .memory_sources import authorize, _text_source, _admit, _strings, CORPUS_LIMIT, SOURCE_COUNT_LIMIT
from .memory_transaction import publish


SOURCE = 'LIFEOS/MEMORY/LEARNING/SIGNALS/ratings.jsonl'
PREFIX = 'LIFEOS/MEMORY/LEARNING/SYNTHESIS/'


def _authorize_write(scope):
    authorize(scope)
    if not {'principal', 'assistant', 'project'} <= set(scope.write):
        raise MemoryUnavailable('Learning report publication requires unrestricted owner write access')


def _collect(memory, scope, connection, path):
    authorize(scope)
    if path != str(memory.root / SOURCE):
        raise MemoryUnavailable('Learning analysis requires its fixed installed rating source')
    target = memory._path(SOURCE)
    physical = memory.root.parent / '.config/LIFEOS/USER/MEMORY/LEARNING/SIGNALS/ratings.jsonl'
    if target.is_symlink() or target.resolve() != physical:
        raise MemoryUnavailable('The ratings source changes its permitted physical path')
    if not target.exists():
        return {'source': None, 'ratings': None}
    source, timestamp = _text_source(memory, scope, str(target), suffix='.jsonl')
    rows = []
    for line in source['content'].splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except ValueError:
            continue
        if row is None:
            continue
        if (not isinstance(row, dict) or any(not isinstance(row.get(key), str) or len(row[key]) > CORPUS_LIMIT
                for key in ('timestamp', 'session_id', 'source', 'sentiment_summary'))
                or row['source'] not in ('explicit', 'implicit')
                or any(type(row.get(key)) not in (int, float)
                       for key in ('rating', 'confidence'))
                or not 0 <= row['rating'] <= 10 or not 0 <= row['confidence'] <= 1
                or 'comment' in row and not isinstance(row['comment'], str)):
            raise MemoryUnavailable('The rating source contains an unsupported native row')
        rows.append(row)
    if len(rows) > SOURCE_COUNT_LIMIT:
        raise MemoryUnavailable('The rating source exceeds its admitted row limit')
    projections = ['\n'.join((line, *_strings(row))) for row in rows for line in [json.dumps(row)]]
    accepted = memory._native('validate_source_batch', contents=projections)['accepted'] if projections else []
    admitted = [row for row, projection, valid in zip(rows, projections, accepted, strict=True)
        if valid is True and not _admit(memory, connection, scope, json.dumps(row), SOURCE,
                                       timestamp, projection=projection)['excluded']]
    return {'source': source, 'ratings': admitted}


def _target(memory, relative):
    if (not isinstance(relative, str) or re.fullmatch(
            r'[0-9]{4}-[0-9]{2}/[0-9]{4}-[0-9]{2}-[0-9]{2}_(weekly|monthly|all-time)-patterns\.md', relative) is None):
        raise MemoryUnavailable('Learning synthesis changes its fixed native report name')
    target = memory._path(PREFIX + relative)
    physical = memory.root.parent / '.config/LIFEOS/USER/MEMORY/LEARNING/SYNTHESIS' / relative
    if (target.resolve() != physical or target.is_symlink()
            or target.exists() and (not target.is_file() or target.stat().st_uid != os.getuid()
                                    or target.stat().st_nlink != 1 or target.stat().st_size > CORPUS_LIMIT)):
        raise MemoryUnavailable('The learning report changes its permitted physical owner path')
    return target


def _snapshot(memory, relative):
    target = _target(memory, relative)
    return hashlib.sha256(target.read_bytes()).hexdigest() if target.exists() else None


def publication_paths(memory, scope, payload):
    _authorize_write(scope)
    return [_target(memory, payload['relative']).relative_to(memory.root).as_posix()] if payload['relative'] else []


def ratings(memory, scope, arguments, *, check_current):
    if any(type(arguments[key]) is not bool for key in ('month', 'all', 'dry_run')):
        raise ValueError('Choose native learning period and dry-run modes')
    writing = not arguments['dry_run']
    if writing:
        _authorize_write(scope)
    instant = datetime.now(timezone.utc)
    period = 'monthly' if arguments['month'] else 'all-time' if arguments['all'] else 'weekly'
    expected = instant.astimezone().strftime('%Y-%m') + '/' + instant.strftime('%Y-%m-%d') + '_' + period + '-patterns.md'
    with memory._transaction() as connection:
        collected = _collect(memory, scope, connection, arguments['path'])
        previous = _snapshot(memory, expected) if writing else None
        rendered = memory._native('learning_ratings', ratings=collected['ratings'], path=arguments['path'],
            month=arguments['month'], all=arguments['all'], dry_run=arguments['dry_run'], now=instant.isoformat())
        if (set(rendered) != {'stdout', 'relative', 'content'} or not isinstance(rendered['stdout'], str)
                or not (rendered['relative'] is None and rendered['content'] is None
                    or writing and rendered['relative'] == expected and isinstance(rendered['content'], str))
                or len(json.dumps(rendered).encode()) > CORPUS_LIMIT):
            raise MemoryUnavailable('Native learning analysis returns invalid artifacts')
        generated = rendered['stdout'] + '\n' + (rendered['content'] or '')
        if (memory._native('validate_source_batch', contents=[generated])['accepted'] != [True]
                or memory._filter_history(connection, scope, generated, instant.isoformat(), reviewed=True)['excluded']):
            raise MemoryUnavailable('The generated learning report is excluded by current memory policy')
        check_current()
        if (_collect(memory, scope, connection, arguments['path']) != collected
                or writing and _snapshot(memory, expected) != previous):
            raise MemoryConflict('The learning source or report changes during analysis')
    if not writing:
        return {'ok': True, 'stdout': rendered['stdout']}
    signature = hashlib.sha256(json.dumps(collected, sort_keys=True).encode()).hexdigest()
    payload = {'operation': 'learning_ratings', **arguments, 'sources_signature': signature,
               'relative': rendered['relative']}

    def apply(connection):
        try:
            check_current()
            if (_collect(memory, scope, connection, arguments['path']) != collected
                    or _snapshot(memory, expected) != previous):
                raise MemoryConflict('The learning source or report changes before publication')
        except (MemoryUnavailable, OSError) as error:
            raise MemoryConflict(str(error)) from error
        if rendered['content'] is not None:
            publish(_target(memory, rendered['relative']), rendered['content'].encode())
        return {'status': 'committed', 'stdout': rendered['stdout']}

    receipt = memory._operation(scope, arguments['request_id'], payload, apply)
    return {'ok': receipt['status'] == 'committed', 'stdout': receipt.get('stdout'), 'receipt': receipt}
