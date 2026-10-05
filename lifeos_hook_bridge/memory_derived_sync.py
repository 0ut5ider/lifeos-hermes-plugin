# ABOUTME: Admits native derivative plans and rechecks sources before each child runs.
# ABOUTME: Journals fixed tracking state and logs without holding the writer lock across children.
import hashlib
import json
import os
from pathlib import Path
import re
from uuid import uuid4

from .memory_access import MemoryUnavailable, MemoryConflict
from .memory_evidence import _signature
from .memory_sources import (SYNC_FILES, SOURCE_COUNT_LIMIT, CORPUS_LIMIT,
    _text_source, _admit, authorize, json_projection, markdown_projection)
from .memory_transaction import publish


STATE = 'LIFEOS/MEMORY/STATE/derived-sync.json'
LOG = 'LIFEOS/MEMORY/OBSERVABILITY/derived-sync.jsonl'
LOCK = 'LIFEOS/MEMORY/STATE/derived-sync.lock'


def _target(memory, relative):
    path = memory._publication_path(relative)
    physical = memory.root.parent / '.config/LIFEOS/USER' / Path(relative).relative_to('LIFEOS')
    if (path.resolve() != physical.absolute() or path.is_symlink()
            or path.exists() and (not path.is_file() or path.stat().st_uid != os.getuid()
                                 or path.stat().st_nlink != 1 or path.stat().st_size > CORPUS_LIMIT)):
        raise MemoryUnavailable('Derivative tracking changes its fixed owner destination')
    return path


def publication_paths(memory, scope):
    authorize(scope)
    if not {'principal', 'assistant', 'project'} <= set(scope.write):
        raise MemoryUnavailable('Derivative publication requires unrestricted owner write access')
    for relative in (STATE, LOG, LOCK):
        _target(memory, relative)
    return [STATE, LOG]


def _directory(memory, relative, *, system=False):
    path = memory.root / relative
    physical = memory.physical_root / relative if system else memory.root.parent / '.config/LIFEOS/USER' / Path(relative).relative_to('LIFEOS/USER')
    if path.resolve() != physical or path.is_symlink() or path.exists() and not path.is_dir():
        raise MemoryUnavailable('Derivative source directory changes its installed path')
    if not path.exists():
        return []
    entries = list(path.iterdir())
    if len(entries) > SOURCE_COUNT_LIMIT:
        raise MemoryUnavailable('Derivative sources exceed their count limit')
    return entries


def _collect(memory, scope, connection):
    authorize(scope)
    relatives = set(SYNC_FILES)
    for directory in ('CURRENT_STATE', 'IDEAL_STATE'):
        relatives.update('LIFEOS/USER/TELOS/' + directory + '/' + path.name
            for path in _directory(memory, 'LIFEOS/USER/TELOS/' + directory) if path.name.endswith('.md'))
    relatives.update('LIFEOS/PULSE/pages/' + path.name
        for path in _directory(memory, 'LIFEOS/PULSE/pages', system=True) if path.name.endswith('.manifest.toml'))
    if len(relatives) > SOURCE_COUNT_LIMIT:
        raise MemoryUnavailable('Derivative sources exceed their count limit')
    rows = []
    total = 0
    for relative in sorted(relatives):
        path = memory.root / relative
        if not path.exists() and not path.is_symlink():
            continue
        source, timestamp = _text_source(memory, scope, str(path), suffix=path.suffix,
                                         derived_sync=True, preserve_newlines=True)
        if path.stat().st_uid != os.getuid():
            raise MemoryUnavailable('Derivative planning needs owner source files')
        total += len(source['content'].encode())
        if total > CORPUS_LIMIT:
            raise MemoryUnavailable('Derivative sources exceed their transport limit')
        projection = (json_projection(source['content']) if relative.endswith('.json') else
                      markdown_projection(memory, relative, source['content']))
        rows.append((source, timestamp, projection))
    accepted = memory._native('validate_source_batch', contents=[(projection or '') + '\n' + source['path']
        for source, _, projection in rows])['accepted'] if rows else []
    hashes = {}
    pages = []
    for (source, timestamp, projection), valid in zip(rows, accepted, strict=True):
        if projection is None or valid is not True or _admit(memory, connection, scope, source['content'],
                source['relative'], timestamp, projection=projection)['excluded']:
            continue
        if source['relative'].startswith('LIFEOS/PULSE/pages/'):
            match = re.search(r'^\s*id\s*=\s*"([^"\r\n]+)"\s*$', source['content'], re.MULTILINE)
            if match:
                if re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,127}', match[1]) is None:
                    raise MemoryUnavailable('The derivative page needs a bounded native identifier')
                pages.append(match[1])
        else:
            hashes[source['path']] = hashlib.sha256(source['content'].encode()).hexdigest()
    state_bytes = _target(memory, STATE).read_bytes() if _target(memory, STATE).exists() else None
    log_bytes = _target(memory, LOG).read_bytes() if _target(memory, LOG).exists() else b''
    _target(memory, LOCK)
    state = json.loads(state_bytes) if state_bytes is not None else None
    if state is not None:
        if (not isinstance(state, dict) or set(state) != {'fileHashes', 'lastRun'}
                or not isinstance(state['fileHashes'], dict) or not isinstance(state['lastRun'], str)
                or re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z', state['lastRun']) is None
                or any(not isinstance(path, str) or not isinstance(digest, str)
                       or re.fullmatch('[0-9a-f]{64}', digest) is None for path, digest in state['fileHashes'].items())):
            raise MemoryUnavailable('The native derivative state is malformed')
        state = {**state, 'fileHashes': {path: digest for path, digest in state['fileHashes'].items() if path in hashes}}
    lines = []
    for line in log_bytes.decode('utf-8').splitlines():
        if not line:
            continue
        value = json.loads(line)
        if (not isinstance(value, dict) or not isinstance(value.get('ts'), str)
                or not isinstance(value.get('changed'), list) or not isinstance(value.get('actions'), list)
                or type(value.get('dryRun')) is not bool):
            raise MemoryUnavailable('The native derivative log is malformed')
        projection = json_projection(line)
        if projection is not None and not memory._filter_history(connection, scope, projection,
                value['ts'], reviewed=True)['excluded']:
            lines.append(line)
    return {'hashes': hashes, 'pages': pages, 'state': state, 'lines': lines, 'root_binding': str(memory.physical_root),
            'raw_signature': _signature([row[0] for row in rows]),
            'tracking_signature': _signature([state_bytes.hex() if state_bytes is not None else None, log_bytes.hex()])}


