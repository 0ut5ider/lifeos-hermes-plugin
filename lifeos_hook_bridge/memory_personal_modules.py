# ABOUTME: Supplies admitted owner sources to the native Books, Projects, and Assets views.
# ABOUTME: Rechecks fixed files, native source selection, and current owner authority after rendering.
from datetime import datetime, timezone
from itertools import islice
import json
import re
from urllib.parse import urlsplit

from .memory_access import MemoryUnavailable
from .memory_sources import authorize, _admit, _source_time, SOURCE_LIMIT, SOURCE_COUNT_LIMIT, CORPUS_LIMIT
from .memory_operational_views import projection
from .memory_tab_freshness import _checked


SOURCES = {
    'books': frozenset({'LIFEOS/USER/BOOKS.md'}),
    'projects': frozenset({'LIFEOS/USER/PROJECTS.md', 'LIFEOS/USER/PROJECTS_RETIRED.md',
                           'LIFEOS/USER/TELOS/TELOS.md'}),
    'assets': frozenset({'LIFEOS/USER/GEAR.md', 'LIFEOS/MEMORY/_NETWORK/assets.json'}),
}
NETWORK = 'LIFEOS/MEMORY/_NETWORK'
ROUTES = frozenset('/api/' + name + suffix for name in SOURCES for suffix in ('', '/list', '/status', '/health'))


def request_target(value):
    if not isinstance(value, str) or len(value) > 256:
        raise ValueError('Personal module views require a bounded native route')
    url = urlsplit(value)
    if url.scheme or url.netloc or url.fragment or url.path not in ROUTES:
        raise ValueError('Choose a fixed personal module route')
    if url.query and not (url.path.endswith(('/status', '/health')) and url.query in {'running=0', 'running=1'}):
        raise ValueError('Personal module views require declared native runtime state')
    return url.path + ('?' + url.query if url.query else '')


def _selection(memory, module):
    names = set(SOURCES[module])
    directory = None
    if module == 'assets':
        path = _checked(memory, memory.root / NETWORK)
        if path.exists():
            if not path.is_dir(): raise MemoryUnavailable('Asset topology discovery requires the fixed owner directory')
            before = path.stat()
            entries = list(islice(path.iterdir(), SOURCE_COUNT_LIMIT + 1))
            if len(entries) > SOURCE_COUNT_LIMIT:
                raise MemoryUnavailable('Asset topology discovery exceeds its entry limit')
            filenames = sorted((entry.name for entry in entries if re.fullmatch(r'topology-snapshot-.*\.md', entry.name)),
                key=lambda value: value.encode('utf-16-be', 'surrogatepass'))
            _checked(memory, path)
            after = path.stat()
            if (before.st_dev, before.st_ino, before.st_mtime_ns) != (after.st_dev, after.st_ino, after.st_mtime_ns):
                raise MemoryUnavailable('Asset topology discovery changes during selection')
            directory = (after.st_dev, after.st_ino, tuple(filenames))
            if filenames: names.add(NETWORK + '/' + filenames[-1])
    return names, directory


def _collect(memory, scope, connection, module):
    names, directory = _selection(memory, module)
    candidates, fingerprints = [], []
    total = 0
    keys = lambda info: (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns)
    for relative in sorted(names):
        path = _checked(memory, memory.root / relative)
        if not path.exists():
            fingerprints.append((relative, None))
            continue
        if not path.is_file(): raise MemoryUnavailable('Personal module sources require regular owner files')
        before = path.stat()
        if before.st_size > SOURCE_LIMIT: raise MemoryUnavailable('A personal module source exceeds its byte limit')
        with path.open('rb') as stream: raw = stream.read(SOURCE_LIMIT + 1)
        if len(raw) > SOURCE_LIMIT: raise MemoryUnavailable('A personal module source exceeds its byte limit')
        try: content = raw.decode('utf-8')
        except UnicodeError as error:
            raise MemoryUnavailable('Personal module sources require valid UTF-8') from error
        _checked(memory, path)
        after = path.stat()
        if keys(before) != keys(after): raise MemoryUnavailable('A personal module source changes during collection')
        decoded = projection(content) if relative.endswith('.json') else content
        if decoded is None: raise MemoryUnavailable('A personal module JSON source is incomplete')
        total += len(raw) + len(decoded.encode())
        if total > CORPUS_LIMIT: raise MemoryUnavailable('Personal module sources exceed their transport limit')
        candidates.append((relative, content, decoded, _source_time(after)))
        fingerprints.append((relative, keys(after), content))
    if _selection(memory, module) != (names, directory):
        raise MemoryUnavailable('Personal module source selection changes during collection')
    checked = memory._native('validate_source_batch', contents=[decoded + '\n' + relative
        for relative, _, decoded, _ in candidates])['accepted'] if candidates else []
    for (relative, content, decoded, timestamp), accepted in zip(candidates, checked, strict=True):
        if accepted is not True or _admit(memory, connection, scope, content, relative,
                timestamp, projection=decoded)['excluded']:
            raise MemoryUnavailable('A personal module source is excluded under current owner policy')
    return [{'relative': relative, 'content': content} for relative, content, _, _ in candidates], (directory, fingerprints)


def view(memory, scope, target, *, check_current=None):
    target = request_target(target)
    url = urlsplit(target)
    module = url.path.split('/')[2]
    authorize(scope)
    if not scope.principal: raise MemoryUnavailable('Personal module views require a bound owner')
    if check_current is not None: check_current()
    with memory._transaction() as connection:
        sources, fingerprints = _collect(memory, scope, connection, module)
        result = memory._native('personal_module_view', module=module, target=url.path, sources=sources,
            running=url.query == 'running=1')
        if check_current is not None: check_current()
        if _collect(memory, scope, connection, module) != (sources, fingerprints):
            raise MemoryUnavailable('Personal module sources change during native rendering')
        if (not isinstance(result, dict) or set(result) != {'status', 'body'} or result['status'] != 200
                or not isinstance(result['body'], dict) or len(json.dumps(result).encode()) > CORPUS_LIMIT):
            raise MemoryUnavailable('The native personal module changes its declared response')
        decoded = projection(json.dumps(result))
        if decoded is None or memory._native('validate_source_batch', contents=[decoded])['accepted'] != [True] or memory._filter_history(
                connection, scope, decoded, datetime.now(timezone.utc).isoformat())['excluded']:
            raise MemoryUnavailable('The native personal module response contains excluded source text')
        if check_current is not None: check_current()
        return result
