# ABOUTME: Admits fixed latest digests and bounded native LocalIntelligence history selections.
# ABOUTME: Rechecks physical sources, selection, and current owner authority before delivery.
from datetime import datetime, timedelta, timezone
from itertools import islice
import json
import re
from urllib.parse import parse_qs, urlencode, urlsplit

from .memory_access import MemoryUnavailable
from .memory_sources import authorize, _admit, _source_time, SOURCE_LIMIT, SOURCE_COUNT_LIMIT, CORPUS_LIMIT
from .memory_operational_views import projection
from .memory_tab_freshness import _checked

PRIMARY = 'LIFEOS/USER/CUSTOMIZATIONS/SKILLS/LocalIntelligence/latest.json'
HISTORY = 'LIFEOS/MEMORY/DATA/LocalIntelligence'
FALLBACK = HISTORY + '/latest.json'
ROUTES = frozenset('/api/local-intelligence' + suffix for suffix in ('', '/history', '/status', '/refresh'))
RANGES = {'week': 7, 'month': 30, 'year': 365}
DIGEST = r'\d{4}-\d{2}-\d{2}_.*_digest\.json'


def declared_source(relative):
    return relative in {PRIMARY, FALLBACK} or re.fullmatch(re.escape(HISTORY) + '/' + DIGEST, relative) is not None


def request_target(value):
    if not isinstance(value, str) or len(value) > 256:
        raise ValueError('LocalIntelligence requires a bounded native route')
    url = urlsplit(value)
    if url.scheme or url.netloc or url.fragment or url.path not in ROUTES:
        raise ValueError('Choose a fixed LocalIntelligence route')
    query = parse_qs(url.query, keep_blank_values=True, strict_parsing=True)
    if set(query) - {'range', 'running', 'started'} or any(len(values) != 1 for values in query.values()):
        raise ValueError('Choose declared LocalIntelligence state and selectors')
    if 'range' in query and (url.path != '/api/local-intelligence/history' or query['range'][0] not in RANGES):
        raise ValueError('Choose a native LocalIntelligence history range')
    for name in ('running', 'started'):
        if name not in query: continue
        if url.path != '/api/local-intelligence/status': raise ValueError('Runtime state requires the native status route')
        if name == 'running' and query[name][0] not in {'0', '1'}:
            raise ValueError('Choose declared LocalIntelligence runtime state')
        if name == 'started' and (re.fullmatch(r'[0-9]{1,16}', query[name][0]) is None
                or int(query[name][0]) > 8640000000000000):
            raise ValueError('Choose a valid native start timestamp')
    return url.path + ('?' + urlencode({k: v[0] for k, v in query.items()}) if query else '')


def _selection(memory, target, date):
    url = urlsplit(target)
    if url.path != '/api/local-intelligence/history':
        primary = _checked(memory, memory.root / PRIMARY)
        return [PRIMARY] + ([] if primary.exists() else [FALLBACK]), None
    directory = _checked(memory, memory.root / HISTORY)
    if not directory.exists(): return [], None
    if not directory.is_dir(): raise MemoryUnavailable('LocalIntelligence requires its fixed history directory')
    before = directory.stat()
    entries = list(islice(directory.iterdir(), SOURCE_COUNT_LIMIT + 1))
    if len(entries) > SOURCE_COUNT_LIMIT: raise MemoryUnavailable('LocalIntelligence discovery exceeds its entry limit')
    days = RANGES[parse_qs(url.query).get('range', ['week'])[0]]
    cutoff = (datetime.fromisoformat(date) - timedelta(days=days - 1)).date().isoformat()
    names = sorted((entry.name for entry in entries if re.fullmatch(DIGEST, entry.name)
        and entry.name[:10] >= cutoff), key=lambda value: value.encode('utf-16-be', 'surrogatepass'), reverse=True)
    after = directory.stat()
    _checked(memory, directory)
    keys = lambda info: (info.st_dev, info.st_ino, info.st_mtime_ns)
    if keys(before) != keys(after): raise MemoryUnavailable('LocalIntelligence discovery changes during selection')
    return [HISTORY + '/' + name for name in names], (keys(after), tuple(entry.name for entry in entries))


