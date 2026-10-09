# ABOUTME: Observes actual Conduit preparation and publication on synthetic managed sources.
# ABOUTME: Exercises later edits and process-death recovery without replacing native results.
import json
import os
from pathlib import Path
import sys

from lifeos_hook_bridge.memory_access import NativeMemory
from lifeos_hook_bridge.memory_context import parse_context
from lifeos_hook_bridge.memory_service import MemoryConfiguration, MemoryService
import lifeos_hook_bridge.memory_conduit_insight as insight

configuration = MemoryConfiguration(Path(sys.argv[1]))
mode = sys.argv[2]
context = parse_context(json.loads(sys.argv[3]))
root = Path(configuration.load()['root'])
service = MemoryService(configuration)
arguments = {'date': '2026-10-08', 'initialize': True}
prepared = service.native(context, 'conduit_prepare', arguments)
assert prepared['ok'], prepared
original = NativeMemory._native
observed = []


def native(memory, action, **values):
    result = original(memory, action, **values)
    if action == 'validate_source_batch' and observed and mode.startswith('projection-') and len(observed) == 1:
        observed.append(result)
        if mode == 'projection-authority': configuration.update(lambda value: value['accounts'].clear())
        elif mode == 'projection-source':
            path = root / 'LIFEOS/USER/CONDUIT/events/2026-10-08.jsonl'
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps({'ts': '2026-10-08T12:00:00Z', 'type': 'app-focus',
                'source': 'synthetic', 'app': 'SyntheticInsightLater'}) + '\n')
    if action == 'conduit_prepare' and not observed:
        observed.append(result)
        if mode == 'source':
            path = root / 'LIFEOS/USER/CONDUIT/events/2026-10-08.jsonl'
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps({'ts': '2026-10-08T12:00:00Z', 'type': 'app-focus', 'source': 'synthetic',
                'app': 'SyntheticInsightLater'}) + '\n')
        elif mode == 'destination':
            path = root / 'LIFEOS/USER/CONDUIT/insights/2026-10-08.json'
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('{"synthetic_later":true}')
        elif mode == 'authority': configuration.update(lambda value: value['accounts'].clear())
    return result


NativeMemory._native = native
original_publish = insight.publish


def publish(path, content):
    original_publish(path, content)
    if mode == 'interrupt': os._exit(73)


insight.publish = publish
value = {'date': arguments['date'], 'generatedAt': '2026-10-09T12:00:00Z', 'conduitVersion': '1.0.0',
    'level': 'low', 'model': '(none)', 'since': None, 'eventsConsidered': 0, 'skipped': True,
    'narrative': 'No activity captured yet today.', 'contentTypes': []}
result = (service.native(context, 'conduit_prepare', arguments) if mode.startswith('projection-') else
    service.native(context, 'conduit_publish', {**arguments, 'signature': prepared['signature'], 'value': value, 'reuse': False}))
assert observed
print(json.dumps(result))