def _plan(memory, snapshot, args):
    return memory._native('derived_sync_plan', hashes=snapshot['hashes'], pages=snapshot['pages'],
                          state=snapshot['state'], force='--force' in args)


def _command(command):
    return ' '.join(json.dumps(part, ensure_ascii=False, separators=(',', ':')) if ' ' in part else part for part in command)


def _status(memory, snapshot):
    from datetime import datetime, timezone
    state = snapshot['state']
    path = str(memory.root / STATE)
    lines = [f'state: missing at {path}'] if state is None else [f'state: {path}',
        f"state age ms: {int((datetime.now(timezone.utc) - datetime.fromisoformat(state['lastRun'])).total_seconds() * 1000)}",
        f"last run: {state['lastRun']}"]
    lines.append(f"watched files: {len(snapshot['hashes'])}")
    last = json.loads(snapshot['lines'][-1]) if snapshot['lines'] else None
    lines.append(f"last log: {last['ts']} changed={len(last['changed'])} actions={len(last['actions'])} dryRun={str(last['dryRun']).lower()}"
                 if last is not None else 'last log: none')
    return '\n'.join(lines)


def handle(memory, scope, operation, arguments, *, check_current):
    fields = {'derived_sync_plan': {'args'}, 'derived_sync_check': {'args', 'signature'},
              'derived_sync_publish': {'args', 'signature', 'logs', 'failed'}}
    if set(arguments) != fields[operation]:
        raise ValueError('Derivative sync requires its declared native arguments')
    args = arguments['args']
    if (not isinstance(args, list) or len(args) > 8
            or any(not isinstance(arg, str) or arg not in {'--dry-run', '--status', '--force'} for arg in args)):
        raise ValueError('Choose supported native derivative arguments')
    writing = '--dry-run' not in args and '--status' not in args
    if operation != 'derived_sync_plan' and not writing:
        raise ValueError('Derivative tracking needs a write operation')
    if writing:
        publication_paths(memory, scope)
    with memory._transaction() as connection:
        snapshot = _collect(memory, scope, connection)
        plan = _plan(memory, snapshot, args)
        check_current()
        if _collect(memory, scope, connection) != snapshot:
            raise MemoryConflict('Derivative planning sources changed during collection')
        signature = _signature({'snapshot': snapshot, 'scope': scope.signature, 'args': args})
        if operation == 'derived_sync_plan':
            return {'ok': True, **plan, 'signature': signature, 'lock': str(memory.root / LOCK),
                    'status': _status(memory, snapshot) if '--status' in args else ''}
        if arguments['signature'] != signature:
            raise MemoryConflict('Derivative sources or tracking state changed before execution')
        if operation == 'derived_sync_check':
            return {'ok': True}
        logs = arguments['logs']
        failed = arguments['failed']
        if (not isinstance(logs, list) or not isinstance(failed, list) or len(logs) != len(plan['actions'])
                or len(failed) != len(logs) or any(type(value) is not bool for value in failed)):
            raise ValueError('Derivative publication needs one result for every planned action')
        for log, action, failure in zip(logs, plan['actions'], failed, strict=True):
            if (not isinstance(log, dict) or set(log) != {'cmd', 'exit', 'ms'}
                    or log['cmd'] != _command(action['cmd']) or not (log['exit'] is None or type(log['exit']) is int)
                    or type(log['ms']) is not int or not 0 <= log['ms'] <= 24 * 60 * 60 * 1000
                    or not failure and log['exit'] != 0):
                raise ValueError('Derivative child results change their planned command or duration')
        state = memory._native('derived_sync_finish', hashes=snapshot['hashes'], pages=snapshot['pages'],
            state=snapshot['state'], force='--force' in args, failed=failed)
        line = {'ts': state['lastRun'], 'changed': plan['changed'], 'actions': logs, 'dryRun': False}
        content = '\n'.join([*snapshot['lines'], json.dumps(line, separators=(',', ':'))]) + '\n'
        if len(content.encode()) > CORPUS_LIMIT:
            raise MemoryUnavailable('Derivative tracking log exceeds its publication limit')

    def apply(connection):
        try:
            current = _collect(memory, scope, connection)
            check_current()
            publication_paths(memory, scope)
        except (MemoryUnavailable, OSError) as error:
            raise MemoryConflict('Derivative authority or sources changed before tracking publication') from error
        if current != snapshot:
            raise MemoryConflict('Derivative inputs changed before tracking publication')
        publish(_target(memory, STATE), (json.dumps(state, indent=2) + '\n').encode())
        publish(_target(memory, LOG), content.encode())
        return {'status': 'committed', 'artifacts': 2}

    receipt = memory._operation(scope, 'derived-sync-' + uuid4().hex,
                                {'operation': 'derived_sync', 'source_signature': signature}, apply)
    return {'ok': receipt['status'] == 'committed'}
