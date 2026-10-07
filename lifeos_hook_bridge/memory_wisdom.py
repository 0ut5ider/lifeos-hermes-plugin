# ABOUTME: Admits current Wisdom frame inputs and native observation transformations.
# ABOUTME: Publishes fixed owner frame paths through the existing recovery journal.
from datetime import datetime, timezone
from itertools import islice
import hashlib
import json
import os
from pathlib import Path
import re

from .memory_access import MemoryConflict, MemoryUnavailable
from .memory_sources import authorize, read_markdown, CORPUS_LIMIT, SOURCE_COUNT_LIMIT
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
    if payload['operation'] == 'wisdom_synthesis':
        _authorize_reports(scope)
        return [_report(memory, relative).relative_to(memory.root).as_posix() for relative in payload['outputs']]
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


def _frames(memory, scope, connection, base):
    authorize(scope)
    if base != str(memory.root / 'LIFEOS'):
        raise MemoryUnavailable('Wisdom readers require their installed LifeOS root')
    directory = memory._path(PREFIX.rstrip('/'))
    physical = memory.root.parent / '.config/LIFEOS/USER/MEMORY/WISDOM/FRAMES'
    if directory.is_symlink() or directory.resolve() != physical or directory.exists() and not directory.is_dir():
        raise MemoryUnavailable('The Wisdom frames directory changes its permitted physical path')
    if not directory.exists():
        return {'exists': False, 'sources': []}
    children = list(islice(directory.iterdir(), SOURCE_COUNT_LIMIT + 1))
    if len(children) > SOURCE_COUNT_LIMIT:
        raise MemoryUnavailable('The Wisdom frames directory exceeds its entry limit')
    paths = [str(path) for path in children if path.suffix == '.md']
    return {'exists': True, 'sources': read_markdown(memory, scope, paths, connection=connection)}


def frames(memory, scope, base, *, check_current):
    with memory._transaction() as connection:
        collected = _frames(memory, scope, connection, base)
        check_current()
        if _frames(memory, scope, connection, base) != collected:
            raise MemoryConflict('The Wisdom frames change during collection')
        return {'ok': True, 'sources': [{'path': source['path'], 'content': source['content']}
                                       for source in collected['sources']]}


def _authorize_reports(scope):
    authorize(scope)
    if not {'principal', 'assistant', 'project'} <= set(scope.write):
        raise MemoryUnavailable('Wisdom report publication requires unrestricted owner write access')


def _report(memory, relative):
    if relative not in {'META/frame-health.md', 'PRINCIPLES/verified.md'}:
        raise MemoryUnavailable('Wisdom synthesis changes its fixed report destination')
    target = memory._path('LIFEOS/MEMORY/WISDOM/' + relative)
    physical = memory.root.parent / '.config/LIFEOS/USER/MEMORY/WISDOM' / relative
    if (target.resolve() != physical or target.is_symlink()
            or target.exists() and (not target.is_file() or target.stat().st_uid != os.getuid()
                                    or target.stat().st_nlink != 1 or target.stat().st_size > CORPUS_LIMIT)):
        raise MemoryUnavailable('The Wisdom report changes its permitted physical owner path')
    return target


def _reports(memory, relatives):
    result = {}
    for relative in relatives:
        target = _report(memory, relative)
        result[relative] = hashlib.sha256(target.read_bytes()).hexdigest() if target.exists() else None
    return result


def synthesize(memory, scope, arguments, *, check_current):
    if type(arguments['health']) is not bool or type(arguments['dry_run']) is not bool:
        raise ValueError('Choose native Wisdom health and dry-run modes')
    writing = not arguments['dry_run']
    if writing:
        _authorize_reports(scope)
    with memory._transaction() as connection:
        collected = _frames(memory, scope, connection, arguments['base'])
        relatives = ([] if not writing or not collected['sources'] else ['META/frame-health.md']
                     if arguments['health'] else ['PRINCIPLES/verified.md', 'META/frame-health.md'])
        previous = _reports(memory, relatives)
        rendered = memory._native('wisdom_synthesis',
            sources=[{'path': source['path'], 'content': source['content']} for source in collected['sources']],
            exists=collected['exists'], health=arguments['health'], dry_run=arguments['dry_run'])
        if (set(rendered) != {'stdout', 'writes'} or not isinstance(rendered['stdout'], str)
                or not isinstance(rendered['writes'], list) or len(json.dumps(rendered).encode()) > CORPUS_LIMIT
                or any(not isinstance(write, dict) or set(write) != {'relative', 'content'}
                       or not isinstance(write['relative'], str) or not isinstance(write['content'], str)
                       for write in rendered['writes'])
                or [write['relative'] for write in rendered['writes']] != relatives):
            raise MemoryUnavailable('Native Wisdom synthesis returns invalid reports')
        generated = '\n'.join([rendered['stdout'], *(write['content'] for write in rendered['writes'])])
        if (memory._native('validate_source_batch', contents=[generated])['accepted'] != [True]
                or memory._filter_history(connection, scope, generated,
                    datetime.now(timezone.utc).isoformat(), reviewed=True)['excluded']):
            raise MemoryUnavailable('The generated Wisdom reports are excluded by current memory policy')
        check_current()
        if _frames(memory, scope, connection, arguments['base']) != collected or _reports(memory, relatives) != previous:
            raise MemoryConflict('The Wisdom synthesis inputs or reports change during rendering')
    if not writing:
        return {'ok': True, 'stdout': rendered['stdout']}
    signature = hashlib.sha256(json.dumps(collected, sort_keys=True).encode()).hexdigest()
    payload = {'operation': 'wisdom_synthesis', **arguments, 'sources_signature': signature, 'outputs': relatives}

    def apply(connection):
        try:
            check_current()
            if _frames(memory, scope, connection, arguments['base']) != collected or _reports(memory, relatives) != previous:
                raise MemoryConflict('The Wisdom synthesis inputs or reports change before publication')
        except (MemoryUnavailable, OSError) as error:
            raise MemoryConflict(str(error)) from error
        for write in rendered['writes']:
            publish(_report(memory, write['relative']), write['content'].encode())
        return {'status': 'committed', 'stdout': rendered['stdout']}

    receipt = memory._operation(scope, arguments['request_id'], payload, apply)
    return {'ok': receipt['status'] == 'committed', 'stdout': receipt.get('stdout'), 'receipt': receipt}
