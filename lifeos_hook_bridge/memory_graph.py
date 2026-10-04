# ABOUTME: Supplies current notes and admitted retained silos to the native memory graph algorithms.
# ABOUTME: Rechecks sources and authority before journaled publication of graph artifacts.
from itertools import count
import json
import os
from pathlib import Path
from uuid import uuid4

from .memory_access import MemoryUnavailable
from .memory_canonical import corpus, RESPONSE_LIMIT
from .memory_sources import authorize, read_markdown
from .memory_transaction import publish
from .memory_wiki import _directory_entries, _files


OUTPUTS = ('LIFEOS/MEMORY/GRAPH/graph.json', 'LIFEOS/MEMORY/GRAPH/PATTERNS.md')
COMMANDS = {'build', 'patterns', 'stats', 'related', 'validate'}


def publication_paths(memory, scope):
    authorize(scope)
    if not {'principal', 'assistant', 'project'} <= set(scope.write):
        raise MemoryUnavailable('Graph publication requires unrestricted owner write access')
    physical = memory.root.parent / '.config/LIFEOS/USER/MEMORY/GRAPH'
    for relative in OUTPUTS:
        path = memory._path(relative)
        if (path.resolve() != physical / path.name or path.is_symlink()
                or path.exists() and (not path.is_file() or path.stat().st_uid != os.getuid()
                                      or path.stat().st_size > RESPONSE_LIMIT
                                      or path.samefile(memory.database))):
            raise MemoryUnavailable('A graph artifact changes its permitted physical destination')
    return list(OUTPUTS)


def _collect(memory, scope, connection):
    root = memory.root / 'LIFEOS/MEMORY'
    current = corpus(memory, scope, str(root), connection=connection)
    sources = []
    for path, record in zip(current['files'], current['records'], strict=True):
        relative = Path(path).relative_to(current['root'])
        if len(relative.parts) == 3 and relative.parts[1] in ('People', 'Companies', 'Ideas', 'Research'):
            sources.append({'path': str(root / relative), 'content': record['content']})
    domains = ('People', 'Companies', 'Ideas', 'Research')
    sources.sort(key=lambda source: domains.index(Path(source['path']).parent.name))
    paths = []
    visits = count(1)
    work = root / 'WORK'
    if work.is_symlink():
        raise MemoryUnavailable('The graph work directory changes its permitted physical path')
    if work.exists():
        for directory in _directory_entries(work, visits):
            if directory.name in ('_archive', '_embeddings', '_harvest-queue', '_drafts'):
                continue
            if directory.is_symlink():
                raise MemoryUnavailable('The graph work source changes its permitted physical path')
            if directory.is_dir():
                for name in ('ISA.md', 'PRD.md'):
                    path = directory / name
                    if path.exists() or path.is_symlink():
                        paths.append(str(path))
                        break
    for relative in ('WISDOM/FRAMES', 'WISDOM/PRINCIPLES', 'LEARNING/SYNTHESIS'):
        paths.extend(str(path) for path in _files(root / relative, visits=visits))
    retained = read_markdown(memory, scope, paths, connection=connection)
    sources.extend({'path': source['path'], 'content': source['content']} for source in retained)
    if len(json.dumps(sources).encode()) > RESPONSE_LIMIT:
        raise MemoryUnavailable('The declared graph sources exceed their transport limit')
    return sources


def run(memory, scope, root, command, layer, target, *, check_current):
    authorize(scope)
    if (not isinstance(root, str) or not Path(root).is_absolute()
            or Path(root).resolve() != memory.root.parent / '.config/LIFEOS/USER/MEMORY'
            or not isinstance(command, str) or command not in COMMANDS
            or not isinstance(layer, str) or layer not in ('declared', 'all')
            or command == 'related' and (not isinstance(target, str) or not target or len(target) > 256)
            or command != 'related' and target is not None):
        raise MemoryUnavailable('Choose an installed native graph command and source root')

    def render(connection):
        sources = _collect(memory, scope, connection)
        result = memory._native('memory_graph', sources=sources, command=command, layer=layer, target=target)
        names = {'graph.json', 'PATTERNS.md'} if command in ('build', 'patterns') else set()
        if (set(result) != {'stdout', 'stderr', 'writes'} or not isinstance(result['stdout'], str)
                or not isinstance(result['stderr'], str)
                or not isinstance(result['writes'], list) or len(result['writes']) != len(names)
                or any(not isinstance(write, dict) or set(write) != {'name', 'content'}
                       or not isinstance(write['name'], str) or write['name'] not in names
                       or not isinstance(write['content'], str)
                       for write in result['writes'])
                or {write['name'] for write in result['writes']} != names
                or len(json.dumps(result).encode()) > RESPONSE_LIMIT):
            raise MemoryUnavailable('Native graph rendering changes its declared artifact response')
        if _collect(memory, scope, connection) != sources:
            raise MemoryUnavailable('The graph sources changed during rendering')
        check_current()
        return result

    if command not in ('build', 'patterns'):
        with memory._transaction() as connection:
            result = render(connection)
            return {'ok': True, 'stdout': result['stdout'], 'stderr': result['stderr']}
    output = []

    def apply(connection):
        result = render(connection)
        publication_paths(memory, scope)
        for write in result['writes']:
            publish(memory._path('LIFEOS/MEMORY/GRAPH/' + write['name']), write['content'].encode())
        output.append(result)
        return {'status': 'committed', 'artifacts': len(result['writes'])}

    receipt = memory._operation(scope, 'graph-' + uuid4().hex, {'operation': 'memory_graph',
        'command': command, 'layer': layer}, apply)
    return {'ok': receipt['status'] == 'committed', 'stdout': output[0]['stdout'] if output else '',
            'stderr': output[0]['stderr'] if output else '', 'receipt': receipt}
