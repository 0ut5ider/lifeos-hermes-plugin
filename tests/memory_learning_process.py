# ABOUTME: Measures actual rating analysis against current source and authority changes.
# ABOUTME: Terminates actual report publication for separate transaction recovery.
import json
import os
from pathlib import Path
import sys

from lifeos_hook_bridge.memory_access import NativeMemory
from lifeos_hook_bridge.memory_policy import SessionContext
from lifeos_hook_bridge.memory_service import MemoryConfiguration, MemoryService
import lifeos_hook_bridge.memory_learning as learning

configuration = MemoryConfiguration(Path(sys.argv[1]))
mode = sys.argv[2]
initial = configuration.load()
root = Path(initial['root'])
original = NativeMemory._native


def native(memory, action, **arguments):
    result = original(memory, action, **arguments)
    if action == 'learning_ratings':
        if mode == 'source':
            (root / learning.SOURCE).write_text('Synthetic later ratings edit\n')
        elif mode == 'authority':
            configuration.update(lambda value: value['accounts'].pop('chat-a:100'))
        elif mode == 'destination':
            (root / learning.PREFIX / result['relative']).write_text('Synthetic later rating report edit\n')
    return result


NativeMemory._native = native
original_publish = learning.publish


def publish(path, data):
    original_publish(path, data)
    if mode == 'interrupt':
        os._exit(73)


learning.publish = publish
context = SessionContext('chat-a', '100', '200', 'private', ('owner',), 'local', 'native-session')
print(json.dumps(MemoryService(configuration).native(context, 'learning_ratings', {
    'path': str(root / learning.SOURCE), 'month': False, 'all': True,
    'dry_run': False, 'request_id': 'learning-process-' + mode})))
