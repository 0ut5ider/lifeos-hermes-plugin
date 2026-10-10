# ABOUTME: Measures session consolidation after real rendering changes its input or caller permissions.
# ABOUTME: Terminates after native learning publication to verify journal recovery.
import json
import os
from pathlib import Path
import sys

from lifeos_hook_bridge.memory_access import NativeMemory
from lifeos_hook_bridge.memory_policy import SessionContext
from lifeos_hook_bridge.memory_service import MemoryConfiguration, MemoryService
import lifeos_hook_bridge.memory_session_harvest as harvest


configuration = MemoryConfiguration(Path(sys.argv[1]))
mode = sys.argv[2]
root = Path(configuration.load()['root'])
real_native = NativeMemory._native


def native(memory, action, **arguments):
    result = real_native(memory, action, **arguments)
    if action == 'session_harvest':
        if mode == 'authority':
            configuration.update(lambda value: value['accounts'].pop('chat-a:100'))
        elif mode == 'source':
            with (root / harvest.TRANSCRIPTS / 'native-session.jsonl').open('a') as stream:
                stream.write('\n')
    return result


NativeMemory._native = native
real_publish = harvest.publish


def publish(path, data):
    real_publish(path, data)
    if mode == 'interrupt':
        os._exit(73)


harvest.publish = publish
context = SessionContext('chat-a', '100', '200', 'private', ('owner',), 'local', 'native-session')
print(json.dumps(MemoryService(configuration).native(context, 'session_harvest',
    {'recent':20,'all':False,'session':None,'projects_dir':None,'dry_run':False,'mine':False})))
