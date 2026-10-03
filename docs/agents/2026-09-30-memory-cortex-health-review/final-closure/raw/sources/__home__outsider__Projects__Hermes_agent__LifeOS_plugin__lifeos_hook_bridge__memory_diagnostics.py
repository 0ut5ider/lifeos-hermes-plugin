# ABOUTME: Projects native diagnostic files into authorized operational fields.
# ABOUTME: Filters retained proposal samples without removing historical activity counts.

from datetime import datetime, timezone
import json
import math
import re
from typing import Any

from .memory_policy import MemoryScope
from .memory_access import HOT_FILES, MemoryUnavailable
from .memory_history import project_value
from .memory_sources import _source_path, _strings, authorize


DIAGNOSTIC_FILES = {'LIFEOS/MEMORY/OBSERVABILITY/' + name for name in (
    'reviewer-runs.jsonl', 'memory-retrievals.jsonl', 'pending-proposals.jsonl',
    'memory-writes.jsonl', 'memory-health.jsonl', 'format-gate.jsonl', 'review-state.json')}
DIAGNOSTIC_DIRECTORIES = {'LIFEOS/MEMORY/OBSERVABILITY/reviewer-runs', 'LIFEOS/MEMORY/INDEX'}
PROPOSAL_STATUSES = {'pending', 'sent', 'auto-applied', 'accepted', 'rejected', 'edited', 'applied-elsewhere'}
PROPOSAL_KINDS = {'identity', 'style', 'resume', 'definition', 'canonical-content',
                  'operational-rule', 'projects', 'contacts'}
NUMBER_FIELDS = {
    'reviewer-runs.jsonl': ('duration_ms', 'items_total', 'memory_writes', 'knowledge_appends',
                            'proposals_enqueued', 'inference_duration_ms', 'exchanges'),
    'memory-retrievals.jsonl': ('returned_count', 'duration_ms', 'top_score'),
    'memory-writes.jsonl': ('new_count', 'prior_count'),
    'review-state.json': ('turn_count_since_last_review',),
}
BOOLEAN_FIELDS = {
    'reviewer-runs.jsonl': ('ok', 'parse_ok', 'skipped'),
    'format-gate.jsonl': ('heartbeat_present',),
    'review-state.json': ('pending_review',),
}
CLOCK_FIELDS = {'ts', 'timestamp', 'created_at', 'last_review_at', 'last_message_at'}


def _finding_detail(path: tuple[str | int, ...]) -> bool:
    return len(path) == 3 and path[0] == 'findings' and isinstance(path[1], int) and path[2] == 'detail'


def _evidence_field(path: tuple[str | int, ...]) -> bool:
    return path in (('reviewer',), ('retrieval',), ('index',),
                    ('evidence', 'reviewer'), ('evidence', 'retrieval'), ('evidence', 'index')) or _finding_detail(path)


def _clock(path: tuple[str | int, ...], value: str) -> bool:
    # Valid structural clocks are operational evidence, like counts and severity.
    return (bool(path) and path[-1] in CLOCK_FIELDS
        and (len(path) == 1 or _evidence_field(path[:-1])) and re.fullmatch(
        r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,9})?(?:Z|[+-]\d{2}:\d{2})', value) is not None
        and _timestamp(value))