def _collect(memory, scope, connection, target, date):
    names, directory = _selection(memory, target, date)
    sources, fingerprints, modified, total = [], [], {}, 0
    keys = lambda info: (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns)
    candidates = []
    for relative in names:
        path = _checked(memory, memory.root / relative)
        if not path.exists():
            fingerprints.append((relative, None))
            continue
        if not path.is_file(): raise MemoryUnavailable('LocalIntelligence requires regular owner digest files')
        before = path.stat()
        if before.st_size > SOURCE_LIMIT: raise MemoryUnavailable('A LocalIntelligence digest exceeds its complete byte limit')
        with path.open('rb') as stream: raw = stream.read(SOURCE_LIMIT + 1)
        if len(raw) > SOURCE_LIMIT: raise MemoryUnavailable('A LocalIntelligence digest exceeds its complete byte limit')
        try: content = raw.decode('utf-8')
        except UnicodeError as error: raise MemoryUnavailable('LocalIntelligence requires valid UTF-8') from error
        after = path.stat()
        _checked(memory, path)
        if keys(before) != keys(after): raise MemoryUnavailable('A LocalIntelligence digest changes during collection')
        decoded = '' if content == '' else projection(content)
        if decoded is None: raise MemoryUnavailable('LocalIntelligence admission requires complete JSON')
        total += len(raw) + len(decoded.encode())
        if total > CORPUS_LIMIT: raise MemoryUnavailable('LocalIntelligence digests exceed their transport limit')
        candidates.append((relative, content, decoded, _source_time(after)))
        sources.append({'relative': relative, 'content': content})
        fingerprints.append((relative, keys(after), raw))
        modified[relative] = after.st_mtime_ns / 1000000
    checked = memory._native('validate_source_batch', contents=[decoded + '\n' + relative
        for relative, _, decoded, _ in candidates])['accepted'] if candidates else []
    for (relative, content, decoded, timestamp), accepted in zip(candidates, checked, strict=True):
        if accepted is not True or _admit(memory, connection, scope, content, relative,
                timestamp, projection=decoded)['excluded']:
            raise MemoryUnavailable('A LocalIntelligence digest is excluded under current owner policy')
    if _selection(memory, target, date) != (names, directory):
        raise MemoryUnavailable('LocalIntelligence selection changes during collection')
    return sources, (directory, fingerprints), modified


def view(memory, scope, target, *, check_current=None):
    target = request_target(target)
    url = urlsplit(target)
    authorize(scope)
    if not scope.principal: raise MemoryUnavailable('LocalIntelligence requires a bound owner')
    if check_current is not None: check_current()
    if url.path == '/api/local-intelligence/refresh':
        raise MemoryUnavailable('LocalIntelligence refresh requires governed background publication')
    date = datetime.now(timezone.utc).date().isoformat()
    query = parse_qs(url.query)
    native_target = url.path + ('?range=' + query['range'][0] if 'range' in query else '')
    with memory._transaction() as connection:
        sources, fingerprints, modified = _collect(memory, scope, connection, target, date)
        result = memory._native('local_intelligence_view', sources=sources, target=native_target, modified=modified,
            running=query.get('running') == ['1'], started=int(query.get('started', ['0'])[0]), date=date)
        if check_current is not None: check_current()
        if (_collect(memory, scope, connection, target, date) != (sources, fingerprints, modified)
                or datetime.now(timezone.utc).date().isoformat() != date):
            raise MemoryUnavailable('LocalIntelligence sources change during native rendering')
        if (not isinstance(result, dict) or set(result) != {'status', 'body'} or type(result['status']) is not int
                or result['status'] not in {200, 404} or len(json.dumps(result).encode()) > CORPUS_LIMIT):
            raise MemoryUnavailable('The native LocalIntelligence view changes its declared response')
        decoded = projection(json.dumps(result))
        if (decoded is None or memory._native('validate_source_batch', contents=[decoded])['accepted'] != [True]
                or memory._filter_history(connection, scope, decoded, datetime.now(timezone.utc).isoformat())['excluded']):
            raise MemoryUnavailable('The native LocalIntelligence response contains excluded text')
        if check_current is not None: check_current()
        return result
