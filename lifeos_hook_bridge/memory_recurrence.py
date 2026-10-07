# ABOUTME: Collects admitted native recurrence streams, captures, and patch history.
# ABOUTME: Publishes owner registry records with current authority and recovery receipts.
from datetime import datetime, timezone
from itertools import islice
import json
import os

from .memory_access import MemoryConflict, MemoryUnavailable
from .memory_sources import authorize, _text_source, _admit, json_projection, SOURCE_COUNT_LIMIT, CORPUS_LIMIT, SOURCE_LIMIT
from .memory_transaction import publish

STREAMS = ('verification-gate.jsonl', 'format-gate.jsonl', 'writing-gate.jsonl',
           'tool-failures.jsonl', 'hook-healer.jsonl')
REGISTRY = 'LIFEOS/MEMORY/LEARNING/PATCHES/registry.jsonl'
CAPTURES = 'LIFEOS/MEMORY/LEARNING/FAILURES'


def _path(memory, relative, *, directory=False):
    target = memory._path(relative)
    physical = memory.root.parent / '.config/LIFEOS/USER' / relative.removeprefix('LIFEOS/')
    if (target.is_symlink() or target.resolve() != physical
            or target.exists() and (target.stat().st_uid != os.getuid()
                or not (target.is_dir() if directory else target.is_file())
                or not directory and target.stat().st_nlink != 1)):
        raise MemoryUnavailable('The recurrence source changes its fixed physical owner path')
    return target


def _entries(memory, relative, budget):
    directory = _path(memory, relative, directory=True)
    if not directory.exists():
        return []
    entries = list(islice(directory.iterdir(), SOURCE_COUNT_LIMIT + 1))
    budget[0] += len(entries)
    if budget[0] > SOURCE_COUNT_LIMIT:
        raise MemoryUnavailable('The recurrence directory exceeds its discovery limit')
    return entries


def _collect(memory, scope, connection, base):
    authorize(scope)
    if base != str(memory.root / 'LIFEOS'):
        raise MemoryUnavailable('Recurrence readers require the installed LifeOS root')
    paths = ['LIFEOS/MEMORY/OBSERVABILITY/' + name for name in STREAMS] + [REGISTRY]
    budget = [0]
    for month in _entries(memory, CAPTURES, budget):
        relative = month.relative_to(memory.root).as_posix()
        checked = _path(memory, relative, directory=month.is_dir())
        if not checked.is_dir():
            continue
        for capture in _entries(memory, relative, budget):
            selected = capture.relative_to(memory.root).as_posix()
            checked = _path(memory, selected, directory=capture.is_dir())
            if checked.is_dir():
                paths.append(selected + '/sentiment.json')
            if len(paths) > SOURCE_COUNT_LIMIT:
                raise MemoryUnavailable('The recurrence corpus exceeds its source count limit')
    raw, admitted = [], []
    total = count = 0
    for relative in paths:
        target = _path(memory, relative)
        if not target.exists():
            continue
        source, timestamp = _text_source(memory, scope, str(target), suffix=target.suffix, preserve_newlines=True)
        raw.append(source)
        total += len(source['content'].encode())
        if total > CORPUS_LIMIT:
            raise MemoryUnavailable('The recurrence corpus exceeds its byte limit')
        lines = source['content'].splitlines() if target.suffix == '.jsonl' else [source['content']]
        rows = []
        for line in lines:
            projection = json_projection(line)
            if projection is None:
                continue
            row = json.loads(line)
            if row is None:
                continue
            if not isinstance(row, dict):
                raise MemoryUnavailable('Recurrence sources require supported object rows')
            if any(key in row and not isinstance(row[key], str) for key in
                    ('ts', 'timestamp', 'captured_at', 'session_id', 'error', 'summary', 'detailed_context')):
                raise MemoryUnavailable('The recurrence source contains unsupported native fields')
            rows.append((line, projection))
        count += len(rows)
        if count > SOURCE_COUNT_LIMIT:
            raise MemoryUnavailable('The recurrence corpus exceeds its row limit')
        accepted = memory._native('validate_source_batch', contents=[p for _, p in rows])['accepted'] if rows else []
        kept = [line for (line, projection), valid in zip(rows, accepted, strict=True)
            if valid is True and not _admit(memory, connection, scope, line, relative, timestamp,
                                            projection=projection)['excluded']]
        if target.suffix == '.json' and not kept:
            continue
        content = '\n'.join(kept) + ('\n' if target.suffix == '.jsonl' and kept else '')
        admitted.append({'path': str(target), 'content': content, 'timestamp': source['lastModified']})
    return {'raw': raw, 'sources': admitted}


