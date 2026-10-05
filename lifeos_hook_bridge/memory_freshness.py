# ABOUTME: Supplies admitted current source bytes and times to native freshness readers.
# ABOUTME: Rechecks source collection and owner authority before returning native results.
import json
from pathlib import Path

from .memory_access import MemoryConflict, MemoryUnavailable, _now
from .memory_sources import (CONTEXT_FILES, CORPUS_LIMIT, FRESHNESS_TELOS_SOURCES,
                             authorize, is_state_source, read_markdown)


TELOS = 'LIFEOS/USER/TELOS/TELOS.md'
CONTEXT = CONTEXT_FILES | {TELOS, 'LIFEOS/LIFEOS_SYSTEM_PROMPT.md',
    'LIFEOS/DOCUMENTATION/ARCHITECTURE_SUMMARY.md', 'LIFEOS/DOCUMENTATION/LifeosSystemArchitecture.md'}
VIEWS = frozenset({'telos', 'context', 'state', 'registry', 'frontmatter', 'legacy_path', 'legacy_date'})
HTTP_VIEWS = {'telos_freshness': '/api/telos/freshness', 'telos_stale': '/api/telos/freshness/stale',
    'telos_freshness_summary': '/api/telos/freshness/summary', 'context_freshness': '/api/freshness',
    'context_freshness_summary': '/api/freshness/summary', 'telos_health': '/api/telos/health'}


def _request(memory, view, path, slug):
    if not isinstance(view, str) or view not in VIEWS:
        raise ValueError('Choose a native freshness read view')
    if view in ('legacy_path', 'legacy_date'):
        if not isinstance(slug, str) or len(slug) > 128:
            raise ValueError('Choose a native TELOS section slug')
    elif slug is not None:
        raise ValueError('This freshness view does not accept a section slug')
    if view in ('telos', 'legacy_path', 'legacy_date', 'frontmatter'):
        if not isinstance(path, str) or not Path(path).is_absolute():
            raise ValueError('Choose an installed freshness source')
        try:
            relative = Path(path).relative_to(memory.root).as_posix()
        except ValueError:
            raise MemoryUnavailable('Freshness cannot read outside its installed root') from None
        if ('..' in Path(relative).parts or
                (relative != TELOS if view != 'frontmatter' else
                 relative not in CONTEXT | FRESHNESS_TELOS_SOURCES and not is_state_source(relative))):
            raise MemoryUnavailable('This is not an installed native freshness source')
    elif path is not None:
        raise ValueError('This freshness view uses the installed source registry')


def _collect(memory, scope, connection, view, path):
    authorize(scope)
    if view == 'context':
        relatives = CONTEXT
    elif view == 'frontmatter':
        relatives = {Path(path).relative_to(memory.root).as_posix()}
    elif view in ('telos', 'legacy_path', 'legacy_date'):
        relatives = FRESHNESS_TELOS_SOURCES
    else:
        relatives = set()
    for directory in ([''] if view in ('telos', 'legacy_path', 'legacy_date') else
                      ['CURRENT_STATE', 'IDEAL_STATE'] if view in ('state', 'registry') else []):
        relative = 'LIFEOS/USER/TELOS' + ('/' + directory if directory else '')
        source = memory._path(relative)
        physical = memory.root.parent / '.config/LIFEOS/USER/TELOS' / directory
        if source.resolve() != physical or source.is_symlink() or source.exists() and not source.is_dir():
            raise MemoryUnavailable('A freshness source directory changes its permitted physical path')
        if directory and source.exists():
            relatives.update(str(item.relative_to(memory.root)) for item in source.iterdir()
                             if is_state_source(str(item.relative_to(memory.root))))
    paths = [str(memory.root / relative) for relative in sorted(relatives)
             if (memory.root / relative).exists() or (memory.root / relative).is_symlink()]
    return read_markdown(memory, scope, paths, connection=connection)


def read(memory, scope, view, path, slug, *, check_current):
    _request(memory, view, path, slug)
    with memory._transaction() as connection:
        sources = _collect(memory, scope, connection, view, path)
        result = memory._native('read_freshness', view=view, path=path, slug=slug, sources=sources)
        if set(result) != {'value'} or len(json.dumps(result).encode()) > CORPUS_LIMIT:
            raise MemoryUnavailable('Native freshness returns an invalid read result')
        if _collect(memory, scope, connection, view, path) != sources:
            raise MemoryUnavailable('Freshness sources changed during rendering')
        check_current()
        return {'ok': True, 'value': result['value']}


def view(memory, scope, name, *, check_current):
    if name not in HTTP_VIEWS:
        raise ValueError('Choose a native freshness HTTP view')
    source_view = 'context' if name.startswith('context_') else 'telos'

    def collect(connection):
        sources = _collect(memory, scope, connection, source_view, None)
        if name == 'telos_health':
            sources = sorted({source['path']: source for source in
                [*sources, *_collect(memory, scope, connection, 'context', None)]}.values(),
                key=lambda source: source['path'])
        return sources

    with memory._transaction() as connection:
        sources = collect(connection)
        result = memory._native('freshness_view', target=HTTP_VIEWS[name], sources=sources)
        if (set(result) != {'status', 'body'} or result['status'] != 200 or not isinstance(result['body'], dict)
                or len(json.dumps(result).encode()) > CORPUS_LIMIT):
            raise MemoryUnavailable('Native freshness returns an invalid HTTP result')
        if collect(connection) != sources:
            raise MemoryUnavailable('Freshness sources changed during HTTP rendering')
        check_current()
        return result['body']


