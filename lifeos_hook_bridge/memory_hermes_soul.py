# ABOUTME: Admits current native identity sources for the standalone Hermes soul publisher.
# ABOUTME: Recovers the fixed profile and workspace output pair after interrupted publication.
import hashlib
import json
import os
from pathlib import Path
from uuid import uuid4

from .memory_access import MemoryUnavailable, MemoryConflict
from .memory_prompt import SOURCES
from .memory_sources import authorize, read_markdown, CORPUS_LIMIT
from .memory_transaction import MemoryTransaction, publish


def _collect(memory, scope, connection):
    paths = {name: relative for name, relative in SOURCES.items() if name != 'systemPrompt'}
    selected = read_markdown(memory, scope, [str(memory.root / path) for path in paths.values()], connection=connection)
    contents = {source['relative']: source['content'] for source in selected}
    declared = {name: contents.get(relative, '') for name, relative in paths.items()}
    for category, name in (('principal', 'principalMemory'), ('assistant', 'daMemory')):
        declared[name] = '\n'.join(memory._hot_snapshot(connection, category)['entries'])
    names = memory._native('hermes_soul_names', sources=declared)
    if set(names) != {'name', 'fullName', 'principal'} or any(not isinstance(value, str) or len(value) > 256 for value in names.values()):
        raise MemoryUnavailable('Native Hermes soul naming is invalid')
    for name, fields in (('daIdentity', ('name', 'fullName')), ('principal', ('principal',))):
        projection = declared[name] + '\n' + '\n'.join(names[field] for field in fields)
        valid = memory._native('validate_source_batch', contents=[projection])['accepted']
        timestamp = next((source['lastModified'] for source in selected if source['relative'] == paths[name]),
                         '1970-01-01T00:00:00Z')
        if valid != [True] or memory._filter_history(connection, scope, projection, timestamp, reviewed=True)['excluded']:
            declared[name] = ''
    return {'declared': declared, 'selected': selected}


def _targets(memory, profile, workspace):
    targets = {'SOUL.md': Path(profile).absolute() / 'SOUL.md',
               '.hermes.md': Path(workspace).absolute() / '.hermes.md'}
    if targets['SOUL.md'] == targets['.hermes.md']:
        raise MemoryUnavailable('Hermes outputs need distinct installed destinations')
    for path in targets.values():
        parent = path.parent
        if parent.resolve() != parent or parent.exists() and (not parent.is_dir() or parent.stat().st_uid != os.getuid()):
            raise MemoryUnavailable('Hermes output directory changes its installed owner path')
        if path.exists() or path.is_symlink():
            info = path.lstat()
            if (path.is_symlink() or not path.is_file() or info.st_uid != os.getuid()
                    or info.st_size > CORPUS_LIMIT or info.st_nlink != 1
                    or memory.database.exists() and path.samefile(memory.database)):
                raise MemoryUnavailable('Hermes output needs a bounded regular owner file')
    return targets


def _snapshot(targets):
    result = {}
    for name, path in targets.items():
        if not path.exists():
            result[name] = None
            continue
        before = path.stat()
        data = path.read_bytes()
        after = path.stat()
        signature = lambda info: (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_mode)
        if signature(before) != signature(after):
            raise MemoryUnavailable('Hermes output changes during collection')
        result[name] = {'digest': hashlib.sha256(data).hexdigest(), 'metadata': signature(after)}
    return result


def run(memory, scope, profile, installed_workspace, *, args, home, workspace, check_current):
    authorize(scope)
    if (not isinstance(args, list) or len(args) > 16 or any(not isinstance(arg, str) or len(arg) > 4096 for arg in args)
            or not isinstance(home, str) or Path(home).absolute() != Path(profile).absolute()
            or not isinstance(installed_workspace, str) or workspace != installed_workspace):
        raise MemoryUnavailable('Hermes soul requires its configured profile, workspace, and bounded arguments')
    to_stdout = '--stdout' in args
    check = '--check' in args and not to_stdout
    writing = not (to_stdout or check)
    if writing and not {'principal', 'assistant', 'project'} <= set(scope.write):
        raise MemoryUnavailable('Hermes soul publication requires unrestricted owner write access')
    targets = _targets(memory, profile, installed_workspace)
    def resolve_publication(name):
        destinations = _targets(memory, profile, installed_workspace)
        for target in destinations.values():
            if name == str(target):
                return target
        raise MemoryUnavailable('Interrupted Hermes publication belongs to different installed destinations')

    journal = MemoryTransaction(memory.database.parent, resolve_publication)
    journal.journal = memory.database.parent / 'memory-hermes-soul-operation.json'
    with memory._transaction() as connection:
        if journal.journal.exists():
            operation = json.loads(journal.journal.read_text())
            for copy in operation['copies']:
                resolve_publication(copy['path'])
        journal.recover(connection)
        if not connection.in_transaction:
            connection.execute('BEGIN IMMEDIATE')
        previous = _snapshot(targets)
        sources = _collect(memory, scope, connection)
        result = memory._native('hermes_soul_render', sources=sources['declared'])
        if (set(result) != {'soul', 'context', 'size', 'hash'}
                or any(not isinstance(result[name], str) for name in ('soul', 'context', 'hash'))
                or len(json.dumps(result).encode()) > CORPUS_LIMIT):
            raise MemoryUnavailable('Native Hermes soul renderer returns invalid artifacts')
        try:
            check_current()
            if _collect(memory, scope, connection) != sources or _snapshot(_targets(memory, profile, installed_workspace)) != previous:
                raise MemoryConflict('Hermes soul sources or destinations changed during rendering')
        except (MemoryUnavailable, OSError) as error:
            raise MemoryConflict(str(error)) from error
        if to_stdout:
            return {'ok': True, 'status': 0, 'stdout': result['soul']}
        if check:
            current = targets['SOUL.md'].read_text() if targets['SOUL.md'].exists() else ''
            drifted = current != result['soul']
            return {'ok': True, 'status': int(drifted), 'stdout':
                f"SOUL.md   {result['size']} / 19500 chars (Hermes cap 20000)\ndigest    {result['hash']}\n" +
                ('state     STALE: re-render needed\n' if drifted else 'state     current\n')}
        request = 'hermes-soul-' + uuid4().hex
        payload = hashlib.sha256(json.dumps(sources, sort_keys=True).encode()).hexdigest()
        journal.prepare(scope.writer, request, [str(path) for path in targets.values()])
        connection.execute('INSERT INTO operations VALUES (?,?,?,?)',
                           (scope.writer, request, payload, json.dumps({'status': 'unknown'})))
        connection.commit()
        connection.execute('BEGIN IMMEDIATE')
        publish(targets['SOUL.md'], result['soul'].encode())
        publish(targets['.hermes.md'], result['context'].encode())
        connection.execute('UPDATE operations SET receipt=? WHERE writer=? AND request_id=?',
                           (json.dumps({'status': 'committed'}), scope.writer, request))
        journal.flush_publication()
        connection.commit()
        journal.finish()
        return {'ok': True, 'status': 0, 'stdout':
            f"SOUL.md      {result['size']} / 19500 chars\n.hermes.md   {len(result['context'])} chars\ndigest       {result['hash']}\n"}
