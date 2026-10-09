# ABOUTME: Traces exceptions from the actual lazily loaded synthetic owner response boundary.
# ABOUTME: Leaves the module load order intact and records no request credentials.
import json
from pathlib import Path
import threading

import httpx
from test_memory_operational_history import MemoryOperationalHistoryTests

failures = []

def trace_exception(frame, event, argument):
    if event == 'exception':
        kind, error, _ = argument
        if kind.__name__ in {'MemoryUnavailable', 'OSError', 'ValueError', 'PermissionError'}:
            failures.append({'function': frame.f_code.co_name, 'file': Path(frame.f_code.co_filename).name,
                'type': kind.__name__, 'error': str(error)})
    return trace_exception


def trace_call(frame, event, argument):
    if (event == 'call' and frame.f_code.co_name in {'snapshot', '_native', 'view', 'life_response'}
            and Path(frame.f_code.co_filename).name in {'memory_access.py', 'memory_preferences.py',
                'memory_operational_views.py', 'memory_operational_history.py'}):
        frame.f_trace_lines = False
        return trace_exception
    return None

threading.settrace(trace_call)
for index in range(20):
    fixture = MemoryOperationalHistoryTests()
    try:
        fixture.setUp()
        fixture.history(5000)
        with httpx.Client(timeout=30) as client:
            fixture.login(client)
            response = client.get(fixture.native + '/api/algorithm')
            print(json.dumps({'index': index, 'status': response.status_code, 'failures': list(failures)}), flush=True)
            failures.clear()
    finally: fixture.doCleanups()
