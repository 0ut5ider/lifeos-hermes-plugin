# ABOUTME: Classifies declared Life source text and opaque metadata for explicit owner review.
# ABOUTME: Preserves source bytes and supplies decoded projections without reading lab report bodies.
import json
from pathlib import Path
import re

from .memory_access import MemoryUnavailable
from .memory_sources import _source_time, SOURCE_LIMIT, SOURCE_COUNT_LIMIT, CORPUS_LIMIT, json_projection
from .memory_tab_freshness import _checked
from .memory_life_finances import SOURCES as FINANCE_SOURCES

TELOS = frozenset('LIFEOS/USER/TELOS/' + name + '.md' for name in ('CURRENT', 'LEARNED', '2036', 'STATUS'))
BUSINESS = 'LIFEOS/USER/WORK/YOUR_COMPANIES'


def classification(relative):
    from .memory_atlas import SNAPSHOT, CACHE, DATABASE
    from .memory_operational_views import SOURCES as OPERATIONAL_SOURCES
    from .memory_manual_state import QUEUE
    from .memory_personal_modules import SOURCES as PERSONAL_SOURCES
    from .memory_performance import SOURCES as PERFORMANCE_SOURCES
    if relative in {QUEUE, 'settings.json', SNAPSHOT, CACHE, DATABASE}: return 'life_text'
    if relative in OPERATIONAL_SOURCES: return 'life_text'
    if relative in PERSONAL_SOURCES['ledger']: return 'life_text'
    if relative in PERSONAL_SOURCES['doctor'] or re.fullmatch(r'hooks/[^/]+\.hook\.(?:ts|sh)', relative): return 'life_text'
    if relative in PERFORMANCE_SOURCES: return 'life_text'
    if re.fullmatch(r'LIFEOS/USER/CONDUIT/(?:config\.json|(?:events|daily|insights)/[^/]+\.(?:json|jsonl))', relative): return 'life_text'
    if (relative in FINANCE_SOURCES or relative in TELOS
            or re.fullmatch(r'LIFEOS/USER/HEALTH/[^/]+\.md', relative) and Path(relative).name != 'README.md'
            or relative == BUSINESS + '/README.md'
            or re.fullmatch(re.escape(BUSINESS) + r'/[^./][^/]*/(?:README\.md|REVENUE/[^/]+\.md)', relative)):
        return 'life_text'
    if (re.fullmatch(r'LIFEOS/USER/HEALTH/lab_results[^/]*', relative)
            or re.fullmatch(re.escape(BUSINESS) + r'/[^./][^/]*', relative)):
        return 'life_metadata'
    return None


def snapshot(memory, scope, relative):
    kind = classification(relative)
    if kind is None:
        raise MemoryUnavailable('Source review requires a declared Life source')
    from .memory_atlas import SNAPSHOT, DATABASE, source_path
    path = source_path(memory, relative) if relative in {SNAPSHOT, DATABASE} else _checked(memory, memory.root / relative)
    if not path.exists() or kind == 'life_text' and not path.is_file():
        raise MemoryUnavailable('Life source review requires existing physical owner sources')
    before = path.stat()
    keys = lambda info: (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns)
    if kind == 'life_metadata':
        content = json.dumps({'size': before.st_size, 'modified_ns': before.st_mtime_ns,
            'directory': path.is_dir()}, sort_keys=True)
    elif relative == DATABASE:
        graph = memory._native('atlas_graph_state')
        if not isinstance(graph, dict) or not isinstance(graph.get('graph'), dict):
            raise MemoryUnavailable('The reviewed Atlas graph requires its declared native tables')
        content = json.dumps(graph['graph'], ensure_ascii=False)
        if len(content.encode()) > SOURCE_LIMIT:
            raise MemoryUnavailable('The reviewed Atlas graph exceeds its byte limit')
    else:
        if before.st_size > SOURCE_LIMIT:
            raise MemoryUnavailable('A reviewed Life source exceeds its byte limit')
        with path.open('r', encoding='utf-8', newline='') as stream: content = stream.read()
    after = path.stat()
    source_path(memory, relative) if relative in {SNAPSHOT, DATABASE} else _checked(memory, path)
    if keys(before) != keys(after):
        raise MemoryUnavailable('A Life source changes during review')
    return ({'path': str(path), 'relative': relative, 'content': content,
             'lastModified': _source_time(after, milliseconds=True)}, _source_time(after))


def projection(memory, relative, content):
    from .memory_atlas import SNAPSHOT, DATABASE, CACHE
    from .memory_operational_views import SOURCES as OPERATIONAL_SOURCES, projection as operational_projection
    from .memory_personal_modules import SOURCES as PERSONAL_SOURCES
    from .memory_performance import SOURCES as PERFORMANCE_SOURCES
    if (relative.startswith('LIFEOS/USER/CONDUIT/') or relative in OPERATIONAL_SOURCES or relative in PERFORMANCE_SOURCES or relative in PERSONAL_SOURCES['doctor']
            or relative in {SNAPSHOT, DATABASE, CACHE}
            or relative in PERSONAL_SOURCES['ledger'] and relative.endswith(('.json', '.jsonl'))):
        values = [operational_projection(line) for line in content.split('\n') if line] if relative.endswith('.jsonl') else [operational_projection(content)]
        result = '\n'.join(values) if all(value is not None for value in values) else None
        return result if result is not None and len(result.encode()) <= CORPUS_LIMIT else None
    if classification(relative) == 'life_metadata': return content
    if relative.endswith(('.yaml', '.toml')):
        values = memory._native('finance_source_projections', sources=[{'relative': relative, 'content': content}])['projections']
        if (not isinstance(values, list) or len(values) != 1
                or values[0] is not None and not isinstance(values[0], str)):
            raise MemoryUnavailable('Native Life projection changes its declared response')
        decoded = values[0]
    elif relative.endswith('.jsonl'):
        lines = [line for line in content.split('\n') if line]
        if len(lines) > SOURCE_COUNT_LIMIT:
            raise MemoryUnavailable('A reviewed Life log exceeds its record count limit')
        values = [json_projection(line) for line in lines]
        decoded = '\n'.join(values) if all(value is not None for value in values) else None
    elif relative.endswith('.json'):
        decoded = json_projection(content)
    else:
        return content
    if decoded is None: return None
    result = content + '\n' + decoded
    if len(result.encode()) > CORPUS_LIMIT:
        raise MemoryUnavailable('A reviewed Life source exceeds its projection limit')
    return result
