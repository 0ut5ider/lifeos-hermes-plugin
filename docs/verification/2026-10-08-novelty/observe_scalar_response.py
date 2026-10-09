# ABOUTME: Captures actual owner novelty JSON and the shared relay's scalar rejection.
# ABOUTME: Records only synthetic response values and exception messages without credentials.
import json
import sys

import httpx
from lifeos_hook_bridge.memory_http import relay
from test_memory_novelty import MemoryNoveltyTests


errors = []


def trace(frame, event, argument):
    if event == 'exception' and frame.f_code.co_name == 'relay':
        kind, error, _ = argument
        if kind is ValueError: errors.append(str(error))
    return trace


fixture = MemoryNoveltyTests()
try:
    fixture.setUp()
    path = fixture.seed()
    with httpx.Client(timeout=30) as client:
        fixture.login(client)
        cookie = '; '.join(f'{key}={value}' for key, value in client.cookies.items())
        for value in ('SyntheticNoveltyCurrent', 17, True):
            path.write_text(json.dumps(value))
            owner = client.get(fixture.dashboard + '/api/plugins/lifeos-hook-bridge/memory/life',
                params={'target': '/api/novelty'})
            sys.settrace(trace)
            try:
                result = relay(fixture.fixture.configuration, {'view': 'life', 'target': '/api/novelty',
                    'authorization': '', 'cookie': cookie})
            finally: sys.settrace(None)
            print(json.dumps({'value': value, 'owner_status': owner.status_code,
                'owner_body': owner.json(), 'relay_status': result['status'], 'errors': list(errors)}))
            errors.clear()
finally: fixture.doCleanups()
