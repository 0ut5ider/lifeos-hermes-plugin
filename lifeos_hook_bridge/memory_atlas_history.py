# ABOUTME: Retains Atlas observation provenance while archiving exact prior graph bytes.
# ABOUTME: Bounds live history and supplies current-owner reads of verified archive rows.
from contextlib import closing
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3

from .memory_access import MemoryUnavailable, _now
from .memory_atlas import DATABASE, SNAPSHOT
from .memory_atlas_insight import _request, _admit_output


RUN_TRIGGER = 64
RUN_RETAIN = 32
EVENT_TRIGGER = 128
EVENT_RETAIN = 64
WINDOWS = ((RUN_RETAIN, EVENT_RETAIN), (16, 50), (0, 0))
ARCHIVE_FILES = frozenset({'atlas.db', 'snapshot.json', 'manifest.json'})
ARCHIVE_PATTERN = r'atlas/history/([0-9a-f]{64})/(atlas\.db|snapshot\.json|manifest\.json)'


def archive_paths(identifier):
    if not isinstance(identifier, str) or re.fullmatch('[0-9a-f]{64}', identifier) is None:
        raise ValueError('Atlas history requires one exact archive identifier')
    return ['atlas/history/' + identifier + '/' + name for name in sorted(ARCHIVE_FILES)]


def publication_path(memory, relative):
    if re.fullmatch(ARCHIVE_PATTERN, relative) is None:
        raise MemoryUnavailable('Atlas archives require fixed digest destinations')
    base = memory.root.parent / '.local/state/lifeos/atlas'
    path = base / Path(relative).relative_to('atlas')
    for selected in (base/'history', path.parent, path):
        if selected.is_symlink() or selected.resolve() != selected:
            raise MemoryUnavailable('Atlas archive destinations require private physical owner files')
        if selected.exists():
            info = selected.stat()
            regular = selected.is_file() and info.st_nlink == 1 if selected == path else selected.is_dir()
            if not regular or info.st_uid != os.getuid() or info.st_mode & 0o077:
                raise MemoryUnavailable('Atlas archive destinations require private physical owner files')
    return path


def _history(snapshot):
    empty = {'version': 1, 'archived_collectors': {}, 'archived_events': 0}
    if snapshot is None:
        return empty
    decoded = json.loads(snapshot)
    if not isinstance(decoded, dict):
        raise MemoryUnavailable('Atlas history requires its native snapshot object')
    value = decoded.get('history', empty)
    if (not isinstance(value, dict) or set(value) != set(empty) or type(value['version']) is not int or value['version'] != 1
            or type(value['archived_events']) is not int or value['archived_events'] < 0
            or not isinstance(value['archived_collectors'], dict)
            or any(not isinstance(name, str) or not isinstance(row, dict) or set(row) != {'runs', 'successes'}
                or any(type(count) is not int or count < 0 for count in row.values())
                or row['successes'] > row['runs'] for name, row in value['archived_collectors'].items())):
        raise MemoryUnavailable('Atlas history requires valid cumulative archive counts')
    return value


def prepare(database, snapshot, *, force=False, run_retain=RUN_RETAIN, event_retain=EVENT_RETAIN):
    history = _history(snapshot)
    removed = {'sync_run': 0, 'lifecycle_event': 0}
    if database is None:
        return database, history, removed
    with closing(sqlite3.connect(':memory:')) as connection:
        connection.deserialize(database)
        connection.execute('PRAGMA trusted_schema=OFF')
        runs = connection.execute('SELECT COUNT(*) FROM sync_run').fetchone()[0]
        events = connection.execute('SELECT COUNT(*) FROM lifecycle_event').fetchone()[0]
        if runs > RUN_TRIGGER or force:
            # Keep the maximum run identifier, every referenced run, and each collector's latest run.
            connection.execute('CREATE TEMP TABLE retained_run (id INTEGER PRIMARY KEY)')
            connection.execute('INSERT OR IGNORE INTO retained_run SELECT id FROM sync_run ORDER BY id DESC LIMIT ?', (run_retain,))
            connection.execute('INSERT OR IGNORE INTO retained_run SELECT MAX(id) FROM sync_run GROUP BY collector')
            connection.execute('INSERT OR IGNORE INTO retained_run SELECT (SELECT id FROM sync_run AS run '
                'WHERE run.collector=collector.collector ORDER BY finished_at DESC,id DESC LIMIT 1) '
                'FROM (SELECT DISTINCT collector FROM sync_run) AS collector')
            for table in ('source_observation', 'edge_observation'):
                connection.execute('INSERT OR IGNORE INTO retained_run SELECT last_run_id FROM ' + table)
            counts = connection.execute("SELECT collector,COUNT(*),SUM(status='success') FROM sync_run "
                'WHERE id NOT IN (SELECT id FROM retained_run) GROUP BY collector').fetchall()
            for name, count, successes in counts:
                previous = history['archived_collectors'].setdefault(name, {'runs': 0, 'successes': 0})
                previous['runs'] += count
                previous['successes'] += successes
            removed['sync_run'] = connection.execute('DELETE FROM sync_run WHERE id NOT IN (SELECT id FROM retained_run)').rowcount
        if events > EVENT_TRIGGER or force:
            removed['lifecycle_event'] = connection.execute('DELETE FROM lifecycle_event WHERE id NOT IN '
                '(SELECT id FROM lifecycle_event ORDER BY id DESC LIMIT ?)', (event_retain,)).rowcount
            history['archived_events'] += removed['lifecycle_event']
        if not any(removed.values()):
            return database, history, removed
        connection.commit()
        connection.execute('VACUUM')
        return connection.serialize(), history, removed


