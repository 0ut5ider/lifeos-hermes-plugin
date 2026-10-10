# ABOUTME: Supplies current admitted graph snapshots to the native Atlas dashboard renderer.
# ABOUTME: Rechecks fixed collector sources, snapshot bytes, and owner authority before delivery.
from datetime import datetime, timezone
import json

from .memory_access import MemoryUnavailable
from .memory_sources import (authorize, _admit, _source_time, SOURCE_LIMIT, CORPUS_LIMIT,
                             json_projection)
from .memory_tab_freshness import _checked
from .memory_operational_views import projection, project_value, PROJECTION_FIELD_LIMIT


SNAPSHOT = 'atlas/snapshot.json'
CACHE = 'LIFEOS/MEMORY/STATE/atlas-insights.json'
DATABASE = 'atlas/graph.json'
COLLECTOR_SOURCES = frozenset({'LIFEOS/USER/GEAR.md', 'LIFEOS/USER/PROJECTS.md'})
SOURCES = COLLECTOR_SOURCES | frozenset({SNAPSHOT, CACHE})
GRAPH_TABLES = frozenset({'asset', 'edge', 'source_observation', 'edge_observation', 'lifecycle_event', 'sync_run'})
TABLE_ROW_LIMIT = 2048


def capacity_projection(content, label):
    count = 0
    def collect(text):
        nonlocal count
        count += 1
        return False
    project_value(json.loads(content), collect)
    if count > PROJECTION_FIELD_LIMIT:
        raise MemoryUnavailable(f'Atlas capacity: {label} projection fields {count} exceed {PROJECTION_FIELD_LIMIT}')
    decoded = projection(content)
    if decoded is None:
        raise MemoryUnavailable(f'Atlas capacity: {label} projection exceeds {CORPUS_LIMIT} bytes')
    return decoded, count


def admit_graph(memory, scope, connection, graph, timestamp):
    if (not isinstance(graph, dict) or set(graph) != {'graph', 'metrics'} or not isinstance(graph['graph'], dict)
            or set(graph['graph']) != GRAPH_TABLES or not isinstance(graph['metrics'], dict)
            or any(not isinstance(rows, list) for rows in graph['graph'].values())
            or len(json.dumps(graph).encode()) > CORPUS_LIMIT):
        raise MemoryUnavailable('The Atlas graph changes its declared bounded response')
    counts = {name: len(rows) for name, rows in graph['graph'].items()}
    for name, count in counts.items():
        if count > TABLE_ROW_LIMIT:
            raise MemoryUnavailable(f'Atlas capacity: {name} rows {count} exceed {TABLE_ROW_LIMIT}')
    content = json.dumps(graph['graph'], ensure_ascii=False)
    decoded, fields = capacity_projection(content, 'graph')
    if (memory._native('validate_source_batch', contents=[decoded])['accepted'] != [True] or _admit(
            memory, connection, scope, content, DATABASE, timestamp, projection=decoded)['excluded']):
        raise MemoryUnavailable('The Atlas graph is excluded under the current owner policy')
    return {'graph_fields': {'used': fields, 'limit': PROJECTION_FIELD_LIMIT},
        'graph_projection_bytes': {'used': len(decoded.encode()), 'limit': CORPUS_LIMIT},
        'tables': {name: {'used': count, 'limit': TABLE_ROW_LIMIT} for name, count in counts.items()}}


def source_path(memory, relative):
    if relative not in SOURCES | {DATABASE}:
        raise MemoryUnavailable('Atlas requires fixed native sources')
    path = (memory.root.parent / '.local/state/lifeos/atlas' / ('snapshot.json' if relative == SNAPSHOT else 'atlas.db')
            if relative in {SNAPSHOT, DATABASE} else memory.root / relative)
    return _checked(memory, path)


