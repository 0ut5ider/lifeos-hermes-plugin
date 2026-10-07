# ABOUTME: Journals publication of the native freshness cache from admitted current sources.
# ABOUTME: Preserves the previous artifact when sources or owner authority change.
import json
import os
from uuid import uuid4

from .memory_access import MemoryUnavailable
from .memory_freshness import _collect
from .memory_sources import CORPUS_LIMIT, authorize
from .memory_transaction import publish


OUTPUT = 'LIFEOS/USER/CACHE/freshness.json'


def publication_paths(memory, scope):
    authorize(scope)
    if not {'principal', 'assistant', 'project'} <= set(scope.write):
        raise MemoryUnavailable('Freshness cache publication requires unrestricted owner write access')
    path = memory._path(OUTPUT)
    physical = memory.root.parent / '.config/LIFEOS/USER/CACHE/freshness.json'
    if (path.resolve() != physical or path.is_symlink()
            or path.exists() and (not path.is_file() or path.stat().st_uid != os.getuid()
                                  or path.stat().st_size > CORPUS_LIMIT or path.samefile(memory.database))):
        raise MemoryUnavailable('The freshness cache changes its permitted physical destination')
    return [OUTPUT]


def run(memory, scope, *, check_current):
    output = []

    def apply(connection):
        sources = _collect(memory, scope, connection, 'context', None)
        result = memory._native('freshness_cache', sources=sources)
        if (set(result) != {'content', 'bytes', 'generated_at'} or not isinstance(result['content'], str)
                or type(result['bytes']) is not int or not isinstance(result['generated_at'], str)
                or len(result['content'].encode()) > CORPUS_LIMIT
                or result['bytes'] != len(result['content'].encode('utf-16-le')) // 2):
            raise MemoryUnavailable('Native freshness cache rendering returns an invalid artifact')
        payload = json.loads(result['content'])
        if not isinstance(payload, dict) or payload.get('generated_at') != result['generated_at']:
            raise MemoryUnavailable('Native freshness cache rendering changes its generation clock')
        if _collect(memory, scope, connection, 'context', None) != sources:
            raise MemoryUnavailable('Freshness cache sources changed during rendering')
        check_current()
        publication_paths(memory, scope)
        publish(memory._path(OUTPUT), result['content'].encode())
        output.append({'path': str(memory.root / OUTPUT), 'bytes': result['bytes'],
                       'generated_at': result['generated_at']})
        return {'status': 'committed', 'artifacts': 1}

    receipt = memory._operation(scope, 'freshness-cache-' + uuid4().hex,
        {'operation': 'freshness_cache'}, apply)
    return {'ok': receipt['status'] == 'committed', 'result': output[0] if output else None}
