# ABOUTME: Validates current native Pulse runtime observations under the bound owner policy.
# ABOUTME: Refuses unsupported subsystems and excluded labels before authenticated health delivery.
from datetime import datetime, timezone
import json

from .memory_access import MemoryUnavailable
from .memory_sources import authorize
from .memory_operational_views import projection

LIMIT = 65536
SUBSYSTEMS = frozenset({'cron', 'hooks', 'observability', 'performance', 'dashboard'})


def _integer(value, *, minimum=0, maximum=9007199254740991):
    return type(value) is int and minimum <= value <= maximum


def _text(value, limit=4096):
    return isinstance(value, str) and len(value.encode()) <= limit


def _date(value):
    if not _text(value, 64): return False
    try:
        parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
        return parsed.tzinfo is not None
    except ValueError: return False


def _shape(value, keys):
    return isinstance(value, dict) and set(value) == set(keys)


def validate(observation):
    if (not _shape(observation, {'status', 'body', 'observed_at'}) or type(observation['status']) is not int
            or observation['status'] not in {200, 503} or not _date(observation['observed_at'])):
        raise ValueError('Choose a bounded current native Pulse observation')
    observed = datetime.fromisoformat(observation['observed_at'].replace('Z', '+00:00'))
    if abs((datetime.now(timezone.utc) - observed).total_seconds()) > 60:
        raise ValueError('Pulse runtime observations require a current timestamp')
    body = observation['body']
    if (not _shape(body, {'status', 'reasons', 'service', 'pid', 'port', 'startedAt', 'uptime', 'subsystems'})
            or body['service'] != 'pulse' or not isinstance(body['status'], str) or body['status'] not in {'ok', 'degraded'}
            or not isinstance(body['reasons'], list) or len(body['reasons']) > 256
            or any(not _text(reason) for reason in body['reasons'])
            or not _integer(body['pid'], minimum=1) or not _integer(body['port'], minimum=1, maximum=65535)
            or not _integer(body['uptime']) or not _date(body['startedAt'])
            or not isinstance(body['subsystems'], dict) or set(body['subsystems']) - SUBSYSTEMS
            or not {'cron', 'dashboard'} <= set(body['subsystems'])):
        raise ValueError('Pulse health requires the selected native runtime fields')
    systems = body['subsystems']
    cron = systems['cron']
    if not _shape(cron, {'status', 'jobs'}) or cron['status'] != 'ok' or not isinstance(cron['jobs'], list) or len(cron['jobs']) > 256:
        raise ValueError('Pulse health requires bounded native job observations')
    for job in cron['jobs']:
        if (not _shape(job, {'name', 'lastRun', 'agoMs', 'result', 'failures'}) or not _text(job['name'], 256)
                or not job['name'] or not _date(job['lastRun']) or not _integer(job['agoMs'], minimum=-9007199254740991)
                or not isinstance(job['result'], str) or job['result'] not in {'ok', 'error'} or not _integer(job['failures'])):
            raise ValueError('Pulse health requires complete native job metadata')
    dashboard = systems['dashboard']
    if (not _shape(dashboard, {'status', 'indexPath'}) or not isinstance(dashboard['status'], str) or dashboard['status'] not in {'ok', 'missing'}
            or not _text(dashboard['indexPath'])
            or observation['status'] != (503 if dashboard['status'] == 'missing' else 200)
            or body['status'] != ('degraded' if body['reasons'] else 'ok')):
        raise ValueError('Pulse health must retain native asset and degradation status')
    if 'hooks' in systems:
        hooks = systems['hooks']
        if (not _shape(hooks, {'status', 'stats'}) or hooks['status'] != 'ok'
                or not _shape(hooks['stats'], {'requests', 'skillGuard', 'agentGuard'})
                or not _integer(hooks['stats']['requests'])):
            raise ValueError('Pulse health requires native hook statistics')
        for name, keys in (('skillGuard', {'total', 'blocked', 'passed'}), ('agentGuard', {'total', 'warned', 'passed'})):
            counts = hooks['stats'][name]
            if not _shape(counts, keys) or any(not _integer(count) for count in counts.values()):
                raise ValueError('Pulse health requires complete native guard counts')
    for name, extras in (('observability', set()), ('performance', {'hasCostData', 'hasFailureData'})):
        if name not in systems: continue
        value = systems[name]
        if (not _shape(value, {'module', 'enabled', 'startedAt'} | extras) or value['module'] != name
                or type(value['enabled']) is not bool or value['startedAt'] is not None and not _date(value['startedAt'])
                or any(type(value[key]) is not bool for key in extras)):
            raise ValueError('Pulse health requires selected native subsystem metadata')
    try: encoded = json.dumps(observation, ensure_ascii=False, allow_nan=False)
    except (ValueError, TypeError) as error: raise ValueError('Pulse health requires finite native JSON') from error
    if len(encoded.encode()) > LIMIT: raise ValueError('Pulse health exceeds its observation byte limit')
    return projection(encoded)


def admit(memory, scope, observation, *, check_current=None):
    authorize(scope)
    if not scope.principal: raise MemoryUnavailable('Pulse runtime observations require a bound owner')
    if check_current is not None: check_current()
    decoded = validate(observation)
    if decoded is None: raise MemoryUnavailable('Pulse runtime observations exceed their complete projection limit')
    with memory._transaction() as connection:
        if (memory._native('validate_source_batch', contents=[decoded])['accepted'] != [True]
                or memory._filter_history(connection, scope, decoded, observation['observed_at'])['excluded']):
            raise MemoryUnavailable('Pulse runtime observations contain excluded labels')
        if check_current is not None: check_current()
        return {'status': observation['status'], 'body': observation['body']}
