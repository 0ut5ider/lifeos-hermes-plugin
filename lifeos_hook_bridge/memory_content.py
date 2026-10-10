# ABOUTME: Admits the complete Conveyor ledger for current owner board and status reads.
# ABOUTME: Refuses incomplete policy folds and rechecks admitted descriptors before delivery.
from datetime import datetime, timezone
import json
import re
from urllib.parse import urlsplit

from .memory_access import MemoryUnavailable
from .memory_sources import authorize, CORPUS_LIMIT
from .memory_operational_views import projection
from . import memory_operational_history as history

EVENTS = 'LIFEOS/MEMORY/STATE/content-pipeline/events.jsonl'
ROUTES = frozenset({'/api/content', '/api/content/', '/api/content/status'})


def request_target(value):
    if not isinstance(value, str) or len(value) > 256:
        raise ValueError('Content requires a bounded native route')
    url = urlsplit(value)
    if url.scheme or url.netloc or url.fragment or (url.path not in ROUTES
            and re.fullmatch(r'/api/content/[A-Za-z0-9]+(?:/run)?', url.path) is None):
        raise LookupError('Choose a declared Content route')
    if url.query and not (url.path == '/api/content/status' and url.query in {'running=0', 'running=1'}):
        raise ValueError('Content requires declared native runtime state')
    return url.path + ('?' + url.query if url.query else '')


def view(memory, scope, target, *, check_current=None):
    target = request_target(target)
    url = urlsplit(target)
    authorize(scope)
    if not scope.principal: raise MemoryUnavailable('Content requires a bound owner')
    if check_current is not None: check_current()
    if url.path not in ROUTES:
        raise MemoryUnavailable('Content actions require governed publication and runner control')
    streamed = {EVENTS: None}
    with memory._transaction() as connection:
        with history.snapshot(memory, scope, connection, check_current=check_current, sources=streamed,
                require_newline=False, objects_only=False, allow_unfinished_utf8=False,
                require_all_admitted=True) as (descriptor, fingerprints):
            result = memory._native('content_view', target=url.path, running=url.query == 'running=1',
                history_descriptor=descriptor, source_descriptors=(descriptor,))
            if check_current is not None: check_current()
            if [history.fingerprint(memory, EVENTS, sources=streamed)] != fingerprints:
                raise MemoryUnavailable('The Content ledger changes during native rendering')
        if (not isinstance(result, dict) or set(result) != {'status', 'body'} or type(result['status']) is not int
                or result['status'] != 200 or not isinstance(result['body'], dict)
                or len(json.dumps(result).encode()) > CORPUS_LIMIT):
            raise MemoryUnavailable('The native Content view changes its declared response')
        validate_output(memory, scope, connection, result)
        if check_current is not None: check_current()
        return result


def validate_output(memory, scope, connection, result):
    decoded = projection(json.dumps(result), field_limit=CORPUS_LIMIT)
    if (decoded is None or memory._native('validate_source_batch', contents=[decoded])['accepted'] != [True]
            or memory._filter_history(connection, scope, decoded, datetime.now(timezone.utc).isoformat())['excluded']):
        raise MemoryUnavailable('The native Content response contains excluded text')
