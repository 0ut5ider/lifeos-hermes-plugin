# ABOUTME: Changes current inputs after actual native Hermes soul rendering.
# ABOUTME: Interrupts actual publication between the soul and workspace outputs.
import json
import os
from pathlib import Path
import sys

from lifeos_hook_bridge.memory_access import NativeMemory
from lifeos_hook_bridge.memory_policy import SessionContext
from lifeos_hook_bridge.memory_service import MemoryConfiguration, MemoryService
import lifeos_hook_bridge.memory_hermes_soul as soul


configuration = MemoryConfiguration(Path(sys.argv[1]))
mode, output = sys.argv[2:4]
initial = configuration.load()
root = Path(initial['root'])
original = NativeMemory._native
rendered = []


def native(memory, action, **arguments):
    result = original(memory, action, **arguments)
    if action == 'hermes_soul_render':
        rendered.append(result)
        if mode == 'source':
            path = root / 'LIFEOS/USER/DIGITAL_ASSISTANT/DA_IDENTITY.md'
            path.write_text(path.read_text() + '\nSynthetic later identity edit\n')
        elif mode == 'authority':
            configuration.update(lambda value: value['accounts'].pop('chat-a:100'))
        elif mode == 'destination':
            (configuration.path.parent / 'SOUL.md').write_text('Synthetic later soul edit\n')
        elif mode == 'workspace':
            configuration.update(lambda value: value.update(hermes_workspace=str(root.parent / 'foreign-workspace')))
    return result


NativeMemory._native = native
original_publish = soul.publish


def publish(path, data):
    original_publish(path, data)
    if mode == 'interrupt':
        os._exit(73)


soul.publish = publish
context = SessionContext('chat-a', '100', '200', 'private', ('owner',), 'local', 'native-session')
result = MemoryService(configuration).native(context, 'hermes_soul', {
    'args': ['--stdout'] if output == 'stdout' else [],
    'home': str(configuration.path.parent), 'workspace': initial['hermes_workspace']})
assert len(rendered) == 1
assert 'Synthetic personality' in rendered[0]['soul']
print(json.dumps(result))
