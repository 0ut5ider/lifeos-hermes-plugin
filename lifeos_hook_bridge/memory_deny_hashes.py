# ABOUTME: Supplies admitted current corpus bytes to native private-token hashing.
# ABOUTME: Journals fixed hash and environment publication without returning salt or environment bytes.
import json
import os
from pathlib import Path
from uuid import uuid4

from .memory_access import MemoryUnavailable, MemoryConflict
from .memory_evidence import _signature
from .memory_sources import (DENY_SOURCE_FILES, SOURCE_LIMIT, SOURCE_COUNT_LIMIT, CORPUS_LIMIT,
    _text_source, _admit, json_projection, authorize)
from .memory_transaction import publish


OUTPUT = 'LIFEOS/USER/SECURITY/DENY_HASHES.json'
OPERATOR = 'LIFEOS/USER/CONFIG/denyhash-allowlist.txt'
SYSTEM_PUBLICATIONS = frozenset({'.env'})


def _target(memory, relative):
    target = memory._publication_path(relative)
    physical = (memory.root / relative if relative == '.env' else
                memory.root.parent / '.config/LIFEOS/USER/SECURITY/DENY_HASHES.json')
    limit = SOURCE_LIMIT if relative == '.env' else CORPUS_LIMIT
    if (target.resolve() != physical.absolute() or target.is_symlink()
            or target.exists() and (not target.is_file() or target.stat().st_uid != os.getuid()
                                    or target.stat().st_size > limit or target.stat().st_nlink != 1)):
        raise MemoryUnavailable('Deny hash publication changes its fixed owner destination')
    return target


def _marker(memory):
    marker = memory.root / 'skills/_LIFEOS'
    if marker.is_symlink() or marker.resolve() != marker.absolute():
        raise MemoryUnavailable('The private hash consumer changes its installed path')
    return marker.exists()


def _collect(memory, scope, connection, writing):
    authorize(scope)
    relatives = set(DENY_SOURCE_FILES)
    directory = memory._path('LIFEOS/MEMORY/_NETWORK')
    physical = memory.root.parent / '.config/LIFEOS/USER/MEMORY/_NETWORK'
    if directory.resolve() != physical or directory.is_symlink() or directory.exists() and not directory.is_dir():
        raise MemoryUnavailable('The deny corpus directory changes its permitted physical path')
    if directory.exists():
        children = list(directory.iterdir())
        if len(children) > SOURCE_COUNT_LIMIT:
            raise MemoryUnavailable('The network snapshot directory exceeds its source count limit')
        snapshots = sorted(child.name for child in children if child.name.startswith('topology-snapshot-')
                           and child.name.endswith('.md'))
        if snapshots:
            relatives.add('LIFEOS/MEMORY/_NETWORK/' + snapshots[-1])
    rows = []
    total = 0
    for relative in sorted(relatives):
        path = memory.root / relative
        if not path.exists() and not path.is_symlink():
            continue
        source, timestamp = _text_source(memory, scope, str(path), suffix=Path(relative).suffix, deny_hashes=True)
        if path.stat().st_uid != os.getuid():
            raise MemoryUnavailable('The deny corpus needs owner sources')
        total += len(source['content'].encode())
        if total > CORPUS_LIMIT:
            raise MemoryUnavailable('The deny corpus exceeds its transport limit')
        projection = json_projection(source['content']) if relative.endswith('.json') else source['content']
        rows.append((source, timestamp, projection))
    valid = memory._native('validate_source_batch', contents=[(projection or '') + '\n' + source['path']
        for source, _, projection in rows])['accepted'] if rows else []
    admitted = [source for (source, timestamp, projection), accepted in zip(rows, valid, strict=True)
        if projection is not None and accepted is True and not _admit(memory, connection, scope,
            source['content'], source['relative'], timestamp, projection=projection)['excluded']]
    environment = None
    if writing:
        path = _target(memory, '.env')
        environment = (_text_source(memory, scope, str(path), suffix=path.suffix, interview_setup=True, preserve_newlines=True)[0]['content']
                       if path.exists() else '')
    return {'sources': admitted, 'raw_signature': _signature([row[0] for row in rows]),
            'environment': environment, 'consumer_present': _marker(memory)}


