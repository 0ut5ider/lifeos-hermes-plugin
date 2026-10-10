# ABOUTME: Admits complete skill scan snapshots and fixed owner security controls.
# ABOUTME: Rechecks native selection, source identity, and owner authority before returning a verdict.
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile

from .memory_access import MemoryUnavailable, MemoryConflict
from .memory_sources import authorize, _admit, _source_time, SOURCE_LIMIT, SOURCE_COUNT_LIMIT, CORPUS_LIMIT
from .memory_operational_views import projection
from .memory_tab_freshness import _checked
from .memory_transaction import publish

DENY = 'LIFEOS/USER/SECURITY/DENY_LIST.txt'
HASHES = 'LIFEOS/USER/SECURITY/DENY_HASHES.json'
ALLOW = 'LIFEOS/USER/CONFIG/skill-hygiene-allowlist.json'
CONTROLS = frozenset({DENY, ALLOW})
EXCLUDED = frozenset({'node_modules', '.playwright-cli', 'profile-data', '.cache'})


def declared(relative):
    parts = Path(relative).parts
    return (relative in CONTROLS or len(parts) >= 2 and parts[0] == 'skills'
        and all(part not in {'', '.', '..'} | EXCLUDED for part in parts)
        and Path(relative).suffix not in {'.png', '.jpg', '.mp3', '.mp4'})


def arguments(args):
    if not isinstance(args, list) or len(args) > 5 or any(not isinstance(value, str) for value in args):
        raise ValueError('Choose bounded native skill scan arguments')
    values, index = {}, 0
    while index < len(args):
        key = args[index]
        if key == '--json' and key not in values:
            values[key] = True
            index += 1
        elif key in {'--skill', '--max-detail'} and key not in values and index + 1 < len(args):
            values[key] = args[index + 1]
            index += 2
        else: raise ValueError('Choose declared native skill scan arguments once')
    skill = values.get('--skill')
    if skill is not None and (not 0 < len(skill.encode()) <= 256 or skill in {'.', '..'}
            or any(char in skill for char in '/\\*?[]{}') or any(ord(char) < 32 for char in skill)):
        raise ValueError('Choose one exact native skill directory')
    detail = values.get('--max-detail')
    if detail is not None and (not detail.isascii() or not detail.isdecimal() or not 0 <= int(detail) <= 2048):
        raise ValueError('Choose a bounded native finding detail count')
    return skill


def inventory(memory, skill):
    directory = _checked(memory, memory.root / 'skills')
    if not directory.is_dir(): raise MemoryUnavailable('The native skills directory is unavailable')
    result = memory._native('skill_hygiene_inventory', skill=skill)
    if (not isinstance(result, dict) or set(result) != {'files', 'vendored'}
            or any(not isinstance(result[key], list) or len(result[key]) > SOURCE_COUNT_LIMIT
                or any(not isinstance(value, str) or len(value.encode()) > 4096 for value in result[key]) for key in result)
            or len(set(result['files'])) != len(result['files']) or len(json.dumps(result).encode()) > CORPUS_LIMIT
            or any(not declared('skills/' + name) or name.startswith('/') or any(ord(char) < 32 for char in name)
                for name in result['files'])):
        raise MemoryUnavailable('The native skill scan changes its bounded selection')
    result['files'].sort()
    result['vendored'].sort()
    return result


def source(memory, relative):
    path = _checked(memory, memory.root / relative)
    if not path.exists(): return None, (relative, None), None
    before = path.stat()
    if not path.is_file() or before.st_size > SOURCE_LIMIT:
        raise MemoryUnavailable('Skill scan sources require bounded regular owner files')
    with path.open('rb') as stream: raw = stream.read(SOURCE_LIMIT + 1)
    if len(raw) > SOURCE_LIMIT: raise MemoryUnavailable('A skill scan source exceeds its byte limit')
    try: content = raw.decode('utf-8')
    except UnicodeError as error: raise MemoryUnavailable('Skill scan sources require valid UTF-8') from error
    after = _checked(memory, path).stat()
    keys = lambda info: (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns)
    if keys(before) != keys(after): raise MemoryConflict('A skill scan source changes during collection')
    return content, (relative, keys(after), hashlib.sha256(raw).hexdigest()), _source_time(after)


