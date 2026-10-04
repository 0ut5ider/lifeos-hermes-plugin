# ABOUTME: Supplies admitted current source bytes and times to native freshness readers.
# ABOUTME: Rechecks source collection and owner authority before returning native results.
import json
from pathlib import Path

from .memory_access import MemoryUnavailable
from .memory_sources import (CONTEXT_FILES, CORPUS_LIMIT, FRESHNESS_TELOS_SOURCES,
                             authorize, is_state_source, read_markdown)


TELOS = 'LIFEOS/USER/TELOS/TELOS.md'
CONTEXT = CONTEXT_FILES | {TELOS, 'LIFEOS/LIFEOS_SYSTEM_PROMPT.md',
    'LIFEOS/DOCUMENTATION/ARCHITECTURE_SUMMARY.md', 'LIFEOS/DOCUMENTATION/LifeosSystemArchitecture.md'}
VIEWS = frozenset({'telos', 'context', 'state', 'registry', 'frontmatter', 'legacy_path', 'legacy_date'})
HTTP_VIEWS = {'telos_freshness': '/api/telos/freshness', 'telos_stale': '/api/telos/freshness/stale',
    'telos_freshness_summary': '/api/telos/freshness/summary', 'context_freshness': '/api/freshness',
    'context_freshness_summary': '/api/freshness/summary'}


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
    with memory._transaction() as connection:
        sources = _collect(memory, scope, connection, source_view, None)
        result = memory._native('freshness_view', target=HTTP_VIEWS[name], sources=sources)
        if (set(result) != {'status', 'body'} or result['status'] != 200 or not isinstance(result['body'], dict)
                or len(json.dumps(result).encode()) > CORPUS_LIMIT):
            raise MemoryUnavailable('Native freshness returns an invalid HTTP result')
        if _collect(memory, scope, connection, source_view, None) != sources:
            raise MemoryUnavailable('Freshness sources changed during HTTP rendering')
        check_current()
        return result['body']
