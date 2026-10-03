# ABOUTME: Selects current native notes, retained silos, and documentation for authenticated wiki views.
# ABOUTME: Validates fixed routes and renders each request in an isolated native worker.
from datetime import datetime, timezone
from itertools import count
import json
import os
from pathlib import Path
import re
from typing import Iterator
from urllib.parse import parse_qsl, quote, unquote, urlencode, urlsplit

from .memory_access import MemoryUnavailable
from .memory_canonical import corpus, RESPONSE_LIMIT
from .memory_sources import read_markdown, SOURCE_COUNT_LIMIT

DOMAINS = {'People': 'person', 'Companies': 'company', 'Ideas': 'idea',
           'Blogs': 'blog', 'Books': 'book', 'Research': 'research'}


def _directory_entries(directory: Path, visits: Iterator[int]) -> list[Path]:
    paths = []
    with os.scandir(directory) as entries:
        for entry in entries:
            if next(visits) > SOURCE_COUNT_LIMIT:
                raise MemoryUnavailable('The wiki directory exceeds its traversal count limit')
            paths.append(Path(entry.path))
    return sorted(paths)


def _files(directory: Path, *, recursive: bool = True, hide_metadata: bool = True,
           visits: Iterator[int] | None = None) -> list[Path]:
    if directory.is_symlink():
        raise MemoryUnavailable('The wiki directory changes its permitted physical path')
    if not directory.exists():
        return []
    result = []
    pending = [directory]
    visits = count(1) if visits is None else visits
    while pending:
        parent = pending.pop()
        for path in _directory_entries(parent, visits):
            if path.name.startswith('.') or (hide_metadata and path.name.startswith('_')):
                continue
            if path.is_symlink():
                raise MemoryUnavailable('The wiki source changes its permitted physical path')
            if path.is_dir() and recursive:
                pending.append(path)
            elif path.is_file() and path.suffix == '.md':
                result.append(path)
    return sorted(result)


def _retained_sources(memory, scope, connection) -> list[dict]:
    root = memory.root / 'LIFEOS'
    selected = {}
    visits = count(1)

    def add(path, category, slug, group=None):
        selected[str(path)] = {'category': category, 'slug': slug, **({'group': group} if group else {})}
        if len(selected) > SOURCE_COUNT_LIMIT:
            raise MemoryUnavailable('The wiki corpus exceeds its source count limit')

    prompt = root / 'LIFEOS_SYSTEM_PROMPT.md'
    if prompt.exists() or prompt.is_symlink():
        add(prompt, 'system-doc', 'LIFEOS_SYSTEM_PROMPT', 'Overview')
    documentation = root / 'DOCUMENTATION'
    for path in _files(documentation, visits=visits):
        relative = path.relative_to(documentation)
        group = 'Overview' if len(relative.parts) == 1 else path.parent.name
        add(path, 'system-doc', path.stem if len(relative.parts) == 1 else group + '__' + path.stem, group)
    for path in _files(root / 'ALGORITHM', recursive=False, hide_metadata=False, visits=visits):
        add(path, 'system-doc', 'Algorithm__' + path.stem, 'Algorithm')
    work = root / 'MEMORY/WORK'
    if work.is_symlink():
        raise MemoryUnavailable('The wiki work directory changes its permitted physical path')
    if work.exists():
        for directory in _directory_entries(work, visits):
            if directory.name.startswith(('.', '_')):
                continue
            if directory.is_symlink():
                raise MemoryUnavailable('The wiki work source changes its permitted physical path')
            path = directory / 'ISA.md'
            if directory.is_dir() and (path.exists() or path.is_symlink()):
                add(path, 'isa', directory.name)
    for silo, subdirectories, category in (('LEARNING', ('SYSTEM', 'ALGORITHM', 'SYNTHESIS'), 'lesson'),
            ('WISDOM', ('FRAMES', 'PRINCIPLES', 'META'), 'wisdom')):
        for sub in subdirectories:
            directory = root / 'MEMORY' / silo / sub
            for path in _files(directory, visits=visits):
                slug = sub + '--' + path.relative_to(directory).with_suffix('').as_posix().replace('/', '--')
                add(path, category, slug, sub.capitalize())
    directory = root / 'MEMORY/RESEARCH'
    for path in _files(directory, visits=visits):
        add(path, 'research', path.relative_to(directory).with_suffix('').as_posix().replace('/', '--'))
    return [{key: source[key] for key in ('path', 'content', 'lastModified')} | selected[source['path']]
            for source in read_markdown(memory, scope, list(selected), connection=connection)]

