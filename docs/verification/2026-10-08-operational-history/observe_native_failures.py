# ABOUTME: Records native failures behind actual synthetic operational history HTTP responses.
# ABOUTME: Preserves the real native operation and captures no request credentials.
import importlib
import types
import json
import os
from pathlib import Path
import sys

import httpx
from lifeos_hook_bridge.memory_access import NativeMemory
from lifeos_hook_bridge.memory_preferences import MemoryPreferences
from test_memory_operational_history import MemoryOperationalHistoryTests

original = NativeMemory._native
failures = []
calls = {}

def observe(memory, action, **arguments):
    calls[action] = calls.get(action, 0) + 1
    try: return original(memory, action, **arguments)
    except Exception as error:
        failures.append({'action': action, 'type': type(error).__name__, 'error': str(error)})
        raise

NativeMemory._native = observe
original_response = MemoryPreferences.life_response

def observe_response(preferences, *arguments, **keywords):
    try: return original_response(preferences, *arguments, **keywords)
    except Exception as error:
        failures.append({'boundary': 'life_response', 'type': type(error).__name__, 'error': str(error)})
        raise

MemoryPreferences.life_response = observe_response
name = 'lifeos_memory_settings'
if name not in sys.modules:
    package = types.ModuleType(name)
    package.__path__ = [str(Path(__file__).resolve().parents[3] / 'lifeos_hook_bridge')]
    sys.modules[name] = package
actual_access = importlib.import_module(name + '.memory_access')
actual_preferences = importlib.import_module(name + '.memory_preferences')
actual_native = actual_access.NativeMemory._native
actual_response = actual_preferences.MemoryPreferences.life_response

def observe_actual_native(memory, action, **arguments):
    key = 'dashboard:' + action
    calls[key] = calls.get(key, 0) + 1
    try: return actual_native(memory, action, **arguments)
    except Exception as error:
        failures.append({'boundary': 'dashboard_native', 'action': action, 'type': type(error).__name__, 'error': str(error)})
        raise

def observe_actual_response(preferences, *arguments, **keywords):
    try: return actual_response(preferences, *arguments, **keywords)
    except Exception as error:
        failures.append({'boundary': 'dashboard_life_response', 'type': type(error).__name__, 'error': str(error)})
        raise

actual_access.NativeMemory._native = observe_actual_native
actual_preferences.MemoryPreferences.life_response = observe_actual_response
for index in range(12):
    fixture = MemoryOperationalHistoryTests()
    try:
        fixture.setUp()
        fixture.history(5000)
        with httpx.Client(timeout=30) as client:
            fixture.login(client)
            response = client.get(fixture.native + '/api/algorithm')
            print(json.dumps({'index': index, 'status': response.status_code, 'failures': failures, 'native_calls': dict(calls)}), flush=True)
            failures.clear()
            calls.clear()
    finally: fixture.doCleanups()
