# ABOUTME: Supplies admitted TELOS dimension text to the native state calculations.
# ABOUTME: Rechecks sources and authority before recoverable publication of the state file.
import json
import os
from pathlib import Path
from uuid import uuid4

from .memory_access import MemoryUnavailable
from .memory_sources import authorize, read_markdown, CORPUS_LIMIT, STATE_SOURCES
from .memory_transaction import publish


OUTPUT = 'LIFEOS/USER/TELOS/LIFEOS_STATE.json'


def publication_paths(memory, scope):
    authorize(scope)
    if not {'principal', 'assistant', 'project'} <= set(scope.write):
        raise MemoryUnavailable('State publication requires unrestricted owner write access')
    path = memory._path(OUTPUT)
    physical = memory.root.parent / '.config/LIFEOS/USER/TELOS/LIFEOS_STATE.json'
    if (path.resolve() != physical or path.is_symlink()
            or path.exists() and (not path.is_file() or path.stat().st_uid != os.getuid()
                                  or path.stat().st_size > CORPUS_LIMIT or path.samefile(memory.database))):
        raise MemoryUnavailable('The state artifact changes its permitted physical destination')
    return [OUTPUT]


def _collect(memory, scope, connection):
    authorize(scope)
    for directory in ('', 'IDEAL_STATE', 'CURRENT_STATE'):
        path = memory._path('LIFEOS/USER/TELOS' + ('/' + directory if directory else ''))
        physical = memory.root.parent / '.config/LIFEOS/USER/TELOS' / directory
        if path.resolve() != physical or path.is_symlink() or path.exists() and not path.is_dir():
            raise MemoryUnavailable('A TELOS source directory changes its permitted physical path')
    paths = [str(memory.root / relative) for relative in sorted(STATE_SOURCES)
             if (memory.root / relative).exists() or (memory.root / relative).is_symlink()]
    return read_markdown(memory, scope, paths, connection=connection)


def run(memory, scope, root, json_output, *, check_current):
    if (not isinstance(root, str) or not Path(root).is_absolute()
            or Path(root).resolve() != (memory.root / 'LIFEOS').resolve() or type(json_output) is not bool):
        raise MemoryUnavailable('Choose the installed TELOS state writer and output format')
    output = []

    def apply(connection):
        sources = _collect(memory, scope, connection)
        declared = {str(Path(source['relative']).relative_to('LIFEOS/USER/TELOS')): source['content']
                    for source in sources}
        result = memory._native('lifeos_state', sources=declared, json_output=json_output)
        if (set(result) != {'content', 'stdout', 'stderr'}
                or any(not isinstance(result[name], str) for name in ('content', 'stdout', 'stderr'))
                or len(json.dumps(result).encode()) > CORPUS_LIMIT):
            raise MemoryUnavailable('The native state calculation returns an invalid artifact')
        if _collect(memory, scope, connection) != sources:
            raise MemoryUnavailable('The TELOS sources changed during state rendering')
        check_current()
        publication_paths(memory, scope)
        publish(memory._path(OUTPUT), result['content'].encode())
        output.append(result)
        return {'status': 'committed', 'artifacts': 1}

    receipt = memory._operation(scope, 'state-' + uuid4().hex,
        {'operation': 'lifeos_state', 'json_output': json_output}, apply)
    return {'ok': receipt['status'] == 'committed', 'stdout': output[0]['stdout'] if output else '',
            'stderr': output[0]['stderr'] if output else ''}
