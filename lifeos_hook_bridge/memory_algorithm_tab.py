# ABOUTME: Admits the fixed native Algorithm chain, selected doctrine, and cached summaries.
# ABOUTME: Rechecks complete source bytes, version metadata, and current owner authority after rendering.
from datetime import datetime, timezone
from itertools import islice
import json
import re
from urllib.parse import parse_qs, urlencode, urlsplit

from .memory_access import MemoryUnavailable
from .memory_sources import authorize, _admit, _source_time, SOURCE_LIMIT, SOURCE_COUNT_LIMIT, CORPUS_LIMIT
from .memory_operational_views import projection
from .memory_tab_freshness import _checked

LATEST = 'LIFEOS/ALGORITHM/LATEST'
CACHE = 'LIFEOS/MEMORY/STATE/algorithm-tab-summary.json'
DIRECTORY = 'LIFEOS/ALGORITHM'
PERSONAL = frozenset({'LIFEOS/USER/CONFIG/OPERATIONAL_RULES.md',
    'LIFEOS/USER/CONFIG/OperationalRulesExpanded.md',
    'LIFEOS/USER/DIGITAL_ASSISTANT/REFERENCE/WritingStyleBackstop.md',
    'LIFEOS/MEMORY/LEARNING/INCIDENTS/README.md'})
ROUTES = frozenset('/api/algorithm-tab' + suffix for suffix in ('', '/', '/file', '/doctrine', '/summary/regenerate'))
VERSION = r'\d{1,10}\.\d{1,10}\.\d{1,10}'


def request_target(value):
    if not isinstance(value, str) or len(value) > 256:
        raise ValueError('Algorithm views require a bounded native route')
    url = urlsplit(value)
    if url.scheme or url.netloc or url.fragment or url.path not in ROUTES:
        raise LookupError('Choose a declared Algorithm route')
    query = parse_qs(url.query, keep_blank_values=True, strict_parsing=True)
    if query:
        if (url.path != '/api/algorithm-tab/file' or set(query) - {'id', 'version'} or 'id' not in query
                or any(len(values) != 1 for values in query.values())
                or re.fullmatch(r'[a-z][a-z-]{0,63}', query['id'][0]) is None
                or 'version' in query and re.fullmatch(VERSION, query['version'][0]) is None):
            raise ValueError('Choose a fixed Algorithm file and version')
    return url.path + ('?' + urlencode({name: values[0] for name, values in query.items()}) if query else '')


def _catalog(memory):
    sources = memory._native('algorithm_tab_sources').get('sources')
    if (not isinstance(sources, list) or not sources or len(sources) > 32
            or any(not isinstance(source, dict) or set(source) != {'id', 'relative'}
                or not isinstance(source['id'], str) or re.fullmatch(r'[a-z][a-z-]{0,63}', source['id']) is None
                or not isinstance(source['relative'], str) or len(source['relative']) > 256
                or source['relative'].startswith('/') or any(part in {'', '.', '..'} for part in source['relative'].split('/'))
                for source in sources)
            or len({source['id'] for source in sources}) != len(sources)):
        raise MemoryUnavailable('Algorithm sources require the fixed native catalog')
    return {source['id']: source['relative'] for source in sources}


