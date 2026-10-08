# ABOUTME: Admits selected company overviews and revenue reports from the physical owner business directory.
# ABOUTME: Bounds directory discovery and rechecks source labels, content, metadata, and authority after rendering.
from datetime import datetime, timezone
from itertools import islice
import json

from .memory_access import MemoryUnavailable
from .memory_sources import authorize, _admit, _source_time, SOURCE_LIMIT, SOURCE_COUNT_LIMIT, CORPUS_LIMIT
from .memory_tab_freshness import _checked

BUSINESS = 'LIFEOS/USER/WORK/YOUR_COMPANIES'


def _collect(memory, scope, connection):
    root = _checked(memory, memory.root / BUSINESS)
    fingerprints, candidates = [], []
    discovered = 0
    total = 0
    keys = lambda info: (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns)

    def entries(directory):
        nonlocal discovered
        _checked(memory, directory)
        if not directory.exists():
            fingerprints.append((str(directory), None))
            return []
        if not directory.is_dir():
            raise MemoryUnavailable('Business discovery requires physical owner directories')
        items = list(islice(directory.iterdir(), SOURCE_COUNT_LIMIT + 1))
        discovered += len(items)
        if discovered > SOURCE_COUNT_LIMIT:
            raise MemoryUnavailable('Business discovery exceeds its entry limit')
        fingerprints.append((str(directory), keys(directory.stat()), tuple(item.name for item in items)))
        return items

    def source(path):
        nonlocal total
        _checked(memory, path)
        if not path.exists():
            fingerprints.append((str(path), None))
            return
        if not path.is_file():
            raise MemoryUnavailable('Business sources require regular owner markdown')
        before = path.stat()
        if before.st_size > SOURCE_LIMIT:
            raise MemoryUnavailable('A business source exceeds its byte limit')
        with path.open('r', encoding='utf-8', newline='') as stream: content = stream.read()
        total += len(content.encode())
        if total > CORPUS_LIMIT:
            raise MemoryUnavailable('Business sources exceed their transport limit')
        after = path.stat()
        _checked(memory, path)
        if keys(before) != keys(after):
            raise MemoryUnavailable('A business source changes during collection')
        fingerprints.append((str(path), keys(after), content))
        candidates.append((path.relative_to(memory.root).as_posix(), content, _source_time(after)))

    directories = []
    for path in entries(root):
        if path.name.startswith('.'): continue
        _checked(memory, path)
        if path.is_dir():
            revenue = _checked(memory, path / 'REVENUE')
            directories.append((path, revenue.exists()))
    fingerprints.append(tuple((str(path), exists) for path, exists in directories))
    selected = next((path for path, exists in directories if exists), directories[0][0] if directories else None)
    company = selected.name if selected is not None else ''
    company_timestamp = _source_time(selected.stat()) if selected is not None else None
    if selected is not None:
        fingerprints.append((str(selected), keys(selected.stat())))
        source(selected / 'README.md')
        for path in entries(selected / 'REVENUE'):
            if path.name.endswith('.md'): source(path)
    source(root / 'README.md')
    contents = [content + '\n' + relative for relative, content, _ in candidates]
    if selected is not None: contents.append(selected.relative_to(memory.root).as_posix())
    if len(json.dumps(contents).encode()) > CORPUS_LIMIT:
        raise MemoryUnavailable('Business source projections exceed their transport limit')
    checked = memory._native('validate_source_batch', contents=contents)['accepted'] if contents else []
    sources = [{'relative': relative, 'content': content}
        for (relative, content, timestamp), accepted in zip(candidates, checked[:len(candidates)], strict=True)
        if accepted is True and not _admit(memory, connection, scope, content, relative, timestamp)['excluded']]
    if selected is not None and (checked[-1] is not True or _admit(memory, connection, scope, '',
            selected.relative_to(memory.root).as_posix(), company_timestamp)['excluded']):
        company = ''
        sources = [source for source in sources if source['relative'] == BUSINESS + '/README.md']
    return company, sources, fingerprints


def view(memory, scope, *, check_current=None):
    authorize(scope)
    if not scope.principal:
        raise MemoryUnavailable('Business views require a bound owner')
    if check_current is not None: check_current()
    with memory._transaction() as connection:
        company, sources, fingerprints = _collect(memory, scope, connection)
        result = memory._native('life_business_view', company=company, sources=sources)
        if check_current is not None: check_current()
        if _collect(memory, scope, connection) != (company, sources, fingerprints):
            raise MemoryUnavailable('Business sources change during native rendering')
        if (not isinstance(result, dict) or set(result) != {'status', 'body'}
                or type(result['status']) is not int or result['status'] != 200
                or not isinstance(result['body'], dict) or len(json.dumps(result).encode()) > CORPUS_LIMIT):
            raise MemoryUnavailable('The native business view changes its declared response')
        if memory._filter_history(connection, scope, json.dumps(result), datetime.now(timezone.utc).isoformat())['excluded']:
            raise MemoryUnavailable('The native business view contains excluded source text')
        if check_current is not None: check_current()
        return result
