# ABOUTME: Publishes native Content run requests under current complete owner ledger admission.
# ABOUTME: Keeps existing bytes, retires stale responses, and recovers interrupted event appends.
import hashlib
import json
import re
from uuid import uuid4

from .memory_access import MemoryUnavailable
from .memory_content import EVENTS, validate_output
from .memory_policy import CATEGORIES
from .memory_source_review import _retirement_digest
from .memory_sources import authorize
from .memory_tab_freshness import _checked
from . import memory_operational_history as history


def target(value, observation):
    if (not isinstance(value, str) or len(value) > 256
            or re.fullmatch(r'/api/content/[A-Za-z0-9]{1,200}(?:/run)?', value) is None):
        raise LookupError('Choose a declared Content action route')
    if not isinstance(observation, dict) or set(observation) != {'method'} or observation['method'] != ('POST' if value.endswith('/run') else 'DELETE'):
        raise ValueError('Choose the declared Content action method')


def publication_paths(memory, scope, payload):
    authorize(scope)
    if not scope.principal or not CATEGORIES <= set(scope.write):
        raise MemoryUnavailable('Content runs require the unrestricted owner writer')
    if payload not in ({'operation': 'content_run'}, {'operation': 'content_delete'}):
        raise ValueError('Choose declared Content run publication')
    _checked(memory, memory._publication_path(EVENTS))
    return [EVENTS]


def action(memory, scope, route, observation, *, check_current):
    target(route, observation)
    authorize(scope)
    if not scope.principal or not CATEGORIES <= set(scope.write):
        raise MemoryUnavailable('Content actions require the unrestricted owner writer')
    if observation['method'] != 'POST':
        from .memory_content_disposal import dispose
        return dispose(memory, scope, route.split('/')[-1], check_current=check_current)
    check_current()
    streamed = {EVENTS: None}
    with memory._transaction() as connection:
        retired = _retirement_digest(connection)
        with history.snapshot(memory, scope, connection, check_current=check_current, sources=streamed,
                require_newline=False, objects_only=False, allow_unfinished_utf8=False,
                require_all_admitted=True) as (descriptor, fingerprints):
            plan = memory._native('content_run_plan', id=route.split('/')[-2], history_descriptor=descriptor,
                source_descriptors=(descriptor,))
            check_current()
            if history.fingerprint(memory, EVENTS, sources=streamed) != fingerprints[0]:
                raise MemoryUnavailable('Content ledger changes during native run preparation')
        if (not isinstance(plan, dict) or set(plan) != {'status', 'body', 'event'}
                or type(plan['status']) is not int or plan['status'] not in {200, 404}
                or not isinstance(plan['body'], dict) or not (plan['event'] is None or isinstance(plan['event'], dict))):
            raise MemoryUnavailable('Native Content run planning changes its response')
        validate_output(memory, scope, connection, plan)
        if plan['event'] is None:
            check_current()
            if _retirement_digest(connection) != retired or history.fingerprint(memory, EVENTS, sources=streamed) != fingerprints[0]:
                raise MemoryUnavailable('Content repeat delivery preserves later source and authority changes')
            return {'status': plan['status'], 'body': plan['body']}
        path = _checked(memory, memory._publication_path(EVENTS))
        raw = path.read_bytes()
        if raw and not raw.endswith(b'\n'):
            raise MemoryUnavailable('Content run publication requires a complete terminated ledger')
        if hashlib.sha256(raw).hexdigest() != fingerprints[0][2]:
            raise MemoryUnavailable('Content ledger changes before native run publication')
        event = json.dumps(plan['event'], ensure_ascii=False, separators=(',', ':')).encode() + b'\n'
        expected = hashlib.sha256(raw + event).hexdigest()
    payload = {'operation': 'content_run'}
    def append(connection):
        nonlocal expected
        check_current()
        if _retirement_digest(connection) != retired:
            raise MemoryUnavailable('Content retirement changes before run publication')
        if history.fingerprint(memory, EVENTS, sources=streamed) != fingerprints[0]:
            with history.snapshot(memory, scope, connection, check_current=check_current, sources=streamed,
                    require_newline=False, objects_only=False, allow_unfinished_utf8=False,
                    require_all_admitted=True) as (descriptor, current):
                repeated = memory._native('content_run_plan', id=route.split('/')[-2], history_descriptor=descriptor,
                    source_descriptors=(descriptor,))
                check_current()
                if history.fingerprint(memory, EVENTS, sources=streamed) != current[0]:
                    raise MemoryUnavailable('Content ledger changes during repeat admission')
            if repeated != {'status': 200, 'body': {'ok': True, 'id': route.split('/')[-2], 'already': True}, 'event': None}:
                raise MemoryUnavailable('Content source changes before run publication')
            validate_output(memory, scope, connection, repeated)
            expected = current[0][2]
            return {'status': 'committed', 'response': repeated['body']}
        result = memory._native('content_run_append', event=plan['event'])
        path = _checked(memory, memory._publication_path(EVENTS))
        path.chmod(0o600)
        check_current()
        if result != {'ok': True} or history.fingerprint(memory, EVENTS, sources=streamed)[2] != expected:
            raise MemoryUnavailable('Content publication changes its native event bytes')
        if _retirement_digest(connection) != retired:
            raise MemoryUnavailable('Content retirement changes during run publication')
        validate_output(memory, scope, connection, plan['body'])
        return {'status': 'committed', 'response': plan['body']}
    receipt = memory._operation(scope, 'content-run-' + uuid4().hex, payload, append,
        publication_digests={EVENTS: expected})
    if receipt['status'] != 'committed':
        raise MemoryUnavailable('Content run publication needs recovery')
    with memory._transaction() as connection:
        check_current()
        if _retirement_digest(connection) != retired or history.fingerprint(memory, EVENTS, sources=streamed)[2] != expected:
            raise MemoryUnavailable('Content delivery preserves later source or authority changes')
        validate_output(memory, scope, connection, receipt['response'])
        check_current()
    return {'status': 200, 'body': receipt['response']}
