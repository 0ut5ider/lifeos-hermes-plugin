# ABOUTME: Projects native diagnostic files into authorized operational fields.
# ABOUTME: Filters retained proposal samples without removing historical activity counts.

from datetime import datetime, timezone
import json
import math
from typing import Any

from .memory_policy import MemoryScope
from .memory_sources import _source_path, _strings


DIAGNOSTIC_FILES = {'LIFEOS/MEMORY/OBSERVABILITY/' + name for name in (
    'reviewer-runs.jsonl', 'memory-retrievals.jsonl', 'pending-proposals.jsonl',
    'memory-writes.jsonl', 'memory-health.jsonl', 'format-gate.jsonl', 'review-state.json')}
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