def collect(memory, scope, connection, skill, root, check_current):
    selected = inventory(memory, skill)
    fingerprints, batch, size = [], [], 2

    def flush():
        nonlocal batch, size
        if not batch: return
        check_current()
        accepted = memory._native('validate_source_batch', contents=[decoded + '\n' + relative
            for relative, content, decoded, timestamp in batch])['accepted']
        for (relative, content, decoded, timestamp), valid in zip(batch, accepted, strict=True):
            if valid is not True or _admit(memory, connection, scope, content, relative, timestamp, projection=decoded)['excluded']:
                raise MemoryUnavailable('A complete skill scan requires current safe owner sources')
            if root is not None: publish(root / relative, content.encode())
        batch, size = [], 2

    for relative in sorted(CONTROLS) + ['skills/' + name for name in selected['files']]:
        content, fingerprint, timestamp = source(memory, relative)
        fingerprints.append(fingerprint)
        if content is None: continue
        decoded = projection(content) if relative == ALLOW else content
        # Native malformed allowlists produce a scan error. Their raw text still needs admission.
        if decoded is None: decoded = content
        added = len(json.dumps(decoded + '\n' + relative).encode()) + 2
        if added > CORPUS_LIMIT - 4096: raise MemoryUnavailable('A skill scan projection exceeds its transport limit')
        if batch and (size + added > CORPUS_LIMIT - 4096 or len(batch) >= SOURCE_COUNT_LIMIT): flush()
        batch.append((relative, content, decoded, timestamp))
        size += added
    flush()
    hashes = _checked(memory, memory.root / HASHES)
    if hashes.exists():
        if not hashes.is_file(): raise MemoryUnavailable('The native hash artifact changes its physical source')
        info = hashes.stat()
        fingerprints.append((HASHES, (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns)))
        if root is not None: publish(root / HASHES, b'{}')
    else: fingerprints.append((HASHES, None))
    return selected, fingerprints


def render(memory, args, root):
    home = root.parent
    environment = dict(os.environ, HOME=str(home), LIFEOS_DIR=str(root / 'LIFEOS'),
        LIFEOS_MEMORY_INTERNAL='1', LIFEOS_MEMORY_HYGIENE_GIT_ROOT=str(memory.root), BUN_CONFIG_NO_AUTO_INSTALL='1')
    for name in ('LIFEOS_MEMORY_CONTEXT', 'LIFEOS_MEMORY_PUBLICATION_JOURNAL'):
        environment.pop(name, None)
    result = subprocess.run([memory.bun, '--no-install', str(memory.root / 'LIFEOS/TOOLS/SkillHygieneGate.ts'), *args],
        capture_output=True, text=True, timeout=30, env=environment, cwd=home)
    if result.returncode not in (0, 1, 2) or len((result.stdout + result.stderr).encode()) > CORPUS_LIMIT:
        raise MemoryUnavailable('The native skill scan is unavailable')
    return result


def run(memory, scope, *, args, check_current):
    skill = arguments(args)
    authorize(scope)
    if not scope.principal: raise MemoryUnavailable('Skill scans require a bound owner')
    check_current()
    with memory._transaction() as connection, tempfile.TemporaryDirectory(prefix='lifeos-skill-scan-') as directory:
        root = Path(directory) / '.claude'
        (root / 'skills').mkdir(parents=True, mode=0o700)
        collected = collect(memory, scope, connection, skill, root, check_current)
        result = render(memory, args, root)
        check_current()
        if collect(memory, scope, connection, skill, None, check_current) != collected:
            raise MemoryConflict('Skill scan sources change during native rendering')
        decoded = projection(result.stdout) if '--json' in args and result.stdout else result.stdout
        text = (decoded or '') + '\n' + result.stderr
        if (decoded is None or memory._native('validate_source_batch', contents=[text])['accepted'] != [True]
                or memory._filter_history(connection, scope, text, datetime.now(timezone.utc).isoformat())['excluded']):
            raise MemoryUnavailable('The native skill scan response contains excluded text')
        check_current()
        return {'ok': True, 'stdout': result.stdout, 'stderr': result.stderr, 'exit_code': result.returncode}
