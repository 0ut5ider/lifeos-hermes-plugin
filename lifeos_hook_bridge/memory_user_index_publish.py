# ABOUTME: Journals native user index publication under current unrestricted owner authority.
# ABOUTME: Binds rendered indexes to source state and retirement history before replacing the fixed cache.
import hashlib
import json
import os

from .memory_access import MemoryUnavailable, MemoryConflict, _digest
from .memory_policy import CATEGORIES
from .memory_sources import authorize, CORPUS_LIMIT
from .memory_source_review import _retirement_digest
from .memory_transaction import publish
from .memory_user_index import _collect, view

OUTPUT = 'LIFEOS/PULSE/state/user-index.json'
PUBLICATIONS = frozenset({OUTPUT})


def _signature(memory, scope, connection):
    registry = memory._native('user_index_registry')
    skipped = registry.get('skip_directories')
    if (set(registry) != {'skip_directories'} or not isinstance(skipped, list)
            or len(skipped) > 64 or any(not isinstance(name, str) or not name or '/' in name for name in skipped)):
        raise MemoryUnavailable('Native user index discovery changes its declared registry')
    sources, fingerprints = _collect(memory, scope, connection, skipped)
    user = memory.root.parent / '.config/LIFEOS/USER'
    journal = memory.transaction.journal.resolve().relative_to(user)
    directory = 'LIFEOS/USER/' + journal.parent.as_posix()
    # The transaction journal does not enter the native Markdown index.
    fingerprints = [(row[0], tuple(name for name in row[1] if name != journal.name))
        if len(row) == 2 and row[0] == directory else row for row in fingerprints]
    return _digest(json.dumps({'root': str(memory.root), 'scope': scope.signature,
        'sources': sources, 'fingerprints': fingerprints, 'retirement': _retirement_digest(connection)}, sort_keys=True))


def _target(memory):
    target = memory._publication_path(OUTPUT)
    if target.exists() and (not target.is_file() or target.stat().st_uid != os.getuid()
            or target.stat().st_nlink != 1 or target.stat().st_size > CORPUS_LIMIT):
        raise MemoryUnavailable('The user index cache changes its fixed owner destination')
    return target


def publication_paths(memory, connection, scope, payload):
    authorize(scope)
    if not scope.principal or not CATEGORIES <= set(scope.write):
        raise MemoryUnavailable('User index publication requires unrestricted owner write authority')
    _target(memory)
    if _signature(memory, scope, connection) != payload['source_signature']:
        raise MemoryConflict('User index sources or retirement state change before publication')
    return [OUTPUT]


def run(memory, scope, *, query, publish_index, request_id, check_current):
    if (type(publish_index) is not bool or query is not None and (not isinstance(query, str) or len(query) > 2048)
            or publish_index and query is not None):
        raise ValueError('Choose a bounded native index read or publication')
    authorize(scope)
    if publish_index and (not scope.principal or not CATEGORIES <= set(scope.write)):
        raise MemoryUnavailable('User index publication requires unrestricted owner write authority')
    check_current()
    if publish_index:
        with memory._transaction() as connection:
            signature = _signature(memory, scope, connection)
    index = view(memory, scope, '/api/user-index', check_current=check_current)['body']
    if query is not None:
        entry = next((entry for entry in index['files'] if entry['path'] == query or entry['absolute_path'] == query), None)
        if entry is None: return {'ok': False, 'message': 'Not found'}
        return {'ok': True, 'entry': entry}
    if not publish_index: return {'ok': True, 'index': index, 'published': False}
    data = (json.dumps(index, indent=2, ensure_ascii=False) + '\n').encode()
    if len(data) > CORPUS_LIMIT:
        raise MemoryUnavailable('The native user index cache exceeds its publication limit')
    payload = {'operation': 'user_index_publish', 'source_signature': signature}

    def apply(connection):
        publication_paths(memory, connection, scope, payload)
        check_current()
        publish(_target(memory), data)
        return {'status': 'committed', 'artifacts': 1, 'index_digest': hashlib.sha256(data).hexdigest()}

    receipt = memory._operation(scope, request_id, payload, apply,
        publication_digests={OUTPUT: hashlib.sha256(data).hexdigest()})
    if receipt['status'] not in ('committed', 'unchanged'):
        return {'ok': False, 'message': receipt['reason'], 'receipt': receipt}
    with memory._transaction() as connection:
        publication_paths(memory, connection, scope, payload)
        target = _target(memory)
        before = target.stat()
        saved = target.read_bytes()
        after = _target(memory).stat()
        keys = lambda info: (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns)
        if (keys(before) != keys(after) or len(saved) > CORPUS_LIMIT
                or hashlib.sha256(saved).hexdigest() != receipt.get('index_digest')):
            raise MemoryConflict('User index delivery preserves a later cache change')
        index = json.loads(saved)
        check_current()
        return {'ok': True, 'index': index, 'published': True, 'receipt': receipt}
