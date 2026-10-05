# ABOUTME: Measures actual Wisdom updates across rendering and publication boundaries.
# ABOUTME: Changes current sources or authority and terminates actual publication for recovery.
import json
import os
from pathlib import Path
import sys

from lifeos_hook_bridge.memory_access import NativeMemory
from lifeos_hook_bridge.memory_policy import SessionContext
from lifeos_hook_bridge.memory_service import MemoryConfiguration, MemoryService
import lifeos_hook_bridge.memory_wisdom as wisdom

configuration = MemoryConfiguration(Path(sys.argv[1]))
mode = sys.argv[2]
initial = configuration.load()
root = Path(initial['root'])
frame = root / 'LIFEOS/MEMORY/WISDOM/FRAMES/communication.md'
original = NativeMemory._native


def native(memory, action, **arguments):
    result = original(memory, action, **arguments)
    if action == 'wisdom_frame_update':
        if mode == 'source':
            frame.write_text('Synthetic later wisdom edit\n')
        elif mode == 'private':
            frame.write_text('<private>Synthetic later private wisdom edit</private>\n')
        elif mode == 'authority':
            configuration.update(lambda value: value['accounts'].pop('chat-a:100'))
    return result


NativeMemory._native = native
original_publish = wisdom.publish


def publish(path, data):
    original_publish(path, data)
    if mode == 'interrupt':
        os._exit(73)


wisdom.publish = publish
context = SessionContext('chat-a', '100', '200', 'private', ('owner',), 'local', 'native-session')
result = MemoryService(configuration).native(context, 'wisdom_frame_update', {
    'domain': 'communication', 'observation': 'Synthetic interrupted wisdom observation',
    'type': 'evolution', 'path': str(frame), 'request_id': 'wisdom-process-' + mode})
print(json.dumps(result))
