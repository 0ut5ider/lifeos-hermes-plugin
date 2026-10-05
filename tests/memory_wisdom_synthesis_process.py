# ABOUTME: Measures actual Wisdom snapshot and report publication interleavings.
# ABOUTME: Changes sources or authority and terminates publication between the native report pair.
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
original = NativeMemory._native
changed = False


def native(memory, action, **arguments):
    global changed
    result = original(memory, action, **arguments)
    if action == 'wisdom_synthesis':
        if mode == 'source':
            (root / 'LIFEOS/MEMORY/WISDOM/FRAMES/communication.md').write_text('Synthetic later frame edit\n')
        elif mode == 'authority':
            configuration.update(lambda value: value['accounts'].pop('chat-a:100'))
        elif mode == 'destination':
            (root / 'LIFEOS/MEMORY/WISDOM/PRINCIPLES/verified.md').write_text('Synthetic later principles edit\n')
    if mode == 'frames-authority' and action == 'validate_source_batch' and not changed:
        changed = True
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
arguments = {'base': str(root / 'LIFEOS')}
operation = 'wisdom_frames'
if mode != 'frames-authority':
    operation = 'wisdom_synthesis'
    arguments.update(health=False, dry_run=False, request_id='wisdom-synthesis-' + mode)
print(json.dumps(MemoryService(configuration).native(context, operation, arguments)))