def _timestamp(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    try:
        return datetime.fromisoformat(value.replace('Z', '+00:00')).tzinfo is not None
    except ValueError:
        return False


def _numbers(row: dict[str, Any], keys: tuple[str, ...]) -> dict[str, int | float]:
    return {key: row[key] for key in keys if type(row.get(key)) in (int, float)
            and 0 <= row[key] <= 2 ** 53 - 1 and math.isfinite(row[key])}


def _project(row: dict[str, Any], name: str) -> dict[str, Any]:
    result: dict[str, Any] = _numbers(row, NUMBER_FIELDS.get(name, ()))
    result.update({key: row[key] for key in BOOLEAN_FIELDS.get(name, ()) if type(row.get(key)) is bool})
    for key in ('ts', 'created_at', 'timestamp', 'last_review_at', 'last_message_at'):
        if _timestamp(row.get(key)):
            result[key] = row[key]
    if name == 'pending-proposals.jsonl':
        status, kind = row.get('status', 'pending'), row.get('target_kind', 'identity')
        result['status'] = status if isinstance(status, str) and status in PROPOSAL_STATUSES else 'unknown'
        result['target_kind'] = kind if isinstance(kind, str) and kind in PROPOSAL_KINDS else 'unknown'
    elif name == 'memory-writes.jsonl':
        path = row.get('file')
        if isinstance(path, str):
            if path.split('/')[-1] == 'PRINCIPAL_MEMORY.md':
                result['file'] = 'PRINCIPAL_MEMORY.md'
            elif path.split('/')[-1] == 'DA_MEMORY.md':
                result['file'] = 'DA_MEMORY.md'
    elif name == 'reviewer-runs.jsonl':
        dispatch = row.get('dispatch_summary')
        types = dispatch.get('by_type') if isinstance(dispatch, dict) else None
        if isinstance(types, dict):
            result['dispatch_summary'] = {'by_type': _numbers(types, ('memory', 'idea', 'knowledge', 'proposal'))}
    elif name == 'memory-health.jsonl':
        if isinstance(row.get('overall'), str) and row['overall'] in ('ok', 'warn', 'critical'):
            result['overall'] = row['overall']
        if isinstance(row.get('counts'), dict):
            result['counts'] = _numbers(row['counts'], ('ok', 'warn', 'critical'))
    return result


def read(memory, scope: MemoryScope, path: str) -> dict[str, Any]:
    with memory._transaction() as connection:
        source, relative = _source_path(memory, scope, path, diagnostic=True)
        content = source.read_text(encoding='utf-8')
        timestamp = datetime.fromtimestamp(source.stat().st_mtime, timezone.utc).isoformat()
        name = source.name
        projected = []
        samples = []
        for line in content.splitlines() if source.suffix == '.jsonl' else [content]:
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except ValueError:
                projected.append({})
                continue
            if not isinstance(row, dict):
                projected.append({})
                continue
            result = _project(row, name)
            projected.append(result)
            if name == 'pending-proposals.jsonl':
                result['details_available'] = False
                if all(isinstance(row.get(key), str) and row[key] for key in ('id', 'edit', 'target_file')):
                    text = line + '\n' + '\n'.join(_strings(row))
                    samples.append((row, result, text))
        if samples:
            items = []
            fields = []
            for row, _, _ in samples:
                start = len(items)
                for key in ('id', 'edit', 'target_file'):
                    if isinstance(row.get(key), str) and row[key]:
                        items.append({'type': 'idea', 'title': 'Native diagnostic sample', 'content': row[key]})
                fields.append((start, len(items)))
            checked = memory._native('validate_batch', items=items)['results']
            for (row, result, text), (start, end) in zip(samples, fields, strict=True):
                stamp = next((row[key] for key in ('ts', 'created_at', 'timestamp') if _timestamp(row.get(key))), timestamp)
                if (all(check.get('ok') and check.get('item') == item
                        for item, check in zip(items[start:end], checked[start:end], strict=True))
                        and not memory._filter_history(connection, scope, text, stamp)['excluded']):
                    result['details_available'] = True
                    for key in ('id', 'edit', 'target_file'):
                        if isinstance(row.get(key), str):
                            result[key] = (row[key].encode('utf-16-le', errors='surrogatepass')[:162].decode(
                                'utf-16-le', errors='surrogatepass') if key == 'edit' else row[key])
        rendered = '\n'.join(json.dumps(row) for row in projected)
        response = {'ok': True, 'content': rendered, 'excluded': False}
        if len((json.dumps(response) + '\n').encode()) > 3 * 1024 * 1024:
            raise ValueError('The diagnostic projection exceeds the native response limit')
        return response


def check(memory, scope: MemoryScope, path: str, *, report: bool = False) -> dict[str, Any]:
    with memory._transaction():
        _, relative = _source_path(memory, scope, path, diagnostic=True, require_file=False)
        if report and not re.fullmatch(
                r'LIFEOS/MEMORY/OBSERVABILITY/reports/[A-Za-z0-9][A-Za-z0-9_-]*\.json', relative):
            raise MemoryUnavailable('Diagnostic reports need their dedicated publication directory')
    return {'ok': True}


def diagnose_hot(memory, scope: MemoryScope, path: str) -> dict[str, Any]:
    authorize(scope)
    paths = {str(memory._path(relative)): relative for relative in HOT_FILES.values()}
    if not isinstance(path, str) or path not in paths:
        raise ValueError('Hot-memory diagnostics require an installed native memory file')
    relative = paths[path]
    with memory._transaction():
        source = memory._path(relative)
        physical = memory.root.parent / '.config/LIFEOS/USER' / source.relative_to(memory.root / 'LIFEOS/USER')
        if source.resolve() != physical.absolute() or (source.exists() and not source.is_file()):
            raise MemoryUnavailable('Hot-memory diagnostics need the permitted physical source')
        snapshot = memory._native('read_hot', path=str(source))
        if not isinstance(snapshot.get('dropped_invalid'), list):
            raise MemoryUnavailable('The native hot-memory diagnostic is unavailable')
        timestamp = (datetime.fromtimestamp(source.stat().st_mtime, timezone.utc).isoformat()
                     if source.exists() else datetime.now(timezone.utc).isoformat())
    filtered = filter_report(memory, scope, json.dumps({'dropped_invalid': snapshot['dropped_invalid']}), timestamp)
    return {'ok': True, **json.loads(filtered['content'])}


def filter_report(memory, scope: MemoryScope, content: str, timestamp: str) -> dict[str, Any]:
    authorize(scope)
    if not isinstance(content, str) or not _timestamp(timestamp):
        raise ValueError('A diagnostic report and explicit timestamp are required')
    try:
        report = json.loads(content)
    except RecursionError as error:
        raise ValueError('Diagnostic reports require bounded materialized content') from error
    strings, invalid = set(), set()
    def collect(text):
        strings.add(text)
        return False
    def inspect(value, depth=0):
        if depth > 32:
            raise ValueError('Diagnostic reports require bounded materialized content')
        if isinstance(value, str):
            collect(value)
            try:
                project_value(value, collect)
            except ValueError:
                invalid.add(value)
        elif isinstance(value, list):
            for item in value:
                inspect(item, depth + 1)
        elif isinstance(value, dict):
            if any(not key.isascii() or not key.replace('_', '').isalnum() for key in value):
                raise ValueError('Diagnostic fields need supported structural names')
            for item in value.values():
                inspect(item, depth + 1)
    inspect(report)
    items = [{'type': 'idea', 'title': 'Native diagnostic text', 'content': text} for text in sorted(strings) if text]
    with memory._transaction() as connection:
        checked = memory._native('validate_batch', items=items)['results']
        excluded = invalid | {item['content'] for item, check in zip(items, checked, strict=True)
                    if (not check.get('ok') or check.get('item') != item
                        or memory._filter_history(connection, scope, item['content'], timestamp)['excluded'])}
        def project(value, path=()):
            if isinstance(value, str):
                key = path[-1] if path else ''
                if _clock(path, value):
                    return value
                severity = (path == ('overall',) or
                    (len(path) == 3 and path[0] == 'findings' and isinstance(path[1], int) and key == 'severity'))
                if severity and value in ('ok', 'warn', 'critical'):
                    return value
                if key == 'status' and _evidence_field(path[:-1]) and value in ('ok', 'skipped', 'failed', 'parse-failed', 'timed-out',
                                                'missing', 'invalid', 'absent', 'no-index-v1', 'mismatch'):
                    return value
                reason = ((len(path) == 3 and path[0] == 'dropped_invalid' and isinstance(path[1], int)) or
                          (len(path) == 6 and _finding_detail(path[:3]) and path[3] == 'dropped' and isinstance(path[4], int)))
                if key == 'reason' and reason and value in ('malformed', 'overlength'):
                    return value
                if value in excluded:
                    return 'Memory diagnostic details are unavailable under the current policy.'
                try:
                    return project_value(value, lambda text: text in excluded)
                except ValueError:
                    return 'Memory diagnostic details are unavailable under the current policy.'
            if isinstance(value, list):
                return [project(item, (*path, index)) for index, item in enumerate(value)]
            if isinstance(value, dict):
                return {key: project(item, (*path, key)) for key, item in value.items()}
            return value
        response = {'ok': True, 'content': json.dumps(project(report))}
        if len((json.dumps(response) + '\n').encode()) > 3 * 1024 * 1024:
            raise ValueError('The diagnostic projection exceeds the native response limit')
        return response