SYSTEM_PUBLICATIONS = frozenset(CONTEXT - CONTEXT_FILES - {TELOS})
WRITE_KINDS = frozenset({'telos', 'context', 'review', 'stamp'})


def _write_request(memory, kind, path, slug, by, scope):
    authorize(scope)
    if not {'principal', 'assistant', 'project'} <= set(scope.write):
        raise MemoryUnavailable('Timestamp publication requires unrestricted owner write access')
    if not isinstance(kind, str) or kind not in WRITE_KINDS:
        raise ValueError('Choose a native timestamp mutation')
    _request(memory, 'telos' if kind == 'telos' else 'frontmatter', path, None)
    if slug is not None and (kind != 'telos' or not isinstance(slug, str) or len(slug) > 128):
        raise ValueError('Choose a bounded native TELOS section slug')
    if by is None:
        by = scope.writer
    if not isinstance(by, str) or not by or len(by) > 256 or any(ord(char) < 32 for char in by):
        raise ValueError('Use a bounded single-line timestamp writer label')
    return by


def _source_signature(sources):
    from .memory_access import _digest
    return _digest(json.dumps(sources, sort_keys=True))


def _write_sources(memory, scope, connection, path):
    sources = _collect(memory, scope, connection, 'frontmatter', path)
    if Path(path).exists() and not sources:
        raise MemoryUnavailable('The timestamp source is excluded under the current policy')
    return sources


def publication_paths(memory, connection, scope, payload):
    import os
    from .memory_sources import SOURCE_LIMIT
    _write_request(memory, payload['kind'], payload['path'], payload['slug'], payload['by'], scope)
    sources = _write_sources(memory, scope, connection, payload['path'])
    if _source_signature(sources) != payload['source_signature']:
        raise MemoryConflict('The timestamp source changed before publication preparation')
    relative = Path(payload['path']).relative_to(memory.root).as_posix()
    path = memory._publication_path(relative)
    if path.exists() and (not path.is_file() or path.stat().st_uid != os.getuid()
                          or path.stat().st_size > SOURCE_LIMIT):
        raise MemoryUnavailable('The timestamp source needs a bounded owner publication path')
    return [relative] if sources else []


def write(memory, scope, kind, path, slug, by, *, check_current):
    from uuid import uuid4
    from .memory_transaction import publish
    by = _write_request(memory, kind, path, slug, by, scope)
    with memory._transaction() as connection:
        sources = _write_sources(memory, scope, connection, path)
        signature = _source_signature(sources)
    payload = {'operation': 'freshness_write', 'kind': kind, 'path': path, 'slug': slug,
               'by': by, 'source_signature': signature}
    output = []

    def current_sources(connection):
        try:
            return _write_sources(memory, scope, connection, path)
        except MemoryUnavailable as error:
            # A later excluded edit also remains the current source before any publication.
            raise MemoryConflict(str(error)) from error

    def apply(connection):
        current = current_sources(connection)
        if _source_signature(current) != signature:
            raise MemoryConflict('The timestamp source changed before native rendering')
        result = memory._native('freshness_write', kind=kind, path=path, slug=slug, by=by,
                                content=current[0]['content'] if current else None)
        required = {'changed'} | ({'sectionFound'} if kind == 'telos' else
                                 {'provenanceFlipped'} if kind == 'stamp' else set())
        if (set(result) != {'report', 'content'} or not isinstance(result['report'], dict)
                or set(result['report']) != required or any(type(value) is not bool for value in result['report'].values())
                or (not isinstance(result['content'], str) if result['report']['changed'] else result['content'] is not None)
                or len(json.dumps(result).encode()) > CORPUS_LIMIT):
            raise MemoryUnavailable('Native timestamp rendering changes its publication contract')
        if result['content'] is not None:
            accepted = memory._native('validate_source_batch', contents=[result['content']])['accepted']
            if accepted != [True] or memory._filter_history(connection, scope, result['content'], _now(), reviewed=True)['excluded']:
                raise MemoryUnavailable('The rendered timestamp source contains excluded text')
        if _source_signature(current_sources(connection)) != signature:
            raise MemoryConflict('The timestamp source changed during rendering')
        try:
            check_current()
        except MemoryUnavailable as error:
            raise MemoryConflict(str(error)) from error
        try:
            publication_paths(memory, connection, scope, payload)
        except MemoryUnavailable as error:
            raise MemoryConflict(str(error)) from error
        if result['content'] is not None:
            publish(memory._publication_path(Path(path).relative_to(memory.root).as_posix()), result['content'].encode())
        output.append(result['report'])
        return {'status': 'committed' if result['report']['changed'] else 'unchanged',
                'artifacts': int(result['report']['changed'])}

    receipt = memory._operation(scope, 'freshness-' + uuid4().hex, payload, apply)
    return {'ok': receipt['status'] in ('committed', 'unchanged'), 'report': output[0] if output else None}
