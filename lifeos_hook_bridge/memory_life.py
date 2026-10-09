# ABOUTME: Supplies current admitted TELOS sources to native Life home and goals views.
# ABOUTME: Rechecks source bytes and authenticated owner authority before returning rendered responses.
from datetime import datetime, timezone
import json
import os
from urllib.parse import urlsplit

from .memory_access import MemoryUnavailable
from .memory_sources import authorize, read_markdown, CORPUS_LIMIT, _source_path
from .memory_operational_views import ROUTES as OPERATIONAL_ROUTES
from .memory_personal_modules import ROUTES as PERSONAL_ROUTES
from .memory_performance import ROUTES as PERFORMANCE_ROUTES
from .memory_conduit import ROUTES as CONDUIT_ROUTES

ROUTES = frozenset({'/api/life/home', '/api/life/goals', '/api/life/health', '/api/life/finances',
                    '/api/life/work', '/api/life/business', '/api/observability/life-card', '/api/user-index',
                    '/api/telos/overview', '/api/onboarding/state', '/api/atlas', '/api/atlas/insights'}) | frozenset(OPERATIONAL_ROUTES) | PERSONAL_ROUTES | frozenset(PERFORMANCE_ROUTES) | CONDUIT_ROUTES


def request_target(value):
    if not isinstance(value, str) or len(value) > 256:
        raise ValueError('Life views require a bounded installed route')
    parsed = urlsplit(value)
    if parsed.path in CONDUIT_ROUTES:
        from .memory_conduit import request_target as conduit_target
        return conduit_target(value)
    if parsed.path in PERFORMANCE_ROUTES:
        from .memory_performance import request_target as performance_target
        return performance_target(value)
    if parsed.path in PERSONAL_ROUTES:
        from .memory_personal_modules import request_target as personal_target
        return personal_target(value)
    if parsed.path == '/api/capabilities' and not parsed.scheme and not parsed.netloc and not parsed.fragment:
        if parsed.query not in ('', 'window=60', 'window=360', 'window=1440'):
            raise ValueError('Capability telemetry requires a fixed declared time window')
        return parsed.path + ('?' + parsed.query if parsed.query else '')
    if parsed.path == '/api/user-index' and not parsed.scheme and not parsed.netloc and not parsed.fragment:
        if parsed.query not in ('', 'filter=stats', 'filter=publish', 'filter=stale', 'filter=gaps'):
            raise ValueError('User indexes require a fixed declared slice')
        return parsed.path + ('?' + parsed.query if parsed.query else '')
    if parsed.scheme or parsed.netloc or parsed.query or parsed.fragment:
        raise ValueError('Life views require fixed routes without selectors')
    if parsed.path not in ROUTES:
        raise LookupError('This Life route is not a governed read view')
    return parsed.path


def _sources(memory, scope, connection, filenames):
    authorize(scope)
    if not scope.principal:
        raise MemoryUnavailable('Life views require a bound owner')
    paths = []
    for filename in filenames:
        path, _ = _source_path(memory, scope,
            str(memory.root / 'LIFEOS/USER/TELOS' / filename), require_file=False)
        if path.is_symlink() or path.exists() and (not path.is_file()
                or path.stat().st_uid != os.getuid() or path.stat().st_nlink != 1):
            raise MemoryUnavailable('Life views require regular fixed owner sources')
        if path.exists(): paths.append(str(path))
    sources = read_markdown(memory, scope, paths, connection=connection)
    result = [{'filename': source['relative'].rsplit('/', 1)[1], 'content': source['content']}
              for source in sources]
    if len(json.dumps(result).encode()) > CORPUS_LIMIT:
        raise MemoryUnavailable('Life view sources exceed their transport limit')
    return result


def view(memory, scope, target, *, check_current=None):
    target = request_target(target)
    if urlsplit(target).path in CONDUIT_ROUTES:
        from .memory_conduit import view as conduit_view
        return conduit_view(memory, scope, target, check_current=check_current)
    if urlsplit(target).path in PERFORMANCE_ROUTES:
        from .memory_performance import view as performance_view
        return performance_view(memory, scope, target, check_current=check_current)
    if urlsplit(target).path in PERSONAL_ROUTES:
        from .memory_personal_modules import view as personal_view
        return personal_view(memory, scope, target, check_current=check_current)
    if target in {'/api/atlas', '/api/atlas/insights'}:
        from .memory_atlas import view as atlas_view
        return atlas_view(memory, scope, target=target, check_current=check_current)
    if target in OPERATIONAL_ROUTES:
        from .memory_operational_views import view as operational_view
        return operational_view(memory, scope, target, check_current=check_current)
    if target == '/api/onboarding/state':
        from .memory_onboarding import view as onboarding_view
        return onboarding_view(memory, scope, check_current=check_current)
    if target == '/api/telos/overview':
        from .memory_telos_overview import view as overview_view
        return overview_view(memory, scope, check_current=check_current)
    if target.split('?')[0] == '/api/user-index':
        from .memory_user_index import view as index_view
        return index_view(memory, scope, target, check_current=check_current)
    if target == '/api/life/health':
        from .memory_life_health import view as health_view
        return health_view(memory, scope, check_current=check_current)
    if target == '/api/life/finances':
        from .memory_life_finances import view as finance_view
        return finance_view(memory, scope, check_current=check_current)
    if target == '/api/life/work':
        from .memory_life_work import view as work_view
        return work_view(memory, scope, check_current=check_current)
    if target == '/api/life/business':
        from .memory_life_business import view as business_view
        return business_view(memory, scope, check_current=check_current)
    if check_current is not None: check_current()
    authorize(scope)
    if not scope.principal:
        raise MemoryUnavailable('Life views require a bound owner')
    filenames = memory._native('life_view_sources').get('filenames')
    if (not isinstance(filenames, list) or len(filenames) > 32
            or any(not isinstance(name, str) or not name.endswith('.md')
                or '/' in name or '\\' in name or '..' in name for name in filenames)
            or len(set(filenames)) != len(filenames)):
        raise MemoryUnavailable('Native Life sources change their declared registry')
    with memory._transaction() as connection:
        sources = _sources(memory, scope, connection, filenames)
        result = memory._native('life_view', sources=sources, target=target)
        if check_current is not None: check_current()
        if _sources(memory, scope, connection, filenames) != sources:
            raise MemoryUnavailable('Life sources change during native rendering')
        if (not isinstance(result, dict) or set(result) != {'status', 'body'}
                or type(result['status']) is not int or result['status'] != 200
                or not isinstance(result['body'], dict) or len(json.dumps(result).encode()) > CORPUS_LIMIT):
            raise MemoryUnavailable('The native Life view changes its declared response')
        if memory._filter_history(connection, scope, json.dumps(result), datetime.now(timezone.utc).isoformat())['excluded']:
            raise MemoryUnavailable('The native Life view contains excluded source text')
        if check_current is not None: check_current()
        return result
