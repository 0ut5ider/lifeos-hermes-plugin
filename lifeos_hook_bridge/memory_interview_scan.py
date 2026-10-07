# ABOUTME: Supplies admitted owner context and setup files to the native interview scanner.
# ABOUTME: Checks decoded assistant naming and current sources before scan output reaches a caller.
import json
import os
from pathlib import Path

from .memory_access import MemoryUnavailable
from .memory_evidence import _collect as evidence_sources, _cache as evidence_cache, OUTPUT as EVIDENCE_CACHE
from .memory_freshness import _collect as freshness_sources
from .memory_sources import (authorize, _text_source, _admit, CORPUS_LIMIT, SOURCE_COUNT_LIMIT,
                             INTERVIEW_SETUP_FILES)


IDENTITY = 'LIFEOS/USER/DIGITAL_ASSISTANT/DA_IDENTITY.md'


def _collect(memory, scope, connection):
    authorize(scope)
    sources = {}
    for view in ('context', 'telos', 'state'):
        for source in freshness_sources(memory, scope, connection, view, None):
            sources[source['path']] = source
    for relative in sorted(INTERVIEW_SETUP_FILES):
        path = memory.root / relative
        if not path.exists() and not path.is_symlink():
            continue
        source, timestamp = _text_source(memory, scope, str(path), suffix=Path(relative).suffix, interview_setup=True)
        if path.stat().st_uid != os.getuid():
            raise MemoryUnavailable('The interview setup source has another owner')
        accepted = memory._native('validate_source_batch', contents=[source['content']])['accepted']
        if accepted == [True] and not _admit(memory, connection, scope, source['content'], relative, timestamp)['excluded']:
            sources[source['path']] = source
    if len(sources) > SOURCE_COUNT_LIMIT or sum(len(source['content'].encode()) for source in sources.values()) > CORPUS_LIMIT:
        raise MemoryUnavailable('Interview sources exceed their transport limits')
    name = memory._native('interview_scan_name', content=sources.get(str(memory.root / IDENTITY), {}).get('content'))
    if set(name) != {'name'} or not isinstance(name['name'], str) or len(name['name']) > 256:
        raise MemoryUnavailable('Native interview identity returns an invalid name')
    identity = sources.get(str(memory.root / IDENTITY))
    if identity is not None:
        projection = identity['content'] + '\n' + name['name']
        valid = memory._native('validate_source_batch', contents=[projection])['accepted']
        if (valid != [True] or memory._filter_history(connection, scope, projection, identity['lastModified'],
                reviewed=True)['excluded']):
            sources.pop(identity['path'])
            name = memory._native('interview_scan_name', content=None)
    present = evidence_cache(memory, str(memory.root / EVIDENCE_CACHE)).exists()
    return {'sources': list(sources.values()), 'name': name['name'],
            'evidence': evidence_sources(memory, scope, connection, None) if present else None}


def read(memory, scope, args, *, check_current):
    authorize(scope)
    if not isinstance(args, list) or len(args) > 16 or any(not isinstance(arg, str) or len(arg) > 4096 for arg in args):
        raise ValueError('Choose bounded native interview scan arguments')
    with memory._transaction() as connection:
        sources = _collect(memory, scope, connection)
        result = memory._native('interview_scan', args=args, **sources)
        if (set(result) != {'status', 'stdout', 'stderr'} or type(result['status']) is not int or result['status'] not in (0, 1)
                or any(not isinstance(result[field], str) for field in ('stdout', 'stderr'))
                or len(json.dumps(result).encode()) > CORPUS_LIMIT):
            raise MemoryUnavailable('Native interview scan returns an invalid result')
        if _collect(memory, scope, connection) != sources:
            raise MemoryUnavailable('Interview scan sources changed during rendering')
        check_current()
        return {'ok': True, 'result': result}
