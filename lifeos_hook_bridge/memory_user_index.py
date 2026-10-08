# ABOUTME: Supplies admitted owner Markdown to the native user index calculations.
# ABOUTME: Rechecks bounded directory discovery, source bytes, and authority before returning each index slice.
from datetime import datetime, timezone
from itertools import islice
import json
import os
from pathlib import Path

from .memory_access import MemoryUnavailable
from .memory_sources import authorize, _admit, _source_time, SOURCE_LIMIT, SOURCE_COUNT_LIMIT, CORPUS_LIMIT
from .memory_tab_freshness import _checked

FILTERS = {'': None, 'stats': 'stats', 'publish': 'publish_feed', 'stale': 'stale_queue', 'gaps': 'interview_gaps'}


def _collect(memory, scope, connection, skipped):
    authorize(scope)
    if not scope.principal:
        raise MemoryUnavailable('User indexes require a bound owner')
    root = memory.root / 'LIFEOS/USER'

    def check_root():
        if (root.resolve() != memory.root.parent / '.config/LIFEOS/USER'
                or not root.is_dir() or root.stat().st_uid != os.getuid()):
            raise MemoryUnavailable('User index discovery changes its installed owner root')
        return root

    check_root()
    sources, fingerprints, candidates = [], [], []
    discovered = total = 0

    def walk(directory, depth):
        nonlocal discovered, total
        check_root() if directory == root else _checked(memory, directory)
        if not directory.exists():
            fingerprints.append((str(directory.relative_to(memory.root)), None))
            return
        if not directory.is_dir():
            raise MemoryUnavailable('User index discovery requires fixed owner directories')
        entries = list(islice(directory.iterdir(), SOURCE_COUNT_LIMIT - discovered + 1))
        discovered += len(entries)
        if discovered > SOURCE_COUNT_LIMIT:
            raise MemoryUnavailable('User index discovery exceeds its entry limit')
        fingerprints.append((str(directory.relative_to(memory.root)),
            tuple(path.name for path in entries)))
        for path in entries:
            if path.is_dir() and path.name in skipped: continue
            if path.is_dir():
                if depth < 2: walk(path, depth + 1)
                continue
            if path.suffix != '.md': continue
            _checked(memory, path)
            if not path.is_file():
                raise MemoryUnavailable('User indexes require regular owner Markdown')
            before = path.stat()
            if before.st_size > SOURCE_LIMIT:
                raise MemoryUnavailable('A user index source exceeds its byte limit')
            with path.open('r', encoding='utf-8', newline='') as stream: content = stream.read()
            after = path.stat()
            _checked(memory, path)
            keys = lambda info: (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns)
            if keys(before) != keys(after):
                raise MemoryUnavailable('A user index source changes during collection')
            relative = str(path.relative_to(memory.root))
            fingerprints.append((relative, keys(after), content))
            candidates.append((relative, content, _source_time(after), {
                'relative': str(path.relative_to(root)), 'content': content,
                'size': after.st_size, 'modified': _source_time(after, milliseconds=True)}))
            total += len(content.encode()) + len(relative.encode())
            if total > CORPUS_LIMIT:
                raise MemoryUnavailable('User index sources exceed their transport limit')

    walk(root, 0)
    accepted = memory._native('validate_source_batch', contents=[content + '\n' + relative
        for relative, content, _, _ in candidates])['accepted'] if candidates else []
    for (relative, content, timestamp, source), valid in zip(candidates, accepted, strict=True):
        if valid is True and not _admit(memory, connection, scope, content, relative, timestamp)['excluded']:
            sources.append(source)
    if len(json.dumps(sources).encode()) > CORPUS_LIMIT:
        raise MemoryUnavailable('User index sources exceed their transport limit')
    return sources, fingerprints


def view(memory, scope, target, *, check_current=None):
    filter_name = target.partition('?filter=')[2]
    if filter_name not in FILTERS:
        raise ValueError('Choose a declared user index slice')
    registry = memory._native('user_index_registry')
    skipped = registry.get('skip_directories')
    if (set(registry) != {'skip_directories'} or not isinstance(skipped, list)
            or len(skipped) > 64 or any(not isinstance(name, str) or not name or '/' in name for name in skipped)):
        raise MemoryUnavailable('Native user index discovery changes its declared registry')
    if check_current is not None: check_current()
    with memory._transaction() as connection:
        sources, fingerprints = _collect(memory, scope, connection, skipped)
        result = memory._native('user_index', sources=sources)
        if check_current is not None: check_current()
        if _collect(memory, scope, connection, skipped) != (sources, fingerprints):
            raise MemoryUnavailable('User index sources change during native rendering')
        if (not isinstance(result, dict) or set(result) != {'index'} or not isinstance(result['index'], dict)
                or len(json.dumps(result).encode()) > CORPUS_LIMIT):
            raise MemoryUnavailable('The native user index changes its declared result')
        index = result['index']
        if set(index) != {'version','generated_at','user_dir','files','by_category','domains',
                          'publish_feed','stale_queue','interview_gaps','stats'}:
            raise MemoryUnavailable('The native user index changes its declared fields')
        if memory._filter_history(connection, scope, json.dumps(index), datetime.now(timezone.utc).isoformat())['excluded']:
            raise MemoryUnavailable('The native user index contains excluded source text')
        if check_current is not None: check_current()
        return {'status': 200, 'body': index[FILTERS[filter_name]] if FILTERS[filter_name] else index}
