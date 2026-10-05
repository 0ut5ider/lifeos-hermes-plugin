# ABOUTME: Admits current Wisdom frame inputs and native observation transformations.
# ABOUTME: Publishes fixed owner frame paths through the existing recovery journal.
from datetime import datetime, timezone
import os
from pathlib import Path
import re

from .memory_access import MemoryConflict, MemoryUnavailable
from .memory_sources import authorize, read_markdown, CORPUS_LIMIT
from .memory_transaction import publish


TYPES = frozenset(('principle', 'contextual-rule', 'prediction', 'anti-pattern', 'evolution'))
PREFIX = 'LIFEOS/MEMORY/WISDOM/FRAMES/'


def _target(memory, scope, arguments):
    authorize(scope)
    if not {'principal', 'assistant', 'project'} <= set(scope.write):
        raise MemoryUnavailable('Wisdom updates require unrestricted owner write access')
    domain = arguments['domain']
    if not isinstance(domain, str) or re.fullmatch(r'[a-z][a-z0-9-]{0,127}', domain) is None:
        raise ValueError('Choose one bounded Wisdom domain name')
    relative = PREFIX + domain + '.md'
    target = memory._path(relative)
    if arguments['path'] != str(memory.root / relative):
        raise MemoryUnavailable('Wisdom updates require their fixed installed frame path')
    physical = memory.root.parent / '.config/LIFEOS/USER/MEMORY/WISDOM/FRAMES' / (domain + '.md')
    if (target.resolve() != physical or target.is_symlink()
            or target.exists() and (not target.is_file() or target.stat().st_uid != os.getuid()
                                    or target.stat().st_nlink != 1 or target.stat().st_size > 256 * 1024)):
        raise MemoryUnavailable('The Wisdom frame changes its permitted physical owner path')
    return relative, target


def publication_paths(memory, scope, payload):
    relative, _ = _target(memory, scope, payload)
    return [relative]


def _collect(memory, scope, connection, arguments):
    _, target = _target(memory, scope, arguments)
    if not target.exists():
        return None
    selected = read_markdown(memory, scope, [str(target)], connection=connection)
    if len(selected) != 1:
        raise MemoryUnavailable('The current Wisdom frame is excluded by memory policy')
    return selected[0]


def update_frame(memory, scope, arguments, *, check_current):
    relative, target = _target(memory, scope, arguments)
    observation, kind = arguments['observation'], arguments['type']
    if (not isinstance(observation, str) or not observation.strip() or len(observation.encode()) > 64 * 1024
            or not isinstance(kind, str) or kind not in TYPES):
        raise ValueError('Choose a bounded observation and supported Wisdom update type')
    payload = {'operation': 'wisdom_frame_update', **arguments}
    projection = '\n'.join((arguments['domain'], observation))
    def admit_observation(connection):
        valid = memory._native('validate_source_batch', contents=[projection])['accepted']
        if valid != [True] or memory._filter_history(connection, scope, projection,
                datetime.now(timezone.utc).isoformat(), reviewed=True)['excluded']:
            raise MemoryUnavailable('The Wisdom observation is excluded by current memory policy')

    with memory._transaction() as connection:
        initial = _collect(memory, scope, connection, arguments)
        admit_observation(connection)
        check_current()

    def apply(connection):
        collected = _collect(memory, scope, connection, arguments)
        if collected != initial:
            raise MemoryConflict('The Wisdom frame changes before native rendering')
        admit_observation(connection)
        rendered = memory._native('wisdom_frame_update', domain=arguments['domain'], observation=observation,
                                 type=kind, path=str(target), previous=collected['content'] if collected else None)
        result, content = rendered.get('result'), rendered.get('content')
        if (set(rendered) != {'result', 'content'} or not isinstance(content, str)
                or len(content.encode()) > 256 * 1024 or not isinstance(result, dict)
                or set(result) != {'success', 'domain', 'type', 'message', 'framePath'}
                or result['success'] is not True or result['domain'] != arguments['domain']
                or result['type'] != kind or result['framePath'] != str(target)
                or not isinstance(result['message'], str) or len(result['message'].encode()) > CORPUS_LIMIT):
            raise MemoryUnavailable('Native Wisdom rendering returns invalid artifacts')
        generated = content + '\n' + result['message']
        if (memory._native('validate_source_batch', contents=[generated])['accepted'] != [True]
                or memory._filter_history(connection, scope, generated,
                    datetime.now(timezone.utc).isoformat(), reviewed=True)['excluded']):
            raise MemoryUnavailable('The generated Wisdom frame is excluded by current memory policy')
        try:
            check_current()
            if _collect(memory, scope, connection, arguments) != collected:
                raise MemoryConflict('The Wisdom frame changes during native rendering')
        except (MemoryUnavailable, OSError) as error:
            raise MemoryConflict(str(error)) from error
        positions = []
        for row in connection.execute("SELECT * FROM records WHERE path=? AND status='active'", (relative,)):
            original = memory._content(row)
            position = content.find(original)
            if position < 0 or content.find(original, position + 1) >= 0:
                raise MemoryUnavailable('The Wisdom update cannot preserve a registered fact position')
            positions.append((position, row['id']))
        publish(target, content.encode())
        for position, identifier in positions:
            connection.execute('UPDATE records SET position=? WHERE id=?', (position, identifier))
        return {'status': 'committed', 'result': result}

    receipt = memory._operation(scope, arguments['request_id'], payload, apply)
    return {'ok': receipt['status'] == 'committed', 'result': receipt.get('result'), 'receipt': receipt}
