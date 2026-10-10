# ABOUTME: Reconciles admitted Atlas collectors through native graph transactions.
# ABOUTME: Publishes the database and snapshot together with current owner checks and recovery.
import base64
import hashlib
import json
import re
from uuid import uuid4

from .memory_access import MemoryConflict, MemoryUnavailable, _now
from .memory_atlas import (DATABASE, SNAPSHOT, CACHE, _collect, _graph, source_path, admit_graph,
                          capacity_projection, PROJECTION_FIELD_LIMIT)
from .memory_atlas_insight import _request, _admit_output
from .memory_source_review import _retirement_digest
from .memory_sources import SOURCE_LIMIT, CORPUS_LIMIT
from .memory_transaction import publish


DATABASE_LIMIT = 2 * 1024 * 1024
PUBLICATIONS = frozenset({DATABASE, SNAPSHOT})


def publication_path(memory, relative):
    path = source_path(memory, relative)
    if relative == DATABASE:
        for suffix in ('-wal', '-shm', '-journal'):
            companion = path.with_name(path.name + suffix)
            if companion.exists() or companion.is_symlink():
                raise MemoryUnavailable('Atlas publication requires a closed database without companion files')
    return path


def publication_paths(memory, scope, payload):
    _request(scope)
    if payload != {'operation': 'atlas_sync'}:
        raise ValueError('Choose declared Atlas synchronization publication')
    for name in PUBLICATIONS:
        path = publication_path(memory, name)
        limit = DATABASE_LIMIT if name == DATABASE else SOURCE_LIMIT
        if path.exists() and (not path.is_file() or path.stat().st_size > limit):
            raise MemoryUnavailable('Atlas synchronization requires bounded fixed destinations')
    return sorted(PUBLICATIONS)


def _database(memory):
    path = publication_path(memory, DATABASE)
    if not path.exists():
        return None
    before = path.stat()
    if not path.is_file() or before.st_size > DATABASE_LIMIT:
        raise MemoryUnavailable('Atlas synchronization requires a bounded database')
    with path.open('rb') as stream:
        content = stream.read(DATABASE_LIMIT + 1)
    publication_path(memory, DATABASE)
    after = path.stat()
    keys = lambda info: (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns)
    if len(content) > DATABASE_LIMIT or keys(before) != keys(after):
        raise MemoryUnavailable('Atlas database changes during synchronization preparation')
    return content


def _snapshot(memory, scope, connection, check_current):
    _request(scope)
    check_current()
    database = _database(memory)
    sources = _collect(memory, scope, connection, insights=True)
    graph = _graph(memory, scope, connection)
    if _database(memory) != database or _collect(memory, scope, connection, insights=True) != sources:
        raise MemoryConflict('Atlas inputs change during synchronization preparation')
    check_current()
    return {'database': database, 'sources': sources, 'graph': graph,
        'retirement': _retirement_digest(connection), 'scope': scope.signature,
        'root': str(memory.physical_root)}


