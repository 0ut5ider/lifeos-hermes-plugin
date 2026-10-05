# ABOUTME: Publishes native interview summary and state calculations as one recoverable seed operation.
# ABOUTME: Rechecks source authority and artifact bytes while preserving later owner edits during recovery.
import hashlib
import json
from pathlib import Path
from uuid import uuid4

from .memory_access import MemoryUnavailable
from . import memory_state as state
from . import memory_telos as telos
from .memory_sources import CORPUS_LIMIT
from .memory_transaction import publish


GENERATORS = ('GenerateTelosSummary.ts', 'UpdateLifeosState.ts')


def publication_paths(memory, scope, payload):
    paths = []
    for generator in payload['generators']:
        paths.extend((telos if generator == GENERATORS[0] else state).publication_paths(memory, scope))
    return paths


def _collect(memory, scope, connection, generators):
    return {generator: (telos if generator == GENERATORS[0] else state)._collect(memory, scope, connection)
        for generator in generators}


def _targets(memory, paths):
    return {relative: hashlib.sha256(memory._path(relative).read_bytes()).hexdigest()
        if memory._path(relative).exists() else None for relative in paths}


def run(memory, scope, root, config_dir, generators, *, check_current, request_id=None):
    if request_id is not None and (not isinstance(request_id, str) or not 1 <= len(request_id) <= 256):
        raise ValueError('Interview seeding requires a bounded retry identifier')
    if (not isinstance(root, str) or not Path(root).is_absolute() or Path(root).resolve() != memory.physical_root
            or not isinstance(config_dir, str) or not Path(config_dir).is_absolute()
            or Path(config_dir).resolve() != memory.root.parent / '.config/LIFEOS'
            or not isinstance(generators, list) or not generators
            or generators != [generator for generator in GENERATORS if generator in generators]):
        raise MemoryUnavailable('Interview seeding requires the installed root and fixed native generators')
    payload = {'operation': 'seed_pulse', 'generators': generators}
    with memory._transaction() as connection:
        paths = publication_paths(memory, scope, payload)
        before = _targets(memory, paths)
        sources = _collect(memory, scope, connection, generators)
        outputs = {}
        for generator in generators:
            selected = sources[generator]
            if generator == GENERATORS[0]:
                declared = {'principalIdentity' if source['relative'] == telos.IDENTITY else Path(source['relative']).name:
                    source['content'] for source in selected}
                result = memory._native('telos_summary', sources=declared)
                relative = telos.OUTPUT
            else:
                declared = {str(Path(source['relative']).relative_to('LIFEOS/USER/TELOS')): source['content']
                    for source in selected}
                result = memory._native('lifeos_state', sources=declared, json_output=False)
                relative = state.OUTPUT
            if (not isinstance(result, dict) or set(result) != {'content', 'stdout', 'stderr'}
                    or any(not isinstance(result[name], str) for name in result)
                    or len(json.dumps(result).encode()) > CORPUS_LIMIT):
                raise MemoryUnavailable('The native interview generator returns an invalid artifact')
            outputs[relative] = result['content'].encode()
        if _collect(memory, scope, connection, generators) != sources or _targets(memory, paths) != before:
            raise MemoryUnavailable('Interview sources or artifacts change during seed rendering')
        check_current()
    digests = {relative: hashlib.sha256(content).hexdigest() for relative, content in outputs.items()}
    payload['source_signature'] = hashlib.sha256(json.dumps(sources, sort_keys=True).encode()).hexdigest()

    def apply(connection):
        if _collect(memory, scope, connection, generators) != sources or _targets(memory, paths) != before:
            raise MemoryUnavailable('Interview sources or artifacts change before seed publication')
        check_current()
        publication_paths(memory, scope, payload)
        for relative, content in outputs.items():
            expected = {**before, **{path: digests[path] for path in outputs if path in published}}
            if _collect(memory, scope, connection, generators) != sources or _targets(memory, paths) != expected:
                raise MemoryUnavailable('Interview sources or artifacts change during seed publication')
            check_current()
            publication_paths(memory, scope, payload)
            publish(memory._path(relative), content)
            published.add(relative)
        return {'status': 'committed', 'artifacts': len(outputs)}

    published = set()
    receipt = memory._operation(scope, request_id if request_id is not None else 'seed-' + uuid4().hex, payload, apply,
        publication_digests=digests)
    return {'ok': receipt['status'] == 'committed', 'receipt': receipt}
