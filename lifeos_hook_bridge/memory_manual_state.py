# ABOUTME: Runs fixed native state proposals and identity synchronization on admitted private snapshots.
# ABOUTME: Rechecks original sources and owner authority before recoverable publication.
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import tempfile
from uuid import uuid4

from .memory_access import MemoryUnavailable, MemoryConflict
from .memory_sources import (authorize, _admit, _source_time, markdown_projection,
                             SOURCE_LIMIT, SOURCE_COUNT_LIMIT, CORPUS_LIMIT)
from .memory_operational_views import projection
from .memory_tab_freshness import _checked
from .memory_transaction import publish


PREFIX = 'LIFEOS/USER/TELOS/CURRENT_STATE/'
QUEUE = PREFIX + 'proposals.jsonl'
TARGETS = frozenset({'CONSUMPTION', 'ACTIVITY', 'SOCIAL', 'FINANCIAL', 'SIGNALS', 'SNAPSHOT'})
PROPOSAL_SOURCES = frozenset({QUEUE}) | frozenset(PREFIX + name + '.md' for name in TARGETS)
IDENTITY = 'LIFEOS/USER/PRINCIPAL/PRINCIPAL_IDENTITY.md'
SYSTEM_PUBLICATIONS = frozenset({'settings.json'})
TOOLS = {'ProposeCurrentStateEntry.ts', 'ApproveCurrentStateEntries.ts', 'SyncIdentityToSettings.ts'}


def _arguments(tool, args):
    if not isinstance(tool, str) or tool not in TOOLS or not isinstance(args, list) or len(args) > 6 or any(
            not isinstance(value, str) or len(value.encode()) > SOURCE_LIMIT for value in args):
        raise ValueError('Choose a fixed native state command with bounded arguments')
    if tool == 'SyncIdentityToSettings.ts':
        if args not in ([], ['--verbose']): raise ValueError('Choose the native identity synchronization command')
    elif tool == 'ApproveCurrentStateEntries.ts':
        if args not in ([], ['--review'], ['--approve-all']) and not (
                len(args) == 2 and args[0] in ('--approve', '--reject') and 0 < len(args[1]) <= 256):
            raise ValueError('Choose one native proposal review action')
    else:
        if len(args) != 6 or set(args[::2]) != {'--source', '--target', '--json'}:
            raise ValueError('Choose the three native proposal fields')
        values = dict(zip(args[::2], args[1::2], strict=True))
        if values['--source'] not in ('lifelog', 'calendar', 'gmail', 'homebridge', 'manual', 'amazon', 'bills') or values['--target'] not in TARGETS:
            raise ValueError('Choose a declared proposal source and target')
        payload = json.loads(values['--json'])
        if not isinstance(payload, dict) or projection(values['--json']) is None:
            raise ValueError('Proposal payloads require bounded JSON objects')
    return tool != 'ApproveCurrentStateEntries.ts' or bool(args) and args[0] != '--review'


def _queue(content):
    lines = [line for line in content.split('\n') if line]
    if len(lines) > SOURCE_COUNT_LIMIT: raise MemoryUnavailable('The proposal queue exceeds its record limit')
    try: rows = [json.loads(line) for line in lines]
    except (ValueError, RecursionError) as error:
        raise MemoryUnavailable('The proposal queue requires complete JSON records') from error
    for row in rows:
        if (not isinstance(row, dict) or set(row) != {'id', 'timestamp', 'source', 'target', 'payload', 'status'}
                or not isinstance(row['id'], str) or not 0 < len(row['id']) <= 256
                or not isinstance(row['timestamp'], str) or len(row['timestamp']) > 128
                or row['source'] not in ('lifelog', 'calendar', 'gmail', 'homebridge', 'manual', 'amazon', 'bills')
                or not isinstance(row['target'], str) or row['target'] not in TARGETS or row['status'] not in ('pending', 'approved', 'rejected')
                or not isinstance(row['payload'], dict)):
            raise MemoryUnavailable('The proposal queue changes its declared record format')
    return rows


