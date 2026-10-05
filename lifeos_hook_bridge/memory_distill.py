# ABOUTME: Supplies current registered notes to the native Knowledge distill reader.
# ABOUTME: Admits fixed configuration and tracking inputs under current owner authority.
import json
import os
from pathlib import Path
import re
from uuid import uuid4

from .memory_access import MemoryUnavailable, MemoryConflict, _now
from .memory_canonical import corpus
from .memory_sources import authorize, json_projection, CORPUS_LIMIT
from .memory_transaction import publish


STATE = 'LIFEOS/MEMORY/STATE/distill.json'
CONFIG = 'LIFEOS/USER/CUSTOMIZATIONS/SKILLS/Cortex/DistillConfig.json'


def _json(memory, scope, connection, relative):
    path = memory._path(relative)
    boundary = 'LIFEOS/USER' if relative.startswith('LIFEOS/USER/') else 'LIFEOS'
    physical = memory.root.parent / '.config/LIFEOS/USER' / Path(relative).relative_to(boundary)
    if path.is_symlink() or path.resolve() != physical:
        raise MemoryUnavailable('Distill input changes its fixed owner path')
    if not path.exists():
        return None
    info = path.stat()
    if not path.is_file() or info.st_uid != os.getuid() or info.st_nlink != 1 or info.st_size > CORPUS_LIMIT:
        raise MemoryUnavailable('Distill input requires a bounded regular owner file')
    content = path.read_text(encoding='utf-8')
    projection = json_projection(content)
    if (projection is None or memory._native('validate_source_batch', contents=[projection])['accepted'] != [True]
            or memory._filter_history(connection, scope, projection, _now(), reviewed=True)['excluded']):
        raise MemoryUnavailable('Distill input is excluded by current policy')
    value = json.loads(content)
    if not isinstance(value, dict):
        raise MemoryUnavailable('Distill input requires a native object')
    return value


def _collect(memory, scope, connection):
    authorize(scope)
    notes = corpus(memory, scope, str(memory.root / 'LIFEOS/MEMORY'), connection=connection)
    state = _json(memory, scope, connection, STATE)
    if state is not None and (set(state) != {'schema_version', 'surfaced_slugs', 'item_hashes', 'last_run'}
            or state['schema_version'] != 1 or not isinstance(state['surfaced_slugs'], dict)
            or not isinstance(state['item_hashes'], dict)
            or state['last_run'] is not None and not isinstance(state['last_run'], str)
            or any(not isinstance(value, str) for field in ('surfaced_slugs', 'item_hashes') for value in state[field].values())):
        raise MemoryUnavailable('Distill tracking requires its native schema')
    config = _json(memory, scope, connection, CONFIG)
    if config is not None and (set(config) - {'contentRepo', 'contentLabel', 'maxIssues', 'maxUpgrades', 'maxDigestItems', 'windowDays'}
            or any(not isinstance(config[key], str) for key in ('contentRepo', 'contentLabel') if key in config)
            or any(type(config[key]) is not int or not 0 <= config[key] <= 36500
                   for key in ('maxIssues', 'maxUpgrades', 'maxDigestItems', 'windowDays') if key in config)):
        raise MemoryUnavailable('Distill settings require bounded native fields')
    return {'sources': [{'path': path, 'content': record['content']}
                       for path, record in zip(notes['files'], notes['records'], strict=True)], 'state': state, 'config': config}


def read(memory, scope, args, *, check_current):
    if (not isinstance(args, list) or not args or args[0] not in {'gather', 'status'} or len(args) > 5
            or any(not isinstance(arg, str) or len(arg) > 64 for arg in args)):
        raise ValueError('Choose supported native distill read arguments')
    with memory._transaction() as connection:
        inputs = _collect(memory, scope, connection)
        value = memory._native('distill_read', args=args, **inputs)['value']
        check_current()
        if _collect(memory, scope, connection) != inputs:
            raise MemoryConflict('Distill inputs changed during collection')
        result = {'ok': True, 'value': value}
        if len(json.dumps(result).encode()) > CORPUS_LIMIT:
            raise MemoryUnavailable('Distill read exceeds its transport limit')
        return result


def publication_paths(memory, scope):
    authorize(scope)
    if not {'principal', 'assistant', 'project'} <= set(scope.write):
        raise MemoryUnavailable('Distill marking requires unrestricted owner write access')
    path = memory._publication_path(STATE)
    physical = memory.root.parent / '.config/LIFEOS/USER/MEMORY/STATE/distill.json'
    if (path.is_symlink() or path.resolve() != physical or path.exists() and
            (not path.is_file() or path.stat().st_uid != os.getuid() or path.stat().st_nlink != 1
             or path.stat().st_size > CORPUS_LIMIT)):
        raise MemoryUnavailable('Distill marking changes its fixed owner destination')
    return [STATE]


def _digest(memory, scope, connection, path):
    if not isinstance(path, str):
        raise ValueError('Choose an installed distill digest')
    try:
        relative = Path(path).relative_to(memory.root).as_posix()
    except ValueError as error:
        raise MemoryUnavailable('The digest leaves its installed source directory') from error
    if re.fullmatch(r'LIFEOS/MEMORY/DIGESTS/\d{4}-\d{2}-\d{2}-distill\.md', relative) is None:
        raise MemoryUnavailable('Choose a native dated distill digest')
    source = memory._path(relative)
    physical = memory.root.parent / '.config/LIFEOS/USER' / Path(relative).relative_to('LIFEOS')
    if (source.is_symlink() or source.resolve() != physical or not source.is_file()
            or source.stat().st_uid != os.getuid() or source.stat().st_nlink != 1 or source.stat().st_size > 256 * 1024):
        raise MemoryUnavailable('Distill marking needs a bounded regular owner digest')
    content = source.read_text(encoding='utf-8')
    if (memory._native('validate_source_batch', contents=[content])['accepted'] != [True]
            or memory._filter_history(connection, scope, content, _now(), reviewed=True)['excluded']):
        raise MemoryUnavailable('The digest is excluded by current policy')
    return content


def mark(memory, scope, path, *, check_current):
    publication_paths(memory, scope)
    with memory._transaction() as connection:
        inputs = _collect(memory, scope, connection)
        content = _digest(memory, scope, connection, path)
        target = memory._publication_path(STATE)
        before = target.read_bytes() if target.exists() else None
        result = memory._native('distill_mark', content=content, state=inputs['state'])
        check_current()
        if _collect(memory, scope, connection) != inputs or _digest(memory, scope, connection, path) != content:
            raise MemoryConflict('Distill marking inputs changed during collection')

    def apply(connection):
        try:
            check_current()
            publication_paths(memory, scope)
            current = _collect(memory, scope, connection)
            current_digest = _digest(memory, scope, connection, path)
            current_bytes = target.read_bytes() if target.exists() else None
        except (MemoryUnavailable, OSError) as error:
            raise MemoryConflict('Distill marking authority or inputs changed before publication') from error
        if current != inputs or current_digest != content or current_bytes != before:
            raise MemoryConflict('Distill marking preserves later input and destination changes')
        publish(target, json.dumps(result['state'], ensure_ascii=False, indent=2).encode())
        return {'status': 'committed', 'counts': result['counts']}

    receipt = memory._operation(scope, 'distill-mark-' + uuid4().hex, {'operation': 'distill_mark'}, apply)
    return {'ok': receipt['status'] == 'committed', 'value': receipt.get('counts')}
