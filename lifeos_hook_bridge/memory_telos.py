# ABOUTME: Supplies admitted TELOS and principal identity text to the native summary parser.
# ABOUTME: Rechecks current authority and sources before journaled summary publication.
import json
import os
from pathlib import Path
from uuid import uuid4

from .memory_access import MemoryUnavailable
from .memory_sources import authorize, read_markdown, CORPUS_LIMIT, TELOS_SOURCES
from .memory_transaction import publish


OUTPUT = 'LIFEOS/USER/TELOS/PRINCIPAL_TELOS.md'
IDENTITY = 'LIFEOS/USER/PRINCIPAL/PRINCIPAL_IDENTITY.md'


def publication_paths(memory, scope):
    authorize(scope)
    if not {'principal', 'assistant', 'project'} <= set(scope.write):
        raise MemoryUnavailable('TELOS summary publication requires unrestricted owner write access')
    path = memory._path(OUTPUT)
    physical = memory.root.parent / '.config/LIFEOS/USER/TELOS/PRINCIPAL_TELOS.md'
    if (path.resolve() != physical or path.is_symlink()
            or path.exists() and (not path.is_file() or path.stat().st_uid != os.getuid()
                                  or path.stat().st_size > CORPUS_LIMIT or path.samefile(memory.database))):
        raise MemoryUnavailable('The TELOS summary changes its permitted physical destination')
    return [OUTPUT]


def _collect(memory, scope, connection):
    authorize(scope)
    directory = memory._path('LIFEOS/USER/TELOS')
    physical = memory.root.parent / '.config/LIFEOS/USER/TELOS'
    if directory.resolve() != physical or directory.is_symlink() or directory.exists() and not directory.is_dir():
        raise MemoryUnavailable('The TELOS source directory changes its permitted physical path')
    paths = [str(memory.root / relative) for relative in sorted(TELOS_SOURCES | {IDENTITY})
             if (memory.root / relative).exists() or (memory.root / relative).is_symlink()]
    return read_markdown(memory, scope, paths, connection=connection)


def run(memory, scope, root, *, check_current):
    if (not isinstance(root, str) or not Path(root).is_absolute()
            or Path(root).resolve() != memory.root.parent / '.config/LIFEOS/USER/TELOS'):
        raise MemoryUnavailable('Choose the installed TELOS summary source root')
    output = []

    def apply(connection):
        sources = _collect(memory, scope, connection)
        declared = {'principalIdentity' if source['relative'] == IDENTITY else Path(source['relative']).name:
                    source['content'] for source in sources}
        result = memory._native('telos_summary', sources=declared)
        if (set(result) != {'content', 'stdout', 'stderr'}
                or any(not isinstance(result[name], str) for name in ('content', 'stdout', 'stderr'))
                or len(json.dumps(result).encode()) > CORPUS_LIMIT):
            raise MemoryUnavailable('The native TELOS parser returns an invalid summary artifact')
        if _collect(memory, scope, connection) != sources:
            raise MemoryUnavailable('The TELOS summary sources changed during rendering')
        check_current()
        publication_paths(memory, scope)
        publish(memory._path(OUTPUT), result['content'].encode())
        output.append(result)
        return {'status': 'committed', 'artifacts': 1}

    receipt = memory._operation(scope, 'telos-' + uuid4().hex, {'operation': 'telos_summary'}, apply)
    return {'ok': receipt['status'] == 'committed', 'stdout': output[0]['stdout'] if output else '',
            'stderr': output[0]['stderr'] if output else ''}