def _collect(memory, scope, connection, tool, args):
    names = [IDENTITY, 'settings.json'] if tool == 'SyncIdentityToSettings.ts' else [QUEUE]
    contents, fingerprints, candidates = {}, [], []
    keys = lambda info: (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns)
    for relative in names:
        path = _checked(memory, memory.root / relative)
        if not path.exists():
            fingerprints.append((relative, None))
            continue
        before = path.stat()
        if not path.is_file() or before.st_size > SOURCE_LIMIT:
            raise MemoryUnavailable('Native state sources require bounded regular owner files')
        with path.open('rb') as stream: raw = stream.read(SOURCE_LIMIT + 1)
        if len(raw) > SOURCE_LIMIT: raise MemoryUnavailable('A native state source exceeds its byte limit')
        content = raw.decode('utf-8')
        after = _checked(memory, path).stat()
        if keys(before) != keys(after): raise MemoryUnavailable('A native state source changes during collection')
        contents[relative] = content
        fingerprints.append((relative, keys(after), raw))
        if relative == QUEUE:
            rows = _queue(content)
            decoded = projection(json.dumps(rows))
            if tool == 'ApproveCurrentStateEntries.ts' and args and args[0] in ('--approve', '--approve-all'):
                names.extend(sorted({PREFIX + row['target'] + '.md' for row in rows
                    if row['status'] == 'pending' and (args[0] == '--approve-all' or row['id'] == args[1])}))
        elif relative.endswith('.json'): decoded = projection(content)
        else: decoded = markdown_projection(memory, relative, content)
        candidates.append((relative, content, _source_time(after), decoded))
    if len(json.dumps(contents).encode()) > CORPUS_LIMIT:
        raise MemoryUnavailable('Native state sources exceed their transport limit')
    checked = memory._native('validate_source_batch', contents=[(decoded or '') + '\n' + relative
        for relative, _, _, decoded in candidates])['accepted'] if candidates else []
    for (relative, content, timestamp, decoded), accepted in zip(candidates, checked, strict=True):
        if decoded is None or accepted is not True or _admit(memory, connection, scope,
                content, relative, timestamp, projection=decoded)['excluded']:
            raise MemoryUnavailable('The native state source requires current safe owner review')
    return contents, fingerprints


def _render(memory, tool, args, contents):
    with tempfile.TemporaryDirectory(prefix='lifeos-state-') as directory:
        home = Path(directory)
        root = home / '.claude'
        root.mkdir(mode=0o700)
        (root / 'LIFEOS/USER/TELOS/CURRENT_STATE').mkdir(parents=True, mode=0o700)
        for relative, content in contents.items(): publish(root / relative, content.encode())
        environment = dict(os.environ, HOME=str(home), LIFEOS_DIR=str(root / 'LIFEOS'),
            LIFEOS_CONFIG_DIR=str(root / 'LIFEOS/USER/CONFIG'), LIFEOS_MEMORY_INTERNAL='1', BUN_CONFIG_NO_AUTO_INSTALL='1')
        for name in ('LIFEOS_CONFIG_PATH', 'LIFEOS_MEMORY_CONTEXT', 'LIFEOS_MEMORY_PUBLICATION_JOURNAL'):
            environment.pop(name, None)
        result = subprocess.run([memory.bun, '--no-install', str(memory.root / 'LIFEOS/TOOLS' / tool), *args],
            capture_output=True, text=True, timeout=30, env=environment, cwd=home)
        if result.returncode: raise MemoryUnavailable('The native state command refuses the admitted snapshot')
        names = SYSTEM_PUBLICATIONS if tool == 'SyncIdentityToSettings.ts' else PROPOSAL_SOURCES
        rendered = {relative: (root / relative).read_bytes().decode('utf-8') for relative in names if (root / relative).exists()}
        if any(len(value.encode()) > SOURCE_LIMIT for value in rendered.values()) or len(json.dumps(rendered).encode()) > CORPUS_LIMIT:
            raise MemoryUnavailable('Native state output exceeds its byte limit')
        stdout, stderr = result.stdout.replace(str(root), str(memory.root)), result.stderr.replace(str(root), str(memory.root))
        if len((stdout + stderr).encode()) > CORPUS_LIMIT:
            raise MemoryUnavailable('Native state diagnostics exceed their transport limit')
        return {'contents': rendered, 'stdout': stdout, 'stderr': stderr}


