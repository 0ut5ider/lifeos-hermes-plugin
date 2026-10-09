# ABOUTME: Observes real LocalIntelligence planning and publication before synthetic concurrent changes.
# ABOUTME: Tests process-death recovery after the dated digest write without replacing native results.
import json
import os
from pathlib import Path
import sys
from lifeos_hook_bridge.memory_access import NativeMemory
from lifeos_hook_bridge.memory_context import parse_context
from lifeos_hook_bridge.memory_service import MemoryConfiguration, MemoryService
import lifeos_hook_bridge.memory_transaction as transaction

configuration = MemoryConfiguration(Path(sys.argv[1]))
mode = sys.argv[2]
context = parse_context(json.loads(sys.argv[3]))
value = json.loads(sys.argv[4])
root = Path(configuration.load()['root'])
service = MemoryService(configuration)
prepared = service.native(context, 'local_refresh_prepare', {})
assert prepared['ok'], prepared
original = NativeMemory._native
observed = []


def native(memory, action, **arguments):
    result = original(memory, action, **arguments)
    if action == 'local_refresh_publication' and not observed:
        observed.append(result)
        if mode == 'source': (root / 'LIFEOS/USER/PRINCIPAL/PRINCIPAL_IDENTITY.md').write_text('# Synthetic changed identity\n')
        elif mode == 'destination':
            path = root / 'LIFEOS/USER/CUSTOMIZATIONS/SKILLS/LocalIntelligence/latest.json'
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('{"news":{"items":[]},"synthetic_later":true}')
        elif mode == 'authority': configuration.update(lambda config: config['accounts'].clear())
    return result


NativeMemory._native = native
original_publish = transaction.publish


def publish(path, content):
    original_publish(path, content)
    if mode == 'interrupt' and path.name == prepared['plan']['filename']:
        os._exit(73)


transaction.publish = publish
result = service.native(context, 'local_refresh_publish', {'signature': prepared['signature'], 'value': value})
assert observed
print(json.dumps(result))
