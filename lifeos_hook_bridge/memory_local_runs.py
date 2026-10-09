# ABOUTME: Publishes fixed LocalIntelligence run logs and start markers through the owner journal.
# ABOUTME: Checks current authority and preserves later diagnostic edits before publication.
from datetime import datetime, timezone
import hashlib
import re
from uuid import uuid4

from .memory_access import MemoryUnavailable, MemoryConflict
from .memory_evidence import _signature
from .memory_local_refresh import _request, _collect, _output
from .memory_source_review import _retirement_digest
from .memory_sources import SOURCE_LIMIT
from .memory_tab_freshness import _checked

RUNS = 'LIFEOS/USER/CUSTOMIZATIONS/SKILLS/LocalIntelligence/runs'
RUN_ID = r'\d{4}-\d{2}-\d{2}T\d{2}-\d{2}-\d{2}-\d{3}Z_[0-9a-f]{8}'


def run_paths(run_id):
    if not isinstance(run_id, str) or re.fullmatch(RUN_ID, run_id) is None:
        raise ValueError('Choose a native LocalIntelligence run identifier')
    return [RUNS + '/' + run_id + '.log', RUNS + '/' + run_id + '.log.started']


def publication_paths(memory, scope, payload):
    _request(scope)
    if (set(payload) != {'operation', 'run_id', 'phase'} or payload['operation'] != 'local_run'
            or not isinstance(payload['phase'], str) or payload['phase'] not in {'start', 'finish'}):
        raise ValueError('Choose a declared LocalIntelligence diagnostic publication')
    paths = run_paths(payload['run_id'])
    for relative in paths:
        path = _checked(memory, memory._publication_path(relative))
        if path.exists() and (not path.is_file() or path.stat().st_size > SOURCE_LIMIT):
            raise MemoryUnavailable('LocalIntelligence diagnostics require bounded regular owner files')
    return paths if payload['phase'] == 'start' else paths[:1]


def _snapshot(memory, scope, connection, run_id, check_current):
    _request(scope)
    check_current()
    paths = run_paths(run_id)
    contents, records = _collect(memory, scope, connection, paths)
    check_current()
    return {'contents': contents, 'sources': records, 'scope': scope.signature,
        'root': str(memory.physical_root), 'retirement': _retirement_digest(connection)}


def run(memory, scope, operation, arguments, *, check_current):
    from .memory_transaction import publish
    _request(scope)
    fields = {'run_id'} if operation == 'local_run_start' else {'run_id', 'signature', 'content', 'exit_code'}
    if set(arguments) != fields:
        raise ValueError('Choose declared LocalIntelligence diagnostic arguments')
    run_id = arguments['run_id']
    paths = run_paths(run_id)
    starting = operation == 'local_run_start'
    with memory._transaction() as connection:
        snapshot = _snapshot(memory, scope, connection, run_id, check_current)
        if starting:
            if any(value is not None for value in snapshot['contents'].values()):
                raise MemoryConflict('LocalIntelligence diagnostics preserve existing run files')
            contents = {paths[0]: '', paths[1]: datetime.now(timezone.utc).isoformat()}
        else:
            if (not isinstance(arguments['signature'], str) or arguments['signature'] != _signature(snapshot)
                    or snapshot['contents'][paths[0]] != '' or snapshot['contents'][paths[1]] is None):
                raise MemoryConflict('LocalIntelligence diagnostics preserve changed run files or authority')
            if (not isinstance(arguments['content'], str) or type(arguments['exit_code']) is not int
                    or not -255 <= arguments['exit_code'] <= 255):
                raise ValueError('LocalIntelligence diagnostics require native text and a process exit code')
            contents = {paths[0]: arguments['content'] + '\n[exit] code=' + str(arguments['exit_code']) + '\n'}
        for value in contents.values():
            if len(value.encode()) > SOURCE_LIMIT:
                raise MemoryUnavailable('LocalIntelligence diagnostics exceed their complete byte limit')
            _output(memory, scope, connection, value)
        check_current()
    payload = {'operation': 'local_run', 'run_id': run_id, 'phase': 'start' if starting else 'finish'}
    published = snapshot
    def apply(connection):
        nonlocal published
        if _snapshot(memory, scope, connection, run_id, check_current) != snapshot:
            raise MemoryConflict('LocalIntelligence diagnostics preserve later owner edits')
        for relative, value in contents.items():
            check_current()
            _output(memory, scope, connection, value)
            publish(memory._publication_path(relative), value.encode())
        published = _snapshot(memory, scope, connection, run_id, check_current)
        if any(published[key] != snapshot[key] for key in ('scope', 'root', 'retirement')):
            raise MemoryConflict('LocalIntelligence diagnostic authority changes during publication')
        expected = dict(snapshot['contents'], **contents)
        if published['contents'] != expected:
            raise MemoryConflict('LocalIntelligence diagnostics change during publication')
        return {'status': 'committed'}
    receipt = memory._operation(scope, 'local-run-' + uuid4().hex, payload, apply,
        publication_digests={relative: hashlib.sha256(value.encode()).hexdigest() for relative, value in contents.items()})
    if receipt['status'] != 'committed':
        raise MemoryUnavailable('LocalIntelligence diagnostics require recovery or a current retry')
    with memory._transaction() as connection:
        if _snapshot(memory, scope, connection, run_id, check_current) != published:
            raise MemoryConflict('LocalIntelligence diagnostics change before delivery')
        check_current()
    return {'ok': True, 'signature': _signature(published)}