def _collect(memory, scope, connection, *, insights=False, sources=None):
    candidates, fingerprints = [], []
    keys = lambda info: (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns)
    total = 0
    for relative in sorted(sources if sources is not None else SOURCES if insights else SOURCES - {CACHE}):
        path = source_path(memory, relative)
        if not path.exists():
            fingerprints.append((relative, None))
            continue
        if not path.is_file():
            raise MemoryUnavailable('Atlas sources require regular owner files')
        before = path.stat()
        if before.st_size > SOURCE_LIMIT:
            raise MemoryUnavailable('An Atlas source exceeds its byte limit')
        with path.open('rb') as stream: raw = stream.read(SOURCE_LIMIT + 1)
        if len(raw) > SOURCE_LIMIT:
            raise MemoryUnavailable('An Atlas source exceeds its byte limit')
        try: content = raw.decode('utf-8')
        except UnicodeError as error:
            raise MemoryUnavailable('Atlas sources require valid UTF-8') from error
        source_path(memory, relative)
        after = path.stat()
        if keys(before) != keys(after):
            raise MemoryUnavailable('An Atlas source changes during collection')
        decoded = projection(content) if relative in {SNAPSHOT, CACHE} else content
        if decoded is None:
            raise MemoryUnavailable('The Atlas snapshot requires complete JSON')
        total += len(raw) + len(decoded.encode())
        if total > CORPUS_LIMIT:
            raise MemoryUnavailable('Atlas sources exceed their transport limit')
        fingerprints.append((relative, keys(after), content))
        candidates.append((relative, content, decoded, _source_time(after), after.st_mtime_ns / 1_000_000))
    checked = memory._native('validate_source_batch', contents=[decoded + '\n' + relative
        for relative, _, decoded, _, _ in candidates])['accepted'] if candidates else []
    for (relative, content, decoded, timestamp, _), accepted in zip(candidates, checked, strict=True):
        if accepted is not True or _admit(memory, connection, scope, content, relative,
                timestamp, projection=decoded)['excluded']:
            raise MemoryUnavailable('An Atlas source is excluded under the current owner policy')
    snapshot = next(({'content': content, 'modified_ms': modified}
        for relative, content, _, _, modified in candidates if relative == SNAPSHOT), None)
    cache = next((content for relative, content, _, _, _ in candidates if relative == CACHE), None)
    return snapshot, cache, fingerprints


def collect(memory, scope, collector, *, check_current=None):
    if not isinstance(collector, str) or collector not in {'gear', 'projects'}:
        raise ValueError('Choose a declared Atlas owner collector')
    authorize(scope)
    if not scope.principal: raise MemoryUnavailable('Atlas collectors require a bound owner')
    sources = frozenset({'LIFEOS/USER/' + ('GEAR.md' if collector == 'gear' else 'PROJECTS.md')})
    if check_current is not None: check_current()
    with memory._transaction() as connection:
        _, _, fingerprints = _collect(memory, scope, connection, sources=sources)
        content = fingerprints[0][2] if len(fingerprints[0]) == 3 else None
        result = memory._native('atlas_collect', collector=collector, content=content)
        if check_current is not None: check_current()
        if _collect(memory, scope, connection, sources=sources)[2] != fingerprints:
            raise MemoryUnavailable('An Atlas collector source changes during native rendering')
        if (not isinstance(result, dict) or set(result) != {'complete', 'assets', 'edges'}
                or type(result['complete']) is not bool or not isinstance(result['assets'], list)
                or not isinstance(result['edges'], list) or len(json.dumps(result).encode()) > CORPUS_LIMIT):
            raise MemoryUnavailable('The native Atlas collector changes its declared result')
        if memory._filter_history(connection, scope, json.dumps(result),
                datetime.now(timezone.utc).isoformat())['excluded']:
            raise MemoryUnavailable('The native Atlas collector contains excluded source text')
        if check_current is not None: check_current()
        return {'ok': True, 'result': result}


def _graph(memory, scope, connection):
    path = _checked(memory, memory.root.parent / '.local/state/lifeos/atlas/atlas.db')
    if not path.exists(): return None
    before = path.stat()
    graph = memory._native('atlas_graph_state')
    _checked(memory, path)
    after = path.stat()
    keys = lambda info: (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns)
    if keys(before) != keys(after):
        raise MemoryUnavailable('The Atlas graph changes during collection')
    admit_graph(memory, scope, connection, graph, _source_time(after))
    return graph, keys(after)


def view(memory, scope, *, target='/api/atlas', check_current=None):
    authorize(scope)
    if not scope.principal:
        raise MemoryUnavailable('Atlas views require a bound owner')
    if check_current is not None: check_current()
    with memory._transaction() as connection:
        insights = target == '/api/atlas/insights'
        snapshot, cache, fingerprints = _collect(memory, scope, connection, insights=insights)
        graph = _graph(memory, scope, connection) if insights else None
        result = (memory._native('atlas_insights_view', metrics=graph[0]['metrics'] if graph else None, cache=cache)
                  if insights else memory._native('atlas_snapshot_view', snapshot=snapshot))
        if check_current is not None: check_current()
        if _collect(memory, scope, connection, insights=insights) != (snapshot, cache, fingerprints) or (
                insights and _graph(memory, scope, connection) != graph):
            raise MemoryUnavailable('Atlas sources change during native rendering')
        if (not isinstance(result, dict) or set(result) != {'status', 'body'} or result['status'] != 200
                or not isinstance(result['body'], dict) or len(json.dumps(result).encode()) > CORPUS_LIMIT):
            raise MemoryUnavailable('The native Atlas view changes its declared response')
        if memory._filter_history(connection, scope, json.dumps(result),
                datetime.now(timezone.utc).isoformat())['excluded']:
            raise MemoryUnavailable('The native Atlas response contains excluded source text')
        if check_current is not None: check_current()
        return result