def run(memory, scope, collectors, scope_name, *, check_current):
    if (not isinstance(collectors, list) or not 1 <= len(collectors) <= 2
            or any(not isinstance(name, str) or name not in {'gear', 'projects'} for name in collectors)
            or len(set(collectors)) != len(collectors)
            or not isinstance(scope_name, str) or re.fullmatch(r'[A-Za-z0-9:_./-]{1,128}', scope_name) is None):
        raise ValueError('Choose distinct declared Atlas collectors and a bounded native scope')
    _request(scope)
    with memory._transaction() as connection:
        before = _snapshot(memory, scope, connection, check_current)
        rows = {row[0]: row[2] if len(row) == 3 else None for row in before['sources'][2]}
        runs = [{'collector': name, 'scope': scope_name, 'result': memory._native('atlas_collect',
            collector=name, content=rows['LIFEOS/USER/' + ('GEAR.md' if name == 'gear' else 'PROJECTS.md')])}
            for name in collectors]
        plan = memory._native('atlas_sync_plan',
            database=base64.b64encode(before['database']).decode() if before['database'] is not None else None,
            runs=runs)
        if (set(plan) != {'database', 'snapshot', 'graph', 'runs'} or not isinstance(plan['database'], str)
                or not isinstance(plan['snapshot'], dict) or not isinstance(plan['runs'], list)
                or len(json.dumps(plan).encode()) > 2 * CORPUS_LIMIT):
            raise MemoryUnavailable('Native Atlas synchronization changes its bounded publication plan')
        try:
            database = base64.b64decode(plan['database'], validate=True)
        except ValueError as error:
            raise MemoryUnavailable('Native Atlas synchronization requires complete database bytes') from error
        snapshot = json.dumps(plan['snapshot'], ensure_ascii=False).encode()
        for label, count, limit in (('database bytes', len(database), DATABASE_LIMIT),
                                   ('snapshot bytes', len(snapshot), SOURCE_LIMIT)):
            if count > limit:
                raise MemoryUnavailable(f'Atlas capacity: {label} {count} exceed {limit}')
        if (not database.startswith(b'SQLite format 3\x00') or len(plan['runs']) != len(collectors)
                or any(not isinstance(row, dict) or set(row) != {'collector', 'runId', 'swept'}
                    or row['collector'] != name or type(row['runId']) is not int or row['runId'] < 1
                    or type(row['swept']) is not bool for row, name in zip(plan['runs'], collectors))):
            raise MemoryUnavailable('Native Atlas synchronization requires declared database, snapshot, and run fields')
        _admit_output(memory, scope, connection, plan['snapshot'])
        capacity = admit_graph(memory, scope, connection, plan['graph'], _now())
        projected, fields = capacity_projection(snapshot.decode(), 'snapshot')
        capacity.update(database_bytes={'used': len(database), 'limit': DATABASE_LIMIT},
            snapshot_bytes={'used': len(snapshot), 'limit': SOURCE_LIMIT},
            snapshot_fields={'used': fields, 'limit': PROJECTION_FIELD_LIMIT},
            snapshot_projection_bytes={'used': len(projected.encode()), 'limit': CORPUS_LIMIT})
        dimensions = {name: value for name, value in capacity.items() if name != 'tables'}
        dimensions.update({'tables.'+name: value for name, value in capacity['tables'].items()})
        capacity['warnings'] = sorted(name for name, value in dimensions.items()
                                      if value['used'] * 5 >= value['limit'] * 4)
        if _snapshot(memory, scope, connection, check_current) != before:
            raise MemoryConflict('Atlas inputs change during native synchronization planning')
    contents = {DATABASE: database, SNAPSHOT: snapshot}
    after = before

    def apply(connection):
        nonlocal after
        if _snapshot(memory, scope, connection, check_current) != before:
            raise MemoryConflict('Atlas synchronization preserves later source and destination changes')
        check_current()
        for name, content in contents.items():
            publish(memory._publication_path(name), content)
        try:
            after = _snapshot(memory, scope, connection, check_current)
        except MemoryConflict as error:
            raise MemoryUnavailable('Atlas synchronization recheck requires publication recovery') from error
        unchanged = lambda record: [row for row in record['sources'][2] if row[0] != SNAPSHOT]
        if (unchanged(after) != unchanged(before)
                or any(after[key] != before[key] for key in ('scope', 'root', 'retirement'))
                or any(memory._publication_path(name).read_bytes() != content for name, content in contents.items())):
            raise MemoryUnavailable('Atlas synchronization changes during publication and requires recovery')
        check_current()
        return {'status': 'committed'}

    receipt = memory._operation(scope, 'atlas-sync-' + uuid4().hex, {'operation': 'atlas_sync'}, apply,
        publication_digests={name: hashlib.sha256(content).hexdigest() for name, content in contents.items()})
    if receipt['status'] != 'committed':
        raise MemoryUnavailable('Atlas synchronization needs recovery or a current retry')
    with memory._transaction() as connection:
        if _snapshot(memory, scope, connection, check_current) != after:
            raise MemoryConflict('Atlas synchronization preserves later changes before delivery')
        check_current()
    return {'ok': True, 'runs': plan['runs'], 'capacity': capacity}
