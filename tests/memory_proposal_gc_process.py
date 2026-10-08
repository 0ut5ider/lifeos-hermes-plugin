# ABOUTME: Measures proposal cleanup refusal after actual native rendering changes its source or owner.
# ABOUTME: Terminates after a real publication to exercise durable cleanup recovery.
import json
import os
from pathlib import Path
import sys

from lifeos_hook_bridge.memory_access import NativeMemory
from lifeos_hook_bridge.memory_policy import SessionContext
from lifeos_hook_bridge.memory_service import MemoryConfiguration, MemoryService
import lifeos_hook_bridge.memory_proposal_gc as cleanup


configuration = MemoryConfiguration(Path(sys.argv[1]))
mode = sys.argv[2]
root = Path(configuration.load()['root'])
real_native = NativeMemory._native


def native(memory, action, **arguments):
    result = real_native(memory, action, **arguments)
    if action == 'proposal_gc':
        if mode == 'authority':
            configuration.update(lambda value: value['accounts'].pop('chat-a:100'))
        elif mode == 'source':
            path = root / cleanup.TARGETS[0]
            path.write_text(path.read_text() + '\n- Synthetic concurrent owner edit.\n')
    return result


NativeMemory._native = native
real_publish = cleanup.publish


def publish(path, data):
    real_publish(path, data)
    if mode == 'interrupt':
        os._exit(73)


cleanup.publish = publish
context = SessionContext('chat-a', '100', '200', 'private', ('owner',), 'local', 'native-session')
print(json.dumps(MemoryService(configuration).native(context, 'proposal_gc',
    {'apply':True, 'auto':False, 'route':False})))