def request_target(value: object) -> str:
    if not isinstance(value, str) or len(value) > 8192 or any(ord(char) < 32 for char in value):
        raise ValueError('Choose a fixed wiki read route')
    url = urlsplit(value)
    if url.scheme or url.netloc or url.fragment:
        raise ValueError('Wiki reads cannot select a server')
    path = url.path
    fixed = {'/api/wiki', '/api/wiki/graph', '/api/wiki/search'}
    match = re.fullmatch(r'/api/wiki/(?:doc|backlinks)/([^/]+)|/api/wiki/knowledge/([^/]+)/([^/]+)', path)
    if path not in fixed and match is None:
        raise LookupError('This wiki route is not a governed read view')
    if match:
        for part in (part for part in match.groups() if part is not None):
            if re.search(r'%(?![0-9A-Fa-f]{2})', part):
                raise ValueError('Wiki reads require valid page names')
            decoded = unquote(part, errors='strict')
            if (len(decoded) > 256 or decoded in {'.', '..'} or not decoded
                    or any(char in '/\\%' or ord(char) < 32 or ord(char) == 127 for char in decoded)):
                raise ValueError('Wiki reads require valid page names')
        path = '/'.join(quote(unquote(part, errors='strict'), safe='') for part in path.split('/'))
    query = parse_qsl(url.query, keep_blank_values=True, strict_parsing=True)
    if path != '/api/wiki/search' and query:
        raise ValueError('Only wiki search accepts query parameters')
    if (any(key not in {'q', 'limit'} for key, _ in query)
            or len({key for key, _ in query}) != len(query)):
        raise ValueError('Wiki search accepts one query and one result limit')
    for key, argument in query:
        if key == 'q' and (len(argument) > 1024 or any(ord(char) < 32 for char in argument)):
            raise ValueError('Wiki search query exceeds its limit')
        if key == 'limit' and (not re.fullmatch(r'[0-9]{1,3}', argument) or not 1 <= int(argument) <= 200):
            raise ValueError('Wiki search result limit must be between 1 and 200')
    return path + ('?' + urlencode(query) if query else '')


def view(memory, scope, target: str) -> dict:
    target = request_target(target)
    physical = memory.root.parent / '.config/LIFEOS/USER/MEMORY'
    with memory._transaction() as connection:
        current = corpus(memory, scope, str(physical), connection=connection)
        sources = _retained_sources(memory, scope, connection)
        for record in current['records']:
            relative = Path(record['provenance']['path'])
            if len(relative.parts) != 3 or relative.parts[0] != 'KNOWLEDGE' or relative.parts[1] not in DOMAINS:
                continue
            path = physical / relative
            if str(path) not in current['files']:
                raise MemoryUnavailable('The wiki source changes its declared canonical path')
            sources.append({'path': str(path), 'content': record['content'],
                'lastModified': datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat(),
                'category': DOMAINS[relative.parts[1]], 'slug': path.stem})
        if len(json.dumps(sources).encode()) > RESPONSE_LIMIT:
            raise MemoryUnavailable('The declared wiki sources exceed their transport limit')
        result = memory._native('wiki_view', target=target, sources=sources)
        if (set(result) != {'status', 'body'} or type(result['status']) is not int
                or result['status'] not in {200, 404} or not isinstance(result['body'], dict)
                or len(json.dumps(result).encode()) > RESPONSE_LIMIT):
            raise MemoryUnavailable('Native wiki rendering returned an invalid response')
        return result
