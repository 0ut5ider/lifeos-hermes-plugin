# ABOUTME: Admits fixed identity and version sources for the native terminal banner.
# ABOUTME: Rechecks source identity, inventory numbers, and owner authority before output.
from datetime import datetime, timezone
import json
import re

from .memory_access import MemoryUnavailable, MemoryConflict
from .memory_sources import authorize, _admit, _source_time, markdown_projection, SOURCE_LIMIT, CORPUS_LIMIT
from .memory_operational_views import projection
from .memory_tab_freshness import _checked
from .memory_counts import KEYS

IDENTITY = 'LIFEOS/USER/DIGITAL_ASSISTANT/DA_IDENTITY.md'
SOURCES = frozenset({IDENTITY, 'LIFEOS/VERSION', 'LIFEOS/ALGORITHM/LATEST'})
DESIGNS = frozenset({'navy', 'navy-medium', 'navy-compact', 'navy-minimal', 'navy-ultra'})
COLOURS = re.compile(r'\x1b\[[0-9;]*m')


def arguments(args, width):
    if (not isinstance(args, list) or len(args) > 2 or any(not isinstance(value, str) for value in args)
            or type(width) is not int or not 1 <= width <= 1024):
        raise ValueError('Choose bounded native banner arguments and terminal width')
    if args not in ([], ['--test']) and not (len(args) == 1 and args[0].startswith('--design=') and args[0][9:] in DESIGNS):
        raise ValueError('Choose one native banner design or its design preview')


def collect(memory, scope, connection):
    contents, fingerprints, candidates = {}, [], []
    keys = lambda info: (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns)
    for relative in sorted(SOURCES):
        path = _checked(memory, memory.root / relative)
        if not path.exists():
            fingerprints.append((relative, None))
            continue
        before = path.stat()
        if not path.is_file() or before.st_size > SOURCE_LIMIT:
            raise MemoryUnavailable('Banner sources require bounded regular owner files')
        with path.open('rb') as stream: raw = stream.read(SOURCE_LIMIT + 1)
        if len(raw) > SOURCE_LIMIT: raise MemoryUnavailable('A banner source exceeds its byte limit')
        try: content = raw.decode('utf-8')
        except UnicodeError as error: raise MemoryUnavailable('Banner sources require valid UTF-8') from error
        after = _checked(memory, path).stat()
        if keys(before) != keys(after): raise MemoryUnavailable('A banner source changes during collection')
        decoded = markdown_projection(memory, relative, content)
        contents[relative] = content
        fingerprints.append((relative, keys(after), raw))
        candidates.append((relative, content, decoded, _source_time(after)))
    if sum(len(content.encode()) + len((decoded or '').encode()) for _, content, decoded, _ in candidates) > CORPUS_LIMIT:
        raise MemoryUnavailable('Banner sources exceed their complete transport limit')
    accepted = memory._native('validate_source_batch', contents=[(decoded or '') + '\n' + relative
        for relative, _, decoded, _ in candidates])['accepted'] if candidates else []
    for (relative, content, decoded, timestamp), valid in zip(candidates, accepted, strict=True):
        if decoded is None or valid is not True or _admit(memory, connection, scope, content, relative,
                timestamp, projection=decoded)['excluded']:
            raise MemoryUnavailable('A banner source requires current safe owner review')
    return contents, fingerprints


def counts(memory):
    selected = {}
    for key in ('skills', 'hooks'):
        values = memory._native('counts', only=key)
        if (not isinstance(values, dict) or set(values) != set(KEYS)
                or any(type(value) is not int or not 0 <= value <= 2 ** 53 - 1 for value in values.values())):
            raise MemoryUnavailable('Banner inventory requires bounded native numbers')
        selected[key] = values[key]
    return selected


def run(memory, scope, *, args, width, check_current):
    arguments(args, width)
    authorize(scope)
    if not scope.principal: raise MemoryUnavailable('The native banner requires a bound owner')
    check_current()
    with memory._transaction() as connection:
        contents, fingerprints = collect(memory, scope, connection)
        inventory = counts(memory)
        result = memory._native('banner_view', sources=contents, counts=inventory, args=args, width=width)
        check_current()
        if (collect(memory, scope, connection) != (contents, fingerprints) or counts(memory) != inventory):
            raise MemoryConflict('Banner sources or inventory change during native rendering')
        if (not isinstance(result, dict) or set(result) != {'stats', 'stdout'} or not isinstance(result['stats'], dict)
                or set(result['stats']) != {'name', 'catchphrase', 'repoUrl', 'skills', 'hooks', 'paiVersion', 'algorithmVersion'}
                or not isinstance(result['stdout'], str) or len(json.dumps(result).encode()) > CORPUS_LIMIT
                or any(not isinstance(result['stats'][key], str) for key in ('name', 'catchphrase', 'repoUrl', 'paiVersion', 'algorithmVersion'))
                or any(type(result['stats'][key]) is not int or result['stats'][key] != inventory[key] for key in inventory)):
            raise MemoryUnavailable('The native banner changes its declared response')
        decoded = projection(json.dumps({**result, 'stdout': COLOURS.sub('', result['stdout'])}))
        if (decoded is None or memory._native('validate_source_batch', contents=[decoded])['accepted'] != [True]
                or memory._filter_history(connection, scope, decoded, datetime.now(timezone.utc).isoformat())['excluded']):
            raise MemoryUnavailable('The native banner response contains excluded text')
        check_current()
        return {'ok': True, 'stdout': result['stdout']}
