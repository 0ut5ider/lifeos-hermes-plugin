# ABOUTME: Observes actual native Algorithm preparation and private summary publication.
# ABOUTME: Exercises later changes and process-death recovery while retaining real native results.
import json
import os
from pathlib import Path
import sys
from lifeos_hook_bridge.memory_access import NativeMemory
from lifeos_hook_bridge.memory_context import parse_context
from lifeos_hook_bridge.memory_service import MemoryConfiguration, MemoryService
import lifeos_hook_bridge.memory_algorithm_summary as summary

configuration = MemoryConfiguration(Path(sys.argv[1]))
mode = sys.argv[2]
context = parse_context(json.loads(sys.argv[3]))
root = Path(configuration.load()['root'])
service = MemoryService(configuration)
prepared = service.native(context, 'algorithm_summary_prepare', {})
assert prepared['ok'], prepared
original = NativeMemory._native
observed = []


def mutate():
    if mode.endswith('authority'):
        configuration.update(lambda value: value['accounts'].clear())
    elif mode.endswith('source'):
        (root / 'LIFEOS/USER/CONFIG/OPERATIONAL_RULES.md').write_text('# Synthetic later rules\n')
    elif mode == 'destination':
        (root / summary.CACHE).write_text('{"overview":null,"files":{}}')


def native(memory, action, **values):
    result = original(memory, action, **values)
    if action == 'algorithm_summary_plan' and not observed:
        observed.append(result)
        if not mode.startswith('projection-'):
            mutate()
    elif action == 'validate_source_batch' and observed and mode.startswith('projection-') and len(observed) == 1:
        observed.append(result)
        mutate()
    return result


NativeMemory._native = native
original_publish = summary.publish


def publish(path, content):
    original_publish(path, content)
    if mode == 'interrupt':
        os._exit(73)


summary.publish = publish
card = next(row for row in prepared['plan']['files'] if row['id'] == 'operational-rules')
value = prepared['plan']['store']
value['files'][card['id']] = {'hash': card['hash'], 'generated_at': '2026-10-09T12:00:00Z',
    'markdown': 'Synthetic explanation of current rules.'}
result = (service.native(context, 'algorithm_summary_prepare', {}) if mode.startswith('projection-') else
    service.native(context, 'algorithm_summary_publish', {'signature': prepared['signature'], 'value': value}))
assert observed
print(json.dumps(result))
