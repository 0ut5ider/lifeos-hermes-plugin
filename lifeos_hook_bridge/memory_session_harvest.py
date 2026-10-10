# ABOUTME: Admits current Hermes conversation transcripts for native session consolidation.
# ABOUTME: Rechecks owner authority and journals private learning and review-queue publication.
from dataclasses import replace
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import stat

from .memory_access import MemoryConflict, MemoryUnavailable
from .memory_context import parse_context
from .memory_sources import authorize, SOURCE_LIMIT, SOURCE_COUNT_LIMIT, CORPUS_LIMIT
from .memory_transaction import publish


TRANSCRIPTS = 'LIFEOS/MEMORY/STATE/hermes-transcripts'


def _signature(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def _target(memory, relative):
    if re.fullmatch(r'LIFEOS/MEMORY/(?:LEARNING/(?:SYSTEM|ALGORITHM)/\d{4}-\d{2}/[A-Za-z0-9._-]+\.md'
                    r'|KNOWLEDGE/_harvest-queue/[A-Za-z0-9._-]+\.json)', relative) is None:
        raise MemoryUnavailable('Session consolidation requires a fixed native learning or review destination')
    path = memory._publication_path(relative)
    physical = memory.root.parent / '.config/LIFEOS/USER' / Path(relative).relative_to('LIFEOS')
    if (path.resolve() != physical or path.is_symlink()
            or path.exists() and (not path.is_file() or path.stat().st_uid != os.getuid()
                                  or path.stat().st_nlink != 1 or path.stat().st_size > SOURCE_LIMIT)):
        raise MemoryUnavailable('Session consolidation changes its fixed owner destination')
    return path


def _read_private(path, limit):
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    with os.fdopen(descriptor, 'rb') as stream:
        before = os.fstat(stream.fileno())
        if (not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or before.st_uid != os.getuid()
                or before.st_mode & 0o077 or before.st_size > limit):
            raise MemoryUnavailable('Session consolidation requires bounded private owner files')
        data = stream.read(limit + 1)
        stamp = lambda info: (info.st_dev, info.st_ino, info.st_mtime_ns, info.st_size, info.st_mode, info.st_nlink)
        after = os.fstat(stream.fileno())
        if len(data) > limit or stamp(before) != stamp(after) or stamp(after) != stamp(path.lstat()):
            raise MemoryUnavailable('Session consolidation sources change during collection')
    return data, after


def _collect(memory, scope, configuration, profile, options, connection, session_scope):
    authorize(scope)
    directory = memory._path(TRANSCRIPTS)
    physical = memory.root.parent / '.config/LIFEOS/USER/MEMORY/STATE/hermes-transcripts'
    if directory.resolve() != physical or directory.is_symlink():
        raise MemoryUnavailable('Session consolidation changes its transcript directory')
    state_path = profile / 'lifeos-memory-contexts.json'
    if not state_path.exists() and not state_path.is_symlink():
        return {'sessions':[], 'source_revision':None, 'states_revision':None}
    state_bytes, _ = _read_private(state_path, CORPUS_LIMIT)
    states = json.loads(state_bytes)
    if not isinstance(states, dict):
        raise MemoryUnavailable('Session consolidation requires admitted conversation states')
    paths = list(directory.glob('*.jsonl')) if directory.exists() else []
    if len(paths) > SOURCE_COUNT_LIMIT:
        raise MemoryUnavailable('Session consolidation exceeds its transcript count limit')
    files = []
    permitted = {}
    total = 0
    for path in paths:
        if re.fullmatch(r'[A-Za-z0-9._-]{1,180}\.jsonl', path.name) is None:
            raise MemoryUnavailable('Session consolidation requires a bounded native session filename')
        data, info = _read_private(path, SOURCE_LIMIT)
        state = states.get(path.stem)
        if not isinstance(state, dict) or not isinstance(state.get('context'), dict):
            continue
        try:
            context = parse_context(state['context'])
            key = _signature({**state['context'], 'session_id':''})
            if key not in permitted:
                admitted = session_scope(replace(context, session_id=''))
                permitted[key] = admitted
            admitted = permitted[key]
        except (ValueError, MemoryUnavailable):
            continue
        if (context.session_id != path.stem or context.visibility != 'private'
                or context.participants != (configuration['principal'],)
                or admitted.reason or admitted.principal != configuration['principal']
                or state.get('scope') != admitted.signature):
            continue
        lines = []
        for line in data.decode('utf-8').splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            if (not isinstance(row, dict) or row.get('sessionId') != context.session_id
                    or row.get('type') not in ('user', 'assistant')
                    or not isinstance(row.get('message'), dict)
                    or row['message'].get('role') != row['type'] or not isinstance(row.get('timestamp'), str)):
                continue
            filtered = memory._filter_history(connection, scope, line, row['timestamp'])
            if not filtered['excluded']:
                lines.append(filtered['content'])
        total += len(data)
        if total > CORPUS_LIMIT:
            raise MemoryUnavailable('Session consolidation exceeds its transcript byte limit')
        files.append({'path':str(path), 'content':'\n'.join(lines), 'modified':info.st_mtime_ns,
                      'source_digest':hashlib.sha256(data).hexdigest()})
    files.sort(key=lambda row:(row['modified'], row['path']), reverse=True)
    if options['session']:
        files = [row for row in files if options['session'] in Path(row['path']).name][:1]
    elif options['all']:
        cutoff = int((datetime.now(timezone.utc) - timedelta(days=7)).timestamp() * 10**9)
        files = [row for row in files if row['modified'] > cutoff]
    else:
        files = files[:options['recent']]
    return {'sessions':files, 'source_revision':_signature(files),
            'states_revision':hashlib.sha256(state_bytes).hexdigest()}


def publication_paths(memory, scope, payload):
    authorize(scope)
    if not {'principal', 'assistant', 'project'} <= set(scope.write):
        raise MemoryUnavailable('Session consolidation requires unrestricted owner write access')
    files = payload.get('files')
    if (not isinstance(files, list) or len(files) > SOURCE_COUNT_LIMIT
            or len(set(files)) != len(files) or any(not isinstance(path, str) for path in files)):
        raise MemoryUnavailable('Session consolidation requires bounded unique publication paths')
    for relative in files:
        _target(memory, relative)
    return files


def run(memory, scope, configuration, profile, *, recent, all, session, projects_dir, dry_run, mine,
        check_current, session_scope):
    if (type(recent) is not int or not 1 <= recent <= 100 or any(type(value) is not bool for value in (all, dry_run, mine))
            or session is not None and (not isinstance(session, str) or re.fullmatch(r'[A-Za-z0-9._-]{1,180}', session) is None)
            or projects_dir is not None):
        raise ValueError('Managed consolidation uses current Hermes transcripts and bounded native selection options')
    if not dry_run and not {'principal', 'assistant', 'project'} <= set(scope.write):
        raise MemoryUnavailable('Session consolidation requires unrestricted owner write access')
    options = {'recent':recent, 'all':all, 'session':session}
    with memory._transaction() as connection:
        snapshot = _collect(memory, scope, configuration, profile, options, connection, session_scope)
        result = memory._native('session_harvest', sessions=[{'path':row['path'], 'content':row['content']}
            for row in snapshot['sessions']], mine=mine, now=datetime.now(timezone.utc).isoformat())
        if (set(result) != {'count','writes'} or type(result['count']) is not int or result['count'] < 0
                or not isinstance(result['writes'], list) or len(result['writes']) > SOURCE_COUNT_LIMIT
                or any(not isinstance(row, dict) or set(row) != {'file','content'}
                       or not isinstance(row['file'], str) or not isinstance(row['content'], str)
                       or len(row['content'].encode()) > SOURCE_LIMIT for row in result['writes'])):
            raise MemoryUnavailable('Native session consolidation changes its publication contract')
        if _collect(memory, scope, configuration, profile, options, connection, session_scope) != snapshot:
            raise MemoryConflict('Session transcripts change during native consolidation')
        check_current()
    files = list(dict.fromkeys(row['file'] for row in result['writes']))
    if dry_run:
        return {'ok':True, 'count':result['count'], 'sessions':len(snapshot['sessions']), 'files':[], 'status':'preview'}
    payload = {'operation':'session_harvest', 'source_revision':snapshot['source_revision'],
               'states_revision':snapshot['states_revision'], 'mine':mine, 'files':files, 'scope':scope.signature}

    def commit(connection):
        if _collect(memory, scope, configuration, profile, options, connection, session_scope) != snapshot:
            raise MemoryConflict('Session transcripts change before consolidation publication')
        check_current()
        publication_paths(memory, scope, payload)
        saved = []
        for row in result['writes']:
            path = _target(memory, row['file'])
            if not path.exists():
                if memory._filter_history(connection, scope, row['content'],
                        datetime.now(timezone.utc).isoformat(), reviewed=True)['excluded']:
                    raise MemoryUnavailable('Native session consolidation contains retired content')
                check_current()
                publish(path, row['content'].encode())
                saved.append(row['file'])
        check_current()
        return {'status':'committed' if saved else 'unchanged', 'files':saved,
                'count':result['count'], 'sessions':len(snapshot['sessions'])}

    receipt = memory._operation(scope, 'session-harvest-' + _signature(payload), payload, commit)
    return {'ok':receipt['status'] in ('committed','unchanged'), 'count':receipt.get('count', 0),
            'sessions':receipt.get('sessions', 0), 'files':receipt.get('files', []), 'status':receipt['status']}