def _collect(memory, scope, connection, target, catalog):
    sources, fingerprints, metadata, total = [], [], {}, 0
    keys = lambda info: (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns)

    def read(relative):
        nonlocal total
        path = _checked(memory, memory.root / relative)
        if not path.exists():
            fingerprints.append((relative, None))
            return None
        if not path.is_file(): raise MemoryUnavailable('Algorithm reads require regular fixed owner sources')
        before = path.stat()
        if before.st_size > SOURCE_LIMIT: raise MemoryUnavailable('An Algorithm source exceeds its complete byte limit')
        with path.open('rb') as stream: raw = stream.read(SOURCE_LIMIT + 1)
        if len(raw) > SOURCE_LIMIT: raise MemoryUnavailable('An Algorithm source exceeds its complete byte limit')
        try: content = raw.decode('utf-8')
        except UnicodeError as error: raise MemoryUnavailable('Algorithm sources require valid UTF-8') from error
        after = path.stat()
        _checked(memory, path)
        if keys(before) != keys(after): raise MemoryUnavailable('An Algorithm source changes during collection')
        decoded = content
        if relative == CACHE:
            decoded = projection(content)
            if decoded is None:
                try: json.loads(content)
                except json.JSONDecodeError: decoded = content
                else: raise MemoryUnavailable('The Algorithm cache exceeds its decoded projection limit')
        total += len(raw) + len(decoded.encode())
        if total > CORPUS_LIMIT: raise MemoryUnavailable('Algorithm sources exceed their transport limit')
        valid = memory._native('validate_source_batch', contents=[decoded + '\n' + relative])['accepted']
        if valid != [True] or _admit(memory, connection, scope, content, relative,
                _source_time(after), projection=decoded)['excluded']:
            raise MemoryUnavailable('An Algorithm source is excluded under current owner policy')
        sources.append({'relative': relative, 'content': content})
        fingerprints.append((relative, keys(after), raw))
        metadata[relative] = {'size': after.st_size, 'modified': after.st_mtime_ns / 1000000}
        return content

    url = urlsplit(target)
    query = parse_qs(url.query)
    identifier = query.get('id', [''])[0]
    if url.path.endswith('/file') and identifier not in catalog:
        return [], [], {}, [], None
    version = query.get('version', [None])[0] if identifier == 'doctrine' else None
    if not url.path.endswith('/file') or identifier == 'doctrine' and version is None:
        latest = read(LATEST)
        version = latest.strip() if latest is not None else '0.0.0'
        if re.fullmatch(VERSION, version) is None:
            raise MemoryUnavailable('Algorithm doctrine requires a bounded native version')
    names = [catalog[identifier]] if url.path.endswith('/file') else [CACHE, *catalog.values()]
    for relative in names:
        read(relative.replace('{LATEST}', version or '0.0.0'))
    versions, directory_key = [], None
    if not url.path.endswith('/file'):
        directory = _checked(memory, memory.root / DIRECTORY)
        if not directory.is_dir(): raise MemoryUnavailable('Algorithm versions require the fixed native directory')
        before = directory.stat()
        entries = list(islice(directory.iterdir(), SOURCE_COUNT_LIMIT + 1))
        if len(entries) > SOURCE_COUNT_LIMIT: raise MemoryUnavailable('Algorithm discovery exceeds its entry limit')
        for entry in entries:
            if re.fullmatch('v' + VERSION + r'\.md', entry.name) is None: continue
            _checked(memory, entry)
            if not entry.is_file(): raise MemoryUnavailable('Algorithm versions require regular fixed files')
            info = entry.stat()
            relative = DIRECTORY + '/' + entry.name
            metadata[relative] = {'size': info.st_size, 'modified': info.st_mtime_ns / 1000000}
            versions.append(entry.name)
            fingerprints.append((relative, keys(info)))
        after = directory.stat()
        _checked(memory, directory)
        if (before.st_dev, before.st_ino, before.st_mtime_ns) != (after.st_dev, after.st_ino, after.st_mtime_ns):
            raise MemoryUnavailable('Algorithm version discovery changes during collection')
        directory_key = (after.st_dev, after.st_ino, after.st_mtime_ns, tuple(entry.name for entry in entries))
    return sources, fingerprints, metadata, versions, directory_key


def view(memory, scope, target, *, check_current=None):
    target = request_target(target)
    url = urlsplit(target)
    authorize(scope)
    if not scope.principal: raise MemoryUnavailable('Algorithm views require a bound owner')
    if check_current is not None: check_current()
    if url.path not in {'/api/algorithm-tab', '/api/algorithm-tab/', '/api/algorithm-tab/file'} or url.path.endswith('/file') and not url.query:
        raise MemoryUnavailable('Algorithm actions require governed publication and generation')
    catalog = _catalog(memory)
    with memory._transaction() as connection:
        admitted = _collect(memory, scope, connection, target, catalog)
        sources, fingerprints, metadata, versions, directory = admitted
        result = memory._native('algorithm_tab_view', sources=sources, target=target, metadata=metadata, versions=versions)
        if check_current is not None: check_current()
        if _collect(memory, scope, connection, target, catalog) != admitted:
            raise MemoryUnavailable('Algorithm sources change during native rendering')
        if (not isinstance(result, dict) or set(result) != {'status', 'body'} or type(result['status']) is not int
                or result['status'] not in {200, 404} or not isinstance(result['body'], dict)
                or len(json.dumps(result).encode()) > CORPUS_LIMIT):
            raise MemoryUnavailable('The native Algorithm view changes its declared response')
        decoded = projection(json.dumps(result))
        if (decoded is None or memory._native('validate_source_batch', contents=[decoded])['accepted'] != [True]
                or memory._filter_history(connection, scope, decoded, datetime.now(timezone.utc).isoformat())['excluded']):
            raise MemoryUnavailable('The native Algorithm view contains excluded text')
        if check_current is not None: check_current()
        return result
