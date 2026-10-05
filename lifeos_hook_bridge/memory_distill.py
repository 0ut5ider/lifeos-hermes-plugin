# ABOUTME: Supplies current registered notes to the native Knowledge distill reader.
# ABOUTME: Admits fixed configuration and tracking inputs under current owner authority.
import json
import os
from pathlib import Path

from .memory_access import MemoryUnavailable, MemoryConflict, _now
from .memory_canonical import corpus
from .memory_sources import authorize, json_projection, CORPUS_LIMIT


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
