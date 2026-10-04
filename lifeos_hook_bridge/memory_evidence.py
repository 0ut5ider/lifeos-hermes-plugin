# ABOUTME: Supplies admitted decoded JSON inputs to the native state evidence calculations.
# ABOUTME: Checks current sources and authority before delivery or recoverable cache publication.
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
from uuid import uuid4

from .memory_access import MemoryConflict, MemoryUnavailable, _digest
from .memory_sources import (CORPUS_LIMIT, SOURCE_COUNT_LIMIT, EVIDENCE_DIRECTORIES,
                             _text_source, _admit, authorize, is_evidence_source, json_projection)
from .memory_transaction import publish


DOMAINS = frozenset({'health', 'activity', 'work', 'money'})
OUTPUT = 'LIFEOS/USER/CACHE/state-evidence.json'
FILES = {'health': {'LIFEOS/USER/HEALTH/current.json'}, 'activity': set(),
         'work': {'LIFEOS/MEMORY/STATE/work.json'}, 'money': {'LIFEOS/USER/FINANCES/expenses.json'}}


def _now():
    return datetime.now(timezone.utc).isoformat()


def _request(scope, domain, now):
    authorize(scope)
    if domain is not None and (not isinstance(domain, str) or domain not in DOMAINS):
        raise ValueError('Choose a native state evidence domain')
    if not isinstance(now, str) or len(now) > 64 or datetime.fromisoformat(now).tzinfo is None:
        raise ValueError('State evidence requires a bounded dated calculation')


def _cache(memory, path):
    if path != str(memory.root / OUTPUT):
        raise MemoryUnavailable('State evidence can only use its installed cache destination')
    target = memory._path(OUTPUT)
    physical = memory.root.parent / '.config/LIFEOS/USER/CACHE/state-evidence.json'
    if (target.resolve() != physical or target.is_symlink()
            or target.exists() and (not target.is_file() or target.stat().st_uid != os.getuid()
                                    or target.stat().st_size > CORPUS_LIMIT)):
        raise MemoryUnavailable('The evidence cache changes its permitted owner destination')
    return target


def _collect(memory, scope, connection, domain):
    authorize(scope)
    relatives = set().union(*(FILES[name] for name in DOMAINS if domain is None or name == domain))
    for directory in sorted(EVIDENCE_DIRECTORIES):
        selected = 'health' if '/HEALTH/' in directory else 'activity'
        if domain is not None and domain != selected:
            continue
        path = memory._path(directory)
        physical = memory.root.parent / '.config/LIFEOS/USER' / Path(directory).relative_to('LIFEOS/USER')
        if path.resolve() != physical or path.is_symlink() or path.exists() and not path.is_dir():
            raise MemoryUnavailable('An evidence day directory changes its permitted physical path')
        if path.exists():
            relatives.update(str(child.relative_to(memory.root)) for child in path.iterdir()
                             if is_evidence_source(str(child.relative_to(memory.root))))
    if len(relatives) > SOURCE_COUNT_LIMIT:
        raise MemoryUnavailable('The evidence sources exceed their count limit')
    collected = []
    total = 0
    for relative in sorted(relatives):
        path = memory.root / relative
        if not path.exists() and not path.is_symlink():
            continue
        source, timestamp = _text_source(memory, scope, str(path), suffix='.json', evidence=True)
        total += len(source['content'].encode())
        if total > CORPUS_LIMIT:
            raise MemoryUnavailable('The evidence sources exceed their corpus limit')
        projection = json_projection(source['content'])
        if projection is not None:
            collected.append((source, timestamp, projection))
    accepted = memory._native('validate_source_batch',
        contents=[projection + '\n' + source['path'] for source, _, projection in collected])['accepted'] if collected else []
    sources = [source for (source, timestamp, projection), valid in zip(collected, accepted, strict=True)
        if valid is True and not _admit(memory, connection, scope, source['content'], source['relative'],
                                       timestamp, projection=projection)['excluded']]
    commits = None
    if domain is None or domain == 'work':
        result = subprocess.run(['git', '--no-pager', '-C', str(memory.root), 'log', '--no-show-signature',
            '--since=14 days ago', '--format=%ad', '--date=short'], capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            if len(result.stdout.encode()) > CORPUS_LIMIT:
                raise MemoryUnavailable('The evidence Git dates exceed their corpus limit')
            commits = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    return {'sources': sources, 'gitCommits': commits}


def _signature(collected):
    return _digest(json.dumps(collected, sort_keys=True))


def _render(memory, collected, domain, now):
    result = memory._native('state_evidence', domain=domain, now=now, **collected)
    if (set(result) != {'value', 'content'} or not isinstance(result['value'], dict)
            or not isinstance(result['content'], str) or len(json.dumps(result).encode()) > CORPUS_LIMIT
            or domain is None and (result['value'].get('schema') != 1
                                   or set(result['value'].get('domains', {})) != DOMAINS)):
        raise MemoryUnavailable('Native state evidence returns an invalid result')
    return result


def read(memory, scope, domain, now, *, check_current):
    _request(scope, domain, now)
    with memory._transaction() as connection:
        collected = _collect(memory, scope, connection, domain)
        result = _render(memory, collected, domain, now)
        if _collect(memory, scope, connection, domain) != collected:
            raise MemoryUnavailable('The evidence sources changed during calculation')
        check_current()
        return {'ok': True, 'value': result['value']}


def cache_read(memory, scope, path, *, check_current):
    authorize(scope)
    with memory._transaction() as connection:
        target = _cache(memory, path)
        if not target.exists():
            check_current()
            return {'ok': True, 'value': None}
        collected = _collect(memory, scope, connection, None)
        result = _render(memory, collected, None, _now())
        if _collect(memory, scope, connection, None) != collected:
            raise MemoryUnavailable('The evidence sources changed during current cache rendering')
        _cache(memory, path)
        check_current()
        return {'ok': True, 'value': result['value']}


def publication_paths(memory, scope):
    authorize(scope)
    if not {'principal', 'assistant', 'project'} <= set(scope.write):
        raise MemoryUnavailable('Evidence cache publication requires unrestricted owner write access')
    _cache(memory, str(memory.root / OUTPUT))
    return [OUTPUT]


def cache_write(memory, scope, path, evidence, *, check_current):
    publication_paths(memory, scope)
    _cache(memory, path)
    if not isinstance(evidence, dict) or len(json.dumps(evidence).encode()) > CORPUS_LIMIT:
        raise ValueError('Choose a bounded native state evidence payload')
    now = evidence.get('generated_at')
    _request(scope, None, now)
    with memory._transaction() as connection:
        collected = _collect(memory, scope, connection, None)
        signature = _signature(collected)

    def apply(connection):
        current = _collect(memory, scope, connection, None)
        if _signature(current) != signature:
            raise MemoryConflict('The evidence sources changed before cache rendering')
        result = _render(memory, current, None, now)
        if result['value'] != evidence:
            raise MemoryConflict('The supplied evidence does not match its current admitted sources')
        if _signature(_collect(memory, scope, connection, None)) != signature:
            raise MemoryConflict('The evidence sources changed during cache rendering')
        try:
            check_current()
        except MemoryUnavailable as error:
            raise MemoryConflict(str(error)) from error
        publication_paths(memory, scope)
        publish(_cache(memory, path), result['content'].encode())
        return {'status': 'committed', 'artifacts': 1}

    receipt = memory._operation(scope, 'state-evidence-' + uuid4().hex,
        {'operation': 'state_evidence_cache', 'source_signature': signature}, apply)
    return {'ok': receipt['status'] == 'committed'}
