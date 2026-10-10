# ABOUTME: Observes actual Atlas preparation and publication on disposable owner graphs.
# ABOUTME: Exercises later edits and process-death recovery without replacing native results.
import json
import os
from pathlib import Path
import sys
from lifeos_hook_bridge.memory_access import NativeMemory
from lifeos_hook_bridge.memory_context import parse_context
from lifeos_hook_bridge.memory_service import MemoryConfiguration, MemoryService
import lifeos_hook_bridge.memory_atlas_insight as insight

configuration = MemoryConfiguration(Path(sys.argv[1]))
mode = sys.argv[2]
context = parse_context(json.loads(sys.argv[3]))
root = Path(configuration.load()['root'])
service = MemoryService(configuration)
prepared = service.native(context, 'atlas_insight_prepare', {})
assert prepared['ok'], prepared
original = NativeMemory._native
observed = []


def mutate():
    if mode.endswith('authority'): configuration.update(lambda value: value['accounts'].clear())
    elif mode.endswith('source'):
        path = root / 'LIFEOS/USER/GEAR.md'
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('## Synthetic later gear\n')
    elif mode == 'destination':
        path = root / insight.CACHE
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('{"hash":"later","narrative":"Synthetic later edit","generated_at":"later"}')


def native(memory, action, **values):
    result = original(memory, action, **values)
    if action == 'atlas_insight_plan' and not observed:
        observed.append(result)
        if not mode.startswith('projection-'): mutate()
    elif action == 'validate_source_batch' and observed and mode.startswith('projection-') and len(observed) == 1:
        observed.append(result)
        mutate()
    return result


NativeMemory._native = native
original_publish = insight.publish


def publish(path, content):
    original_publish(path, content)
    if mode == 'interrupt': os._exit(73)


insight.publish = publish
value = {'hash': prepared['plan']['hash'], 'narrative': 'Synthetic counted device narrative.',
    'generated_at': '2026-10-09T12:00:00Z'}
result = (service.native(context, 'atlas_insight_prepare', {}) if mode.startswith('projection-') else
    service.native(context, 'atlas_insight_publish', {'signature': prepared['signature'], 'value': value}))
assert observed
print(json.dumps(result))
