# ABOUTME: Reads native PULSE snapshots under current owner source authority.
# ABOUTME: Confines diagnostic paths and filters retained text before owner delivery.
from datetime import datetime, timezone
import json
import math
from pathlib import Path

from .memory_access import HOT_FILES, MemoryUnavailable
from .memory_diagnostics import filter_report
from .memory_sources import authorize


VIEWS = {'snapshot', 'state', 'health', 'runs'}
OBSERVABILITY = 'LIFEOS/MEMORY/OBSERVABILITY/'
CADENCE_FIELDS = ('turn_threshold', 'min_minutes_between', 'idle_threshold', 'confidence_threshold')


def _attest(memory, relative: str, *, directory: bool = False) -> Path:
    source = memory._path(relative)
    base = 'LIFEOS/USER' if relative.startswith('LIFEOS/USER/') else 'LIFEOS'
    physical = memory.root.parent / '.config/LIFEOS/USER' / Path(relative).relative_to(base)
    if source.resolve() != physical.absolute() or (source.exists() and not (
            source.is_dir() if directory else source.is_file())):
        raise MemoryUnavailable('PULSE diagnostics need their permitted physical sources')
    return source


def _attest_runs(memory) -> None:
    runs = _attest(memory, OBSERVABILITY + 'reviewer-runs', directory=True)
    if not runs.exists():
        return
    for child in runs.iterdir():
        relative = child.relative_to(memory.root).as_posix()
        if child.is_symlink():
            raise MemoryUnavailable('PULSE run directories must not redirect their sources')
        if child.is_dir():
            _attest(memory, relative, directory=True)
            _attest(memory, relative + '/dispatch.log')


def snapshot(memory, scope, view: str):
    authorize(scope)
    if not isinstance(view, str) or view not in VIEWS:
        raise ValueError('Choose a supported native PULSE snapshot view')
    with memory._transaction() as connection:
        names = (['review-state.json', 'memory-health.jsonl', 'reviewer-fires.jsonl', 'pending-proposals.jsonl']
                 if view == 'snapshot' else ['review-state.json'] if view == 'state'
                 else ['memory-health.jsonl'] if view == 'health' else [])
        for name in names:
            _attest(memory, OBSERVABILITY + name)
        if view in ('snapshot', 'runs'):
            _attest_runs(memory)
        hot = {}
        if view == 'snapshot':
            _attest(memory, 'LIFEOS/USER/CONFIG/memory-review.json')
            for category, relative in HOT_FILES.items():
                path = _attest(memory, relative)
                if path.exists():
                    entries = memory._hot_snapshot(connection, category)['entries']
                elif connection.execute("SELECT 1 FROM records WHERE category=? AND status='active'",
                                        (category,)).fetchone():
                    raise MemoryUnavailable('PULSE hot memory is missing recorded current facts')
                else:
                    entries = []
                name = 'principalMemory' if category == 'principal' else 'daMemory'
                hot[name] = {'entries': entries, 'count': len(entries),
                             'charsUsed': sum(len(entry.encode('utf-16-le')) // 2 for entry in entries)}
        native = memory._native('pulse_snapshot', view=view)['snapshot']
        if view == 'snapshot':
            if not isinstance(native, dict) or not isinstance(native.get('cadenceConfig'), dict):
                raise MemoryUnavailable('The native PULSE snapshot is unavailable')
            cadence = native['cadenceConfig']
            native['cadenceConfig'] = {key: cadence[key] for key in CADENCE_FIELDS
                if type(cadence.get(key)) in (int, float) and 0 <= cadence[key] <= 2 ** 53 - 1
                and math.isfinite(cadence[key])}
            for name in hot:
                native.pop(name, None)
        filtered = filter_report(memory, scope, json.dumps(native), datetime.now(timezone.utc).isoformat(),
                                 view=view, connection=connection)
        projected = json.loads(filtered['content'])
        if hot:
            projected.update(hot)
        return projected
