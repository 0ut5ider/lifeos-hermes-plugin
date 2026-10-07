# ABOUTME: Supplies admitted constitutional sources to the original native context audit.
# ABOUTME: Checks current authority and destinations before recoverable private report publication.
import hashlib
import json
import os
from pathlib import Path
from uuid import uuid4

from .memory_access import MemoryConflict, MemoryUnavailable
from .memory_freshness import _collect
from .memory_sources import authorize, CORPUS_LIMIT
from .memory_transaction import publish


OUTPUT = 'LIFEOS/MEMORY/STATE/context-audit/AUDIT.md'


def publication_paths(memory, scope):
    authorize(scope)
    if not {'principal', 'assistant', 'project'} <= set(scope.write):
        raise MemoryUnavailable('Context audit publication requires unrestricted owner write access')
    path = memory._path(OUTPUT)
    physical = memory.root.parent / '.config/LIFEOS/USER/MEMORY/STATE/context-audit/AUDIT.md'
    if (path.resolve() != physical or path.is_symlink()
            or path.exists() and (not path.is_file() or path.stat().st_uid != os.getuid()
                                  or path.stat().st_size > CORPUS_LIMIT or path.samefile(memory.database))):
        raise MemoryUnavailable('The context audit changes its permitted physical destination')
    return [OUTPUT]


def run(memory, scope, root, json_output, *, check_current):
    authorize(scope)
    if (not isinstance(root, str) or not Path(root).is_absolute()
            or Path(root).resolve() != memory.physical_root or type(json_output) is not bool):
        raise MemoryUnavailable('Context audit requires the selected installation and a fixed output mode')
    with memory._transaction() as connection:
        sources = _collect(memory, scope, connection, 'context', None)
        if not json_output:
            publication_paths(memory, scope)
            destination = memory._path(OUTPUT)
            original = destination.read_bytes() if destination.exists() else None
        result = memory._native('context_audit', sources=sources)
        if (set(result) != {'report', 'markdown', 'hasCritical'} or not isinstance(result['report'], dict)
                or not isinstance(result['markdown'], str) or type(result['hasCritical']) is not bool
                or len(json.dumps(result).encode()) > CORPUS_LIMIT):
            raise MemoryUnavailable('Native context audit returns an invalid report')
        if _collect(memory, scope, connection, 'context', None) != sources:
            raise MemoryUnavailable('The context audit sources change during rendering')
        check_current()
        if json_output:
            return {'ok': True, **result}

    content = result['markdown'].encode()

    def apply(connection):
        try:
            if _collect(memory, scope, connection, 'context', None) != sources:
                raise MemoryUnavailable('The context audit sources change before publication')
            check_current()
            publication_paths(memory, scope)
            current = destination.read_bytes() if destination.exists() else None
            if current != original:
                raise MemoryUnavailable('The context audit destination changes before publication')
        except MemoryUnavailable as error:
            # No report bytes have been published. Commit the conflict and preserve later edits.
            raise MemoryConflict(str(error)) from error
        publish(memory._path(OUTPUT), content)
        return {'status': 'committed', 'artifacts': 1}

    receipt = memory._operation(scope, 'context-audit-' + uuid4().hex, {'operation': 'context_audit',
        'sources': hashlib.sha256(json.dumps(sources, sort_keys=True).encode()).hexdigest()}, apply,
        publication_digests={OUTPUT: hashlib.sha256(content).hexdigest()})
    return {'ok': receipt['status'] == 'committed', **(result if receipt['status'] == 'committed' else {}),
        'receipt': receipt}