def publication_paths(memory, scope):
    authorize(scope)
    if not {'principal', 'assistant', 'project'} <= set(scope.write):
        raise MemoryUnavailable('Deny hash publication requires unrestricted owner write access')
    for relative in ('.env', OUTPUT):
        _target(memory, relative)
    return ['.env', OUTPUT]


def run(memory, scope, *, args, check_current):
    authorize(scope)
    if not isinstance(args, list) or len(args) > 16 or any(not isinstance(arg, str) or len(arg) > 4096 for arg in args):
        raise ValueError('Deny hashing requires bounded native arguments')
    dry_run = '--dry-run' in args
    show_tokens = '--show-tokens' in args
    writing = not dry_run and _marker(memory)
    if writing:
        publication_paths(memory, scope)
    with memory._transaction() as connection:
        collected = _collect(memory, scope, connection, writing)
        sources = [source['content'] for source in collected['sources'] if source['relative'] != OPERATOR]
        operator = next((source['content'] for source in collected['sources'] if source['relative'] == OPERATOR), '')
        environment = memory._native('deny_hash_environment', content=collected['environment']) if writing else None
        if environment is not None and (set(environment) != {'content', 'salt', 'generated'}
                or not isinstance(environment['content'], str) or not isinstance(environment['salt'], str)
                or type(environment['generated']) is not bool or len(environment['content'].encode()) > SOURCE_LIMIT):
            raise MemoryUnavailable('Native deny salt generation returns invalid environment bytes')
        result = memory._native('deny_hashes', sources=sources, operator=operator,
                                salt=environment['salt'] if environment is not None else None)
        if (set(result) != {'tokens', 'payload'} or not isinstance(result['tokens'], list)
                or any(not isinstance(token, str) for token in result['tokens'])
                or len(json.dumps(result).encode()) > CORPUS_LIMIT
                or writing and not isinstance(result['payload'], dict)):
            raise MemoryUnavailable('Native deny hashing returns invalid artifacts')
        check_current()
        if _collect(memory, scope, connection, writing) != collected:
            raise MemoryConflict('Deny hash sources changed during rendering')
    stdout = f"[DeriveDenyHashes] {len(sources)} corpus files -> {len(result['tokens'])} distinctive tokens\n"
    if show_tokens:
        stdout += '[DeriveDenyHashes] --show-tokens (LOCAL review, NOT written to disk):\n'
        stdout += ', '.join(result['tokens']) + '\n'
    if not writing:
        stdout += ('[DeriveDenyHashes] --dry-run: nothing written\n' if dry_run else
                   '[DeriveDenyHashes] skills/_LIFEOS absent (public install): skipping hash write\n')
        return {'ok': True, 'stdout': stdout}
    signature = _signature(collected)

    def apply(connection):
        try:
            current = _collect(memory, scope, connection, True)
            check_current()
            publication_paths(memory, scope)
        except (MemoryUnavailable, OSError) as error:
            raise MemoryConflict('Deny hash inputs or authority changed before publication') from error
        if _signature(current) != signature:
            raise MemoryConflict('Deny hash inputs changed before publication')
        publish(_target(memory, '.env'), environment['content'].encode())
        publish(_target(memory, OUTPUT), (json.dumps(result['payload'], separators=(',', ':')) + '\n').encode())
        return {'status': 'committed', 'artifacts': 2}

    receipt = memory._operation(scope, 'deny-hashes-' + uuid4().hex,
                                {'operation': 'deny_hashes', 'source_signature': signature}, apply)
    if receipt['status'] != 'committed':
        return {'ok': False, 'stdout': ''}
    if environment['generated']:
        stdout += '[DeriveDenyHashes] generated DENYLIST_SALT in the installed environment\n'
    stdout += f"[DeriveDenyHashes] wrote {len(result['tokens'])} salted hashes (no plaintext)\n"
    return {'ok': True, 'stdout': stdout}
