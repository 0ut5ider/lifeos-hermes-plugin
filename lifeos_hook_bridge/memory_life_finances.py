# ABOUTME: Admits fixed finance text, structured records, and configuration within the selected owner root.
# ABOUTME: Supplies native finance rendering and checks current source snapshots and authority before delivery.
from datetime import datetime, timezone
import json

from .memory_access import MemoryUnavailable
from .memory_sources import authorize, _admit, _source_time, SOURCE_LIMIT, CORPUS_LIMIT, SOURCE_COUNT_LIMIT, json_projection
from .memory_tab_freshness import _checked

FINANCE_FILES = tuple('LIFEOS/USER/FINANCES/' + filename for filename in (
    'state.json', 'INCOME.md', 'EXPENSES.md', 'ACCOUNTS.md', 'INVESTMENTS.md', 'TAXES.md',
    'PLAN.md', 'vendors.yaml', 'obligations.yaml', 'GOALS.md', 'FINANCES.md'))
SOURCES = (*FINANCE_FILES, 'LIFEOS/MEMORY/OBSERVABILITY/vendor-costs.jsonl',
    'LIFEOS/MEMORY/OBSERVABILITY/statement-spend.jsonl', 'LIFEOS/USER/CONFIG/LIFEOS_CONFIG.toml')


def _snapshot(memory):
    sources, fingerprints = [], []
    total = 0
    for relative in SOURCES:
        path = _checked(memory, memory.root / relative)
        if not path.exists():
            fingerprints.append((relative, None))
            continue
        if not path.is_file():
            raise MemoryUnavailable('Finance sources require fixed regular owner files')
        before = path.stat()
        if before.st_size > SOURCE_LIMIT:
            raise MemoryUnavailable('A finance source exceeds its byte limit')
        with path.open('r', encoding='utf-8', newline='') as stream:
            content = stream.read()
        total += len(content.encode())
        if total > CORPUS_LIMIT:
            raise MemoryUnavailable('Finance sources exceed their transport limit')
        after = path.stat()
        keys = lambda info: (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns)
        if keys(before) != keys(after):
            raise MemoryUnavailable('A finance source changes during collection')
        _checked(memory, path)
        fingerprints.append((relative, keys(after), content))
        sources.append({'relative': relative, 'content': content, 'timestamp': _source_time(after)})
    return sources, fingerprints


def _admitted(memory, scope, connection, sources):
    structured = [source for source in sources if source['relative'].endswith(('.yaml', '.toml'))]
    projections = memory._native('finance_source_projections', sources=[
        {'relative': source['relative'], 'content': source['content']} for source in structured])['projections'] if structured else []
    if (not isinstance(projections, list) or len(projections) != len(structured)
            or any(value is not None and not isinstance(value, str) for value in projections)
            or len(json.dumps(projections).encode()) > CORPUS_LIMIT):
        raise MemoryUnavailable('Native finance projections change their declared format')
    by_path = {source['relative']: projection for source, projection in zip(structured, projections, strict=True)}
    candidates = []
    groups = []
    for source in sources:
        relative, content = source['relative'], source['content']
        if relative.endswith('.jsonl'):
            items = [line for line in content.split('\n') if line]
            if len(candidates) + len(items) > SOURCE_COUNT_LIMIT:
                raise MemoryUnavailable('Finance admission exceeds its record count limit')
            group = []
            for line in items:
                group.append(len(candidates))
                projection = json_projection(line)
                candidates.append((source, line, line + '\n' + projection if projection is not None else None))
            groups.append((relative, group, True))
        else:
            projection = (by_path[relative] if relative in by_path else
                          json_projection(content) if relative.endswith('.json') else content)
            if projection is not None and relative.endswith(('.yaml', '.toml', '.json')):
                projection = content + '\n' + projection
            groups.append((relative, [len(candidates)], False))
            candidates.append((source, content, projection))
    if len(candidates) > SOURCE_COUNT_LIMIT or sum(len(projection.encode()) for _, _, projection in candidates
            if projection is not None) > CORPUS_LIMIT:
        raise MemoryUnavailable('Finance admission exceeds its record transport limit')
    contents = [(projection or '') + '\n' + source['relative'] for source, _, projection in candidates]
    checked = memory._native('validate_source_batch', contents=contents)['accepted'] if contents else []
    admitted = []
    for (source, content, projection), accepted in zip(candidates, checked, strict=True):
        excluded = projection is None or accepted is not True or _admit(memory, connection, scope,
            content, source['relative'], source['timestamp'], projection=projection)['excluded']
        admitted.append(None if excluded else content)
    result = []
    for relative, indices, jsonl in groups:
        if jsonl:
            # Nonempty null rows preserve the native first-line header rule when a record is excluded.
            content = '\n'.join(admitted[index] if admitted[index] is not None else 'null' for index in indices)
        else:
            content = admitted[indices[0]]
            if content is None: continue
        result.append({'relative': relative, 'content': content})
    if len(json.dumps(result).encode()) > CORPUS_LIMIT:
        raise MemoryUnavailable('Admitted finance sources exceed their transport limit')
    return result


def view(memory, scope, *, check_current=None):
    authorize(scope)
    if not scope.principal:
        raise MemoryUnavailable('Finance views require a bound owner')
    if check_current is not None: check_current()
    with memory._transaction() as connection:
        sources, fingerprints = _snapshot(memory)
        result = memory._native('life_finance_view', sources=_admitted(memory, scope, connection, sources))
        if check_current is not None: check_current()
        if _snapshot(memory) != (sources, fingerprints):
            raise MemoryUnavailable('Finance sources change during native rendering')
        if (not isinstance(result, dict) or set(result) != {'status', 'body'}
                or type(result['status']) is not int or result['status'] != 200
                or not isinstance(result['body'], dict) or len(json.dumps(result).encode()) > CORPUS_LIMIT):
            raise MemoryUnavailable('The native finance view changes its declared response')
        if memory._filter_history(connection, scope, json.dumps(result), datetime.now(timezone.utc).isoformat())['excluded']:
            raise MemoryUnavailable('The native finance view contains excluded source text')
        if check_current is not None: check_current()
        return result
