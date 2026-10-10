# ABOUTME: Runs native recommendations on fixed admitted preference and consumption snapshots.
# ABOUTME: Rechecks source identity and owner authority before delivering native command output.
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import tempfile

from .memory_access import MemoryUnavailable, MemoryConflict
from .memory_sources import authorize, _admit, _source_time, SOURCE_LIMIT, CORPUS_LIMIT
from .memory_operational_views import projection
from .memory_tab_freshness import _checked
from .memory_transaction import publish

PREFIX = 'LIFEOS/USER/TELOS/'
PREFERENCES = {'restaurant': PREFIX + 'RESTAURANTS.md', 'movie': PREFIX + 'MOVIES.md', 'book': PREFIX + 'BOOKS.md'}
CONSUMPTION = PREFIX + 'CURRENT_STATE/CONSUMPTION.md'
OPTIONS = {'--category', '--cuisine', '--genre', '--theme', '--not-visited', '--not-watched'}


def arguments(args):
    if (not isinstance(args, list) or len(args) > 13
            or any(not isinstance(value, str) or not 0 < len(value.encode()) <= 256 for value in args)):
        raise ValueError('Choose bounded native recommendation arguments')
    values, json_output, index = {}, False, 0
    while index < len(args):
        key = args[index]
        if key == '--json' and not json_output:
            json_output = True
            index += 1
        elif key in OPTIONS and key not in values and index + 1 < len(args) and not args[index + 1].startswith('--'):
            values[key] = args[index + 1]
            index += 2
        else: raise ValueError('Choose declared native recommendation options once')
    if values.get('--category') not in PREFERENCES:
        raise ValueError('Choose restaurant, movie, or book recommendations')
    return values['--category'], json_output


def collect(memory, scope, connection, category):
    names = [PREFERENCES[category]]
    if category != 'book': names.append(CONSUMPTION)
    contents, fingerprints, candidates, total = {}, [], [], 0
    keys = lambda info: (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns)
    for relative in names:
        path = _checked(memory, memory.root / relative)
        if not path.exists():
            fingerprints.append((relative, None))
            continue
        before = path.stat()
        if not path.is_file() or before.st_size > SOURCE_LIMIT:
            raise MemoryUnavailable('Recommendation sources require bounded regular owner files')
        with path.open('rb') as stream: raw = stream.read(SOURCE_LIMIT + 1)
        if len(raw) > SOURCE_LIMIT: raise MemoryUnavailable('A recommendation source exceeds its byte limit')
        try: content = raw.decode('utf-8')
        except UnicodeError as error: raise MemoryUnavailable('Recommendation sources require valid UTF-8') from error
        after = _checked(memory, path).stat()
        if keys(before) != keys(after): raise MemoryUnavailable('A recommendation source changes during collection')
        total += len(raw)
        if total > CORPUS_LIMIT: raise MemoryUnavailable('Recommendation sources exceed their transport limit')
        contents[relative] = content
        fingerprints.append((relative, keys(after), raw))
        candidates.append((relative, content, _source_time(after)))
    accepted = memory._native('validate_source_batch', contents=[content + '\n' + relative
        for relative, content, _ in candidates])['accepted'] if candidates else []
    for (relative, content, timestamp), valid in zip(candidates, accepted, strict=True):
        if valid is not True or _admit(memory, connection, scope, content, relative, timestamp)['excluded']:
            raise MemoryUnavailable('A recommendation source requires current safe owner review')
    return contents, fingerprints


def render(memory, args, contents):
    with tempfile.TemporaryDirectory(prefix='lifeos-recommend-') as directory:
        home = Path(directory)
        root = home / '.claude'
        root.mkdir(mode=0o700)
        for relative, content in contents.items(): publish(root / relative, content.encode())
        environment = dict(os.environ, HOME=str(home), LIFEOS_DIR=str(root / 'LIFEOS'),
            LIFEOS_CONFIG_DIR=str(root / 'LIFEOS/USER/CONFIG'), PROJECTS_DIR=str(root / 'LIFEOS/USER/PROJECTS'),
            LIFEOS_MEMORY_INTERNAL='1', BUN_CONFIG_NO_AUTO_INSTALL='1')
        for name in ('LIFEOS_CONFIG_PATH', 'LIFEOS_MEMORY_CONTEXT', 'LIFEOS_MEMORY_PUBLICATION_JOURNAL'):
            environment.pop(name, None)
        result = subprocess.run([memory.bun, '--no-install', str(memory.root / 'LIFEOS/TOOLS/Recommend.ts'), *args],
            capture_output=True, text=True, timeout=30, env=environment, cwd=home)
        if result.returncode != 0 or result.stderr or len(result.stdout.encode()) > CORPUS_LIMIT:
            raise MemoryUnavailable('The native recommendation command is unavailable')
        return result.stdout


def run(memory, scope, *, args, check_current):
    category, json_output = arguments(args)
    authorize(scope)
    if not scope.principal: raise MemoryUnavailable('Recommendations require a bound owner')
    check_current()
    with memory._transaction() as connection:
        contents, fingerprints = collect(memory, scope, connection, category)
        stdout = render(memory, args, contents)
        check_current()
        if collect(memory, scope, connection, category) != (contents, fingerprints):
            raise MemoryConflict('Recommendation sources change during native rendering')
        decoded = projection(stdout) if json_output else stdout
        if (decoded is None or memory._native('validate_source_batch', contents=[decoded])['accepted'] != [True]
                or memory._filter_history(connection, scope, decoded, datetime.now(timezone.utc).isoformat())['excluded']):
            raise MemoryUnavailable('The native recommendation response contains excluded text')
        check_current()
        return {'ok': True, 'stdout': stdout}
