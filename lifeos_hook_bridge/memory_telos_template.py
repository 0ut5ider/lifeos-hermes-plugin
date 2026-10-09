# ABOUTME: Admits the complete native Telos template Markdown and CSV selection.
# ABOUTME: Rechecks personal source identity and owner authority before returning sorted native data.
from datetime import datetime, timezone
from itertools import islice
import json
from pathlib import Path
import re

from .memory_access import MemoryUnavailable, MemoryConflict
from .memory_sources import authorize, _admit, _source_time, SOURCE_LIMIT, SOURCE_COUNT_LIMIT, CORPUS_LIMIT
from .memory_operational_views import projection
from .memory_tab_freshness import _checked

PREFIX = 'LIFEOS/USER/TELOS/'


def declared(relative):
    return re.fullmatch(re.escape(PREFIX) + r'(?:[^./][^/]*\.md|data/[^./][^/]*\.csv)', relative) is not None


def collect(memory, scope, connection):
    candidates, sources, fingerprints, total, entries_seen = [], [], [], 0, 0
    keys = lambda info: (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns)
    for relative, suffix in ((PREFIX.rstrip('/'), '.md'), (PREFIX + 'data', '.csv')):
        directory = _checked(memory, memory.root / relative)
        if not directory.exists():
            fingerprints.append((relative, None))
            continue
        if not directory.is_dir(): raise MemoryUnavailable('Telos template sources require their fixed owner directories')
        before = directory.stat()
        entries = sorted(islice(directory.iterdir(), SOURCE_COUNT_LIMIT + 1))
        entries_seen += len(entries)
        if entries_seen > SOURCE_COUNT_LIMIT: raise MemoryUnavailable('Telos template selection exceeds its directory limit')
        for path in entries:
            if path.name.startswith('.') or path.suffix != suffix: continue
            path = _checked(memory, path)
            if path.is_dir(): continue
            info = path.stat()
            if not path.is_file() or info.st_size > SOURCE_LIMIT:
                raise MemoryUnavailable('Telos template sources require bounded regular owner files')
            with path.open('rb') as stream: raw = stream.read(SOURCE_LIMIT + 1)
            if len(raw) > SOURCE_LIMIT: raise MemoryUnavailable('A Telos template source exceeds its byte limit')
            try: content = raw.decode('utf-8')
            except UnicodeError as error: raise MemoryUnavailable('Telos template sources require valid UTF-8') from error
            after = _checked(memory, path).stat()
            if keys(info) != keys(after): raise MemoryConflict('A Telos template source changes during collection')
            name = path.relative_to(memory.root).as_posix()
            total += len(raw)
            if total > CORPUS_LIMIT: raise MemoryUnavailable('Complete Telos template sources exceed their transport limit')
            sources.append({'name': path.name.replace(suffix, '', 1), 'filename': name[len(PREFIX):],
                'content': content, 'type': 'markdown' if suffix == '.md' else 'csv'})
            candidates.append((name, content, _source_time(after)))
            fingerprints.append((name, keys(after), raw))
        after = _checked(memory, directory).stat()
        if keys(before) != keys(after): raise MemoryConflict('Telos template selection changes during collection')
        fingerprints.append((relative, keys(after), tuple(path.name for path in entries)))
    if len(json.dumps(sources).encode()) > CORPUS_LIMIT:
        raise MemoryUnavailable('Complete Telos template data exceeds its transport limit')
    checked = memory._native('validate_source_batch', contents=[content + '\n' + relative
        for relative, content, timestamp in candidates])['accepted'] if candidates else []
    for (relative, content, timestamp), valid in zip(candidates, checked, strict=True):
        if valid is not True or _admit(memory, connection, scope, content, relative, timestamp)['excluded']:
            raise MemoryUnavailable('Complete Telos template context requires current safe owner sources')
    return sources, fingerprints


def view(memory, scope, *, check_current):
    authorize(scope)
    if not scope.principal: raise MemoryUnavailable('Telos template reads require a bound owner')
    check_current()
    with memory._transaction() as connection:
        sources, fingerprints = collect(memory, scope, connection)
        result = memory._native('telos_template_view', files=sources)
        check_current()
        if collect(memory, scope, connection) != (sources, fingerprints):
            raise MemoryConflict('Telos template sources change during native rendering')
        if (not isinstance(result, dict) or set(result) != {'files'} or not isinstance(result['files'], list)
                or len(result['files']) != len(sources) or len(json.dumps(result).encode()) > CORPUS_LIMIT
                or sorted(json.dumps(row, sort_keys=True) for row in result['files'])
                    != sorted(json.dumps(row, sort_keys=True) for row in sources)):
            raise MemoryUnavailable('The native Telos template changes its declared data')
        decoded = projection(json.dumps(result), field_limit=SOURCE_COUNT_LIMIT * 8 + 1)
        if (decoded is None or memory._native('validate_source_batch', contents=[decoded])['accepted'] != [True]
                or memory._filter_history(connection, scope, decoded, datetime.now(timezone.utc).isoformat())['excluded']):
            raise MemoryUnavailable('The native Telos template response contains excluded text')
        check_current()
        return {'ok': True, **result}
