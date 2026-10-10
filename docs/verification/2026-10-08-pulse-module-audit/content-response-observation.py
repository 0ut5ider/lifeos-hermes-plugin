# ABOUTME: Measures the actual complete Content response and its decoded projection limits.
# ABOUTME: Retains scalar diagnostics without replacing native results or policy checks.
from datetime import datetime
import json
from pathlib import Path
import sys
from lifeos_hook_bridge.memory_access import NativeMemory
from lifeos_hook_bridge.memory_history import project_value
from lifeos_hook_bridge.memory_operational_views import projection
from lifeos_hook_bridge.memory_preferences import MemoryPreferences
from test_memory_content import MemoryContentTests

fixture = MemoryContentTests()
fixture.setUp()
original = NativeMemory._native
metrics = {}

def observe(memory, action, **arguments):
    result = original(memory, action, **arguments)
    if action == 'content_view':
        serialized = json.dumps(result)
        strings = []
        project_value(result, lambda text: strings.append(text) and False)
        metrics.update(native_items=len(result['body']['items']), response_bytes=len(serialized.encode()),
            decoded_fields=len(strings), full_projection_bytes=len(('\n'.join((serialized,json.dumps(result,ensure_ascii=False),*strings))).encode()),
            projection_available=projection(serialized) is not None)
    return result

NativeMemory._native = observe
try:
    fixture.seed(count=4001)
    preferences = MemoryPreferences(fixture.fixture.configuration.path, fixture.root, Path(sys.executable),
        Path('/home/outsider/Projects/Hermes_agent/LifeOS_plugin/lifeos_hook_bridge/memory_rpc.py'))
    try: preferences.life_response('/api/content', account='dashboard:basic:synthetic-owner')
    except (RuntimeError, PermissionError, ValueError, OSError) as error:
        metrics.update(withheld=True, reason=str(error))
    else: metrics.update(withheld=False)
    print(json.dumps(metrics, indent=2))
finally:
    NativeMemory._native = original
    fixture.doCleanups()
