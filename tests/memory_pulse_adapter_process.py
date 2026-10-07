# ABOUTME: Changes PULSE inputs after actual native page schema validation.
# ABOUTME: Interrupts native page publication to verify recovery of the page and metadata pair.
import json
import os
from pathlib import Path
import sys

from lifeos_hook_bridge.memory_access import NativeMemory
from lifeos_hook_bridge.memory_policy import SessionContext
from lifeos_hook_bridge.memory_service import MemoryConfiguration, MemoryService
import lifeos_hook_bridge.memory_pulse_adapters as adapters


configuration = MemoryConfiguration(Path(sys.argv[1]))
mode = sys.argv[2]
root = Path(configuration.load()['root'])
page = root / adapters.DATA / 'synthetic.json'
value = json.loads(page.read_text())
value['data']['title'] = 'Synthetic replacement page'
original_native = NativeMemory._native
validated = []


def native(memory, action, **arguments):
    result = original_native(memory, action, **arguments)
    if action == 'pulse_validate_page':
        validated.append(result)
        if mode == 'source':
            (root / 'LIFEOS/USER/TELOS/BOOKS.md').write_text('Synthetic later collection source.\n')
        elif mode == 'private':
            (root / 'LIFEOS/USER/TELOS/BOOKS.md').write_text('<private>Synthetic later collection source.</private>\n')
        elif mode == 'authority':
            configuration.update(lambda current: current['accounts'].pop('chat-a:100'))
    return result


NativeMemory._native = native
original_publish = adapters.publish


def publish(path, data):
    original_publish(path, data)
    if mode == 'interrupt':
        os._exit(73)


adapters.publish = publish
context = SessionContext('chat-a', '100', '200', 'private', ('owner',), 'local', 'native-session')
result = MemoryService(configuration).native(context, 'pulse_data', {
    'action': 'write_page', 'identifier': 'synthetic', 'value': value})
assert validated == [{'valid': True}]
print(json.dumps(result))
