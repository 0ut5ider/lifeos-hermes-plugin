# ABOUTME: Measures real owner aggregation and shared relay delivery for the largest telemetry window.
# ABOUTME: Traces transport exceptions without retaining session credentials or original owner records.
import json
import sys
import time

import httpx
from lifeos_hook_bridge.memory_http import relay
from test_memory_capabilities import MemoryCapabilitiesTests


errors = []


def trace(frame, event, argument):
    if event == 'exception' and frame.f_code.co_name == 'relay':
        kind, error, _ = argument
        errors.append({'type': kind.__name__, 'error': str(error)})
    return trace


fixture = MemoryCapabilitiesTests()
try:
    fixture.setUp()
    activity, _ = fixture.seed(copies=11000)
    with httpx.Client(timeout=60) as client:
        fixture.login(client)
        started = time.monotonic()
        owner = client.get(fixture.dashboard + '/api/plugins/lifeos-hook-bridge/memory/life',
            params={'target': '/api/capabilities?window=1440'})
        print(json.dumps({'source_bytes': activity.stat().st_size, 'owner_status': owner.status_code,
            'owner_seconds': round(time.monotonic() - started, 6),
            'tool_calls': owner.json().get('totals', {}).get('tool_calls')}), flush=True)
        cookie = '; '.join(f'{key}={value}' for key, value in client.cookies.items())
        started = time.monotonic()
        sys.settrace(trace)
        try:
            result = relay(fixture.fixture.configuration, {'view': 'life', 'target': '/api/capabilities?window=1440',
                'authorization': '', 'cookie': cookie})
        finally: sys.settrace(None)
        print(json.dumps({'relay_status': result['status'], 'relay_seconds': round(time.monotonic() - started, 6),
            'errors': list(errors)}), flush=True)
finally: fixture.doCleanups()
