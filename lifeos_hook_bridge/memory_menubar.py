# ABOUTME: Admits current Menubar work, telemetry, daemon, and configured gateway sources.
# ABOUTME: Rechecks fixed owner files and anonymous histories before native aggregate delivery.
from datetime import datetime, timezone
import json
import os
from urllib.parse import urlsplit

from .memory_access import MemoryUnavailable
from .memory_sources import authorize, _admit, _source_time, SOURCE_LIMIT, CORPUS_LIMIT
from .memory_operational_views import projection
from .memory_tab_freshness import _checked
from . import memory_operational_history as history
from . import memory_conduit as conduit

ROUTES = frozenset({'/api/menubar', '/api/menubar/'})
SOURCES = frozenset({'LIFEOS/MEMORY/STATE/work.json', 'LIFEOS/PULSE/state/state.json',
    'LIFEOS/PULSE/state/pulse.pid', conduit.CONFIG})
PROFILE_SOURCES = frozenset({'HERMES/gateway_state.json', 'HERMES/gateway-starts.log'})
LOGS = {f'LIFEOS/MEMORY/OBSERVABILITY/{name}.jsonl': 512 * 1024
    for name in ('memory-writes', 'reviewer-runs', 'pending-proposals')}


def request_target(value):
    if not isinstance(value, str) or len(value) > 128:
        raise ValueError('Menubar requires a bounded native route')
    url = urlsplit(value)
    if url.scheme or url.netloc or url.fragment or url.path not in ROUTES or url.query not in ('', 'amber=0', 'amber=1'):
        raise ValueError('Choose a fixed Menubar route and declared optional integration state')
    return url.path + ('?' + url.query if url.query else '')


def source_path(memory, relative):
    if relative not in PROFILE_SOURCES:
        if relative not in SOURCES: raise MemoryUnavailable('Choose fixed Menubar sources')
        return _checked(memory, memory.root / relative)
    profile = memory.profile
    if profile.resolve() != memory.physical_profile or profile.exists() and (
            not profile.is_dir() or profile.stat().st_uid != os.getuid()):
        raise MemoryUnavailable('Gateway metadata changes its configured owner profile')
    path = profile / relative.split('/', 1)[1]
    if (path.resolve() != memory.physical_profile / path.name or path.is_symlink()
            or path.exists() and (not path.is_file() or path.stat().st_uid != os.getuid() or path.stat().st_nlink != 1
                or memory.database.exists() and path.samefile(memory.database))):
        raise MemoryUnavailable('Gateway metadata changes its fixed physical owner source')
    return path


def _collect(memory, scope, connection):
    sources, fingerprints, modified, total = [], [], {}, 0
    keys = lambda info: (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns)
    for relative in sorted(SOURCES | PROFILE_SOURCES):
        path = source_path(memory, relative)
        if not path.exists():
            fingerprints.append((relative, None))
            continue
        if not path.is_file(): raise MemoryUnavailable('Menubar sources require regular owner files')
        before = path.stat()
        if before.st_size > SOURCE_LIMIT: raise MemoryUnavailable('A Menubar source exceeds its byte limit')
        with path.open('rb') as stream: raw = stream.read(SOURCE_LIMIT + 1)
        if len(raw) > SOURCE_LIMIT: raise MemoryUnavailable('A Menubar source exceeds its byte limit')
        try: content = raw.decode('utf-8')
        except UnicodeError as error: raise MemoryUnavailable('Menubar sources require valid UTF-8') from error
        after = path.stat()
        source_path(memory, relative)
        if keys(before) != keys(after): raise MemoryUnavailable('A Menubar source changes during collection')
        decoded = projection(content) if relative.endswith('.json') else content
        if decoded is None: raise MemoryUnavailable('Menubar JSON sources require complete records')
        total += len(raw) + len(decoded.encode())
        if total > CORPUS_LIMIT: raise MemoryUnavailable('Menubar sources exceed their transport limit')
        if (memory._native('validate_source_batch', contents=[decoded + '\n' + relative])['accepted'] != [True]
                or _admit(memory, connection, scope, content, relative, _source_time(after), projection=decoded)['excluded']):
            raise MemoryUnavailable('A Menubar source is excluded under current owner policy')
        sources.append({'relative': relative, 'content': content})
        fingerprints.append((relative, keys(after), raw))
        modified[relative] = after.st_mtime_ns / 1000000
    profile = memory.profile
    present = profile.exists()
    profile_state = (str(profile), str(profile.resolve()), present,
        keys(profile.stat()) if present else None)
    return sources, fingerprints, modified, profile_state


def view(memory, scope, target, *, check_current=None):
    target = request_target(target)
    authorize(scope)
    if not scope.principal: raise MemoryUnavailable('Menubar requires a bound owner')
    if check_current is not None: check_current()
    if urlsplit(target).query == 'amber=1':
        raise MemoryUnavailable('Optional Amber access requires a governed adapter')
    # Admit every fixed source before the dependent native default publication.
    with memory._transaction() as connection:
        initial = _collect(memory, scope, connection)
        if check_current is not None: check_current()
    if not any(source['relative'] == conduit.CONFIG for source in initial[0]):
        conduit.view(memory, scope, '/api/conduit/today', check_current=check_current)
    date = datetime.now().strftime('%Y-%m-%d')
    streamed = {**LOGS, conduit.PREFIX + 'events/' + date + '.jsonl': None}
    with memory._transaction() as connection:
        sources, fingerprints, modified, profile = _collect(memory, scope, connection)
        with history.snapshot(memory, scope, connection, check_current=check_current, sources=streamed,
                require_newline=False, objects_only=False, allow_unfinished_utf8=False) as (descriptor, event_fingerprints):
            result = memory._native('menubar_view', sources=sources, modified=modified,
                profile_home=profile[0], profile_present=profile[2], date=date,
                history_descriptor=descriptor, source_descriptors=(descriptor,))
            if check_current is not None: check_current()
            if (_collect(memory, scope, connection) != (sources, fingerprints, modified, profile)
                    or [history.fingerprint(memory, relative, sources=streamed) for relative in streamed] != event_fingerprints
                    or datetime.now().strftime('%Y-%m-%d') != date):
                raise MemoryUnavailable('Menubar sources change during native rendering')
        if (not isinstance(result, dict) or set(result) != {'status', 'body'} or type(result['status']) is not int
                or result['status'] != 200 or not isinstance(result['body'], dict)
                or len(json.dumps(result).encode()) > CORPUS_LIMIT):
            raise MemoryUnavailable('The native Menubar view changes its declared response')
        decoded = projection(json.dumps(result))
        if (decoded is None or memory._native('validate_source_batch', contents=[decoded])['accepted'] != [True]
                or memory._filter_history(connection, scope, decoded, datetime.now(timezone.utc).isoformat())['excluded']):
            raise MemoryUnavailable('The native Menubar response contains excluded text')
        if check_current is not None: check_current()
        return result