def sources(memory, scope, base, *, check_current):
    with memory._transaction() as connection:
        initial = _collect(memory, scope, connection, base)
        check_current()
        if _collect(memory, scope, connection, base) != initial:
            raise MemoryConflict('Recurrence sources change during collection')
        return {'ok': True, 'sources': initial['sources']}


def _authorize_write(scope):
    authorize(scope)
    if not {'principal', 'assistant', 'project'} <= set(scope.write):
        raise MemoryUnavailable('Recurrence registry publication requires unrestricted owner write access')


def publication_paths(memory, scope):
    _authorize_write(scope)
    return [_path(memory, REGISTRY).relative_to(memory.root).as_posix()]


def append(memory, scope, arguments, *, check_current):
    _authorize_write(scope)
    if arguments['base'] != str(memory.root / 'LIFEOS'):
        raise MemoryUnavailable('Recurrence publication requires the installed LifeOS root')
    record = arguments['record']
    required = {'ts', 'class_id', 'hypothesis_slug', 'files', 'fixture'}
    if (not isinstance(record, dict) or not required <= set(record) or set(record) - required - {'note'}
            or any(not isinstance(record[key], str) or not record[key] or len(record[key].encode()) > 4096
                   for key in ('ts', 'class_id', 'hypothesis_slug'))
            or not isinstance(record['files'], list) or len(record['files']) > 128
            or any(not isinstance(value, str) or len(value.encode()) > 4096 for value in record['files'])
            or record['fixture'] is not None and not isinstance(record['fixture'], str)
            or 'note' in record and not isinstance(record['note'], str)
            or len(json.dumps(record).encode()) > 64 * 1024):
        raise ValueError('Choose one bounded native patch registry record')
    projection = json_projection(json.dumps(record))

    def admit(connection, content):
        generated = json_projection(content) if content.strip() and '\n' not in content.strip() else content
        text = '\n'.join((content, generated or '', projection or ''))
        if (projection is None or memory._native('validate_source_batch', contents=[text])['accepted'] != [True]
                or memory._filter_history(connection, scope, text,
                    datetime.now(timezone.utc).isoformat(), reviewed=True)['excluded']):
            raise MemoryUnavailable('The patch registry record is excluded by current memory policy')

    def snapshot():
        target = _path(memory, REGISTRY)
        if target.exists() and target.stat().st_size > SOURCE_LIMIT:
            raise MemoryUnavailable('The patch registry exceeds its source limit')
        return target.read_text() if target.exists() else ''

    with memory._transaction() as connection:
        previous = snapshot()
        for line in previous.splitlines():
            projection_previous = json_projection(line)
            if projection_previous is not None:
                admit(connection, projection_previous)
        admit(connection, '')
        check_current()
    payload = {'operation': 'recurrence_append', **arguments}

    def apply(connection):
        admit(connection, '')
        if snapshot() != previous:
            raise MemoryConflict('The recurrence registry changes before native rendering')
        result = memory._native('recurrence_append', previous=previous, record=record)
        if set(result) != {'content'} or not isinstance(result['content'], str) or len(result['content'].encode()) > SOURCE_LIMIT:
            raise MemoryUnavailable('Native recurrence publication returns invalid bytes')
        admit(connection, result['content'])
        try:
            check_current()
            if snapshot() != previous:
                raise MemoryConflict('The recurrence registry changes during native rendering')
        except (MemoryUnavailable, OSError) as error:
            raise MemoryConflict(str(error)) from error
        publish(_path(memory, REGISTRY), result['content'].encode())
        return {'status': 'committed'}

    receipt = memory._operation(scope, arguments['request_id'], payload, apply)
    return {'ok': receipt['status'] == 'committed', 'receipt': receipt}