def publication_paths(memory, scope, tool, *, paths=None):
    authorize(scope)
    if not {'principal', 'assistant', 'project'} <= set(scope.write):
        raise MemoryUnavailable('Native state publication requires unrestricted owner write authority')
    names = SYSTEM_PUBLICATIONS if tool == 'SyncIdentityToSettings.ts' else PROPOSAL_SOURCES
    if paths is None: paths = ['settings.json'] if tool == 'SyncIdentityToSettings.ts' else [QUEUE]
    if (not isinstance(paths, list) or len(paths) > len(names) or len(set(paths)) != len(paths)
            or any(relative not in names for relative in paths)):
        raise MemoryUnavailable('Choose fixed native state publication paths')
    for relative in paths: _checked(memory, memory._publication_path(relative))
    return sorted(paths)


def run(memory, scope, *, tool, args, check_current):
    writing = _arguments(tool, args)
    authorize(scope)
    if not scope.principal: raise MemoryUnavailable('Native state commands require a bound owner')
    if writing: publication_paths(memory, scope, tool)
    check_current()
    with memory._transaction() as connection:
        contents, fingerprints = _collect(memory, scope, connection, tool, args)
        if tool == 'ProposeCurrentStateEntry.ts':
            payload = dict(zip(args[::2], args[1::2], strict=True))['--json']
            decoded = projection(payload)
            if memory._native('validate_source_batch', contents=[decoded])['accepted'] != [True] or memory._filter_history(
                    connection, scope, decoded, datetime.now(timezone.utc).isoformat())['excluded']:
                raise MemoryUnavailable('The proposed state payload is excluded')
        if tool == 'ApproveCurrentStateEntries.ts' and args and args[0] in ('--approve', '--approve-all'):
            rows = _queue(contents.get(QUEUE, ''))
            for row in rows:
                if row['status'] == 'pending' and (args[0] == '--approve-all' or row['id'] == args[1]) and PREFIX + row['target'] + '.md' not in contents:
                    raise MemoryUnavailable('Approval requires the existing declared state destination')
        result = _render(memory, tool, args, contents)
        if QUEUE in result['contents']: _queue(result['contents'][QUEUE])
        check_current()
        if _collect(memory, scope, connection, tool, args) != (contents, fingerprints):
            raise MemoryConflict('Native state sources change during rendering')
        if memory._filter_history(connection, scope, result['stdout'] + result['stderr'],
                datetime.now(timezone.utc).isoformat())['excluded']:
            raise MemoryUnavailable('The native state diagnostics contain excluded text')
    if not writing:
        check_current()
        return {'ok': True, 'stdout': result['stdout'], 'stderr': result['stderr']}
    changes = {relative: text for relative, text in result['contents'].items() if contents.get(relative) != text}
    def apply(connection):
        check_current()
        if _collect(memory, scope, connection, tool, args) != (contents, fingerprints):
            raise MemoryConflict('Native state sources change before publication')
        publication_paths(memory, scope, tool, paths=sorted(changes))
        for relative, content in sorted(changes.items()):
            check_current()
            publish(memory._publication_path(relative), content.encode())
        check_current()
        return {'status': 'committed', 'artifacts': len(changes)}
    receipt = memory._operation(scope, 'manual-state-' + uuid4().hex,
        {'operation': 'manual_state', 'tool': tool, 'args': args, 'paths': sorted(changes)}, apply)
    check_current()
    return {'ok': receipt['status'] == 'committed', 'stdout': result['stdout'] if receipt['status'] == 'committed' else '',
            'stderr': result['stderr'] if receipt['status'] == 'committed' else ''}