def complete_snapshot(snapshot, history):
    # The public collector totals count archived and retained runs, rather than resetting at retention.
    for row in snapshot['status']['collectors']:
        previous = history['archived_collectors'].get(row['collector'], {'runs': 0, 'successes': 0})
        row['runs'] += previous['runs']
        row['successes'] += previous['successes']
    snapshot['history'] = history


def archive_contents(before, database, snapshot, removed):
    prior_snapshot = next((row[2].encode() for row in before['sources'][2] if row[0] == SNAPSHOT and len(row) == 3), None)
    if prior_snapshot is None:
        raise MemoryUnavailable('Atlas retention requires the previous admitted snapshot')
    digest = lambda content: hashlib.sha256(content).hexdigest()
    old = {'database': digest(before['database']), 'snapshot': digest(prior_snapshot)}
    manifest = {'version': 1, 'created_at': _now(), 'before': old,
        'after': {'database': digest(database), 'snapshot': digest(snapshot)}, 'removed': removed,
        'scope': before['scope'], 'retirement': before['retirement'],
        'sources': {row[0]: digest(row[2].encode()) if len(row) == 3 else None
            for row in before['sources'][2] if row[0] != SNAPSHOT}}
    identifier = digest(json.dumps(manifest, sort_keys=True, allow_nan=False).encode())
    manifest['archive_id'] = identifier
    contents = {'atlas/history/'+identifier+'/atlas.db': before['database'],
        'atlas/history/'+identifier+'/snapshot.json': prior_snapshot,
        'atlas/history/'+identifier+'/manifest.json': json.dumps(manifest, sort_keys=True).encode()}
    return identifier, contents


def _read_file(memory, relative):
    path = publication_path(memory, relative)
    limit = 2*1024*1024 if path.name == 'atlas.db' else 256*1024
    if not path.is_file() or path.stat().st_size > limit:
        raise MemoryUnavailable('Atlas history requires complete bounded archive files')
    before = path.stat()
    with path.open('rb') as stream:
        content = stream.read(limit + 1)
    publication_path(memory, relative)
    after = path.stat()
    keys = lambda info: (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns)
    if len(content) > limit or keys(before) != keys(after):
        raise MemoryUnavailable('Atlas history changes during its bounded byte read')
    return content


def read(memory, scope, identifier, table, offset, *, check_current):
    _request(scope)
    archive_paths(identifier)
    if not isinstance(table, str) or table not in {'sync_run', 'lifecycle_event'} or type(offset) is not int or not 0 <= offset <= 2048:
        raise ValueError('Atlas history requires a declared table and bounded row offset')
    with memory._transaction() as connection:
        check_current()
        contents = {}
        for relative in archive_paths(identifier):
            contents[Path(relative).name] = _read_file(memory, relative)
        manifest = json.loads(contents['manifest.json'])
        digest = lambda content: hashlib.sha256(content).hexdigest()
        unsigned = {key: value for key, value in manifest.items() if key != 'archive_id'} if isinstance(manifest, dict) else {}
        if (not isinstance(manifest, dict) or manifest.get('version') != 1 or manifest.get('archive_id') != identifier
                or manifest.get('before') != {'database': digest(contents['atlas.db']), 'snapshot': digest(contents['snapshot.json'])}
                or digest(json.dumps(unsigned, sort_keys=True, allow_nan=False).encode()) != identifier
                or json.dumps(manifest, sort_keys=True, allow_nan=False).encode() != contents['manifest.json']):
            raise MemoryUnavailable('Atlas history preserves changed archive files')
        with closing(sqlite3.connect(':memory:')) as archive:
            archive.deserialize(contents['atlas.db'])
            archive.row_factory = sqlite3.Row
            rows = [dict(row) for row in archive.execute('SELECT * FROM '+table+' ORDER BY id LIMIT 100 OFFSET ?', (offset,))]
            total = archive.execute('SELECT COUNT(*) FROM '+table).fetchone()[0]
        _admit_output(memory, scope, connection, rows)
        check_current()
        for relative in archive_paths(identifier):
            if _read_file(memory, relative) != contents[Path(relative).name]:
                raise MemoryUnavailable('Atlas history changes during current owner admission')
        return {'ok': True, 'archive_id': identifier, 'table': table, 'rows': rows, 'total': total,
            'next_offset': offset + len(rows) if offset + len(rows) < total else None}


def read_owner(configuration, route, identifier, table, offset):
    from uuid import uuid4
    from .memory_runtime import MemoryRuntime, MemoryAdmissionError
    from .memory_service import MemoryService
    runtime = MemoryRuntime(configuration)
    runtime.clear()
    try:
        if not runtime.enabled():
            raise MemoryAdmissionError('Atlas history requires activated memory ownership')
        runtime.admit({'HERMES_SESSION_PLATFORM': 'cli', 'HERMES_SESSION_ID': 'atlas-history-'+uuid4().hex},
            **route, is_first_turn=True)
        return MemoryService(runtime.configuration).native(runtime.context(), 'atlas_history',
            {'archive_id': identifier, 'table': table, 'offset': offset})
    finally:
        runtime.clear()
