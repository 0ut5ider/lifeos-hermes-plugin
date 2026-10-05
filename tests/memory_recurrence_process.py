# ABOUTME: Measures recurrence collection and publication against actual later changes.
# ABOUTME: Terminates actual registry publication for separate journal recovery.
import json
import os
from pathlib import Path
import sys

from lifeos_hook_bridge.memory_access import NativeMemory
from lifeos_hook_bridge.memory_policy import SessionContext
from lifeos_hook_bridge.memory_service import MemoryConfiguration, MemoryService
import lifeos_hook_bridge.memory_recurrence as recurrence

configuration = MemoryConfiguration(Path(sys.argv[1]))
mode = sys.argv[2]
root = Path(configuration.load()['root'])
original = NativeMemory._native
changed = False


def native(memory, action, **arguments):
    global changed
    result = original(memory, action, **arguments)
    if not changed and (action == 'recurrence_append' or action == 'validate_source_batch' and mode in ('source', 'read-authority')):
        changed = True
        if mode == 'destination':
            (root / recurrence.REGISTRY).write_text('Synthetic later registry edit\n')
        elif mode in ('authority', 'read-authority'):
            configuration.update(lambda value: value['accounts'].pop('chat-a:100'))
        elif mode == 'source':
            (root / 'LIFEOS/MEMORY/OBSERVABILITY/tool-failures.jsonl').write_text('Synthetic later stream edit\n')
    return result


NativeMemory._native = native
original_publish = recurrence.publish


def publish(path, data):
    original_publish(path, data)
    if mode == 'interrupt':
        os._exit(73)


recurrence.publish = publish
context = SessionContext('chat-a', '100', '200', 'private', ('owner',), 'local', 'native-session')
operation = 'recurrence_sources' if mode in ('source', 'read-authority') else 'recurrence_append'
arguments = {'base': str(root / 'LIFEOS')}
if operation == 'recurrence_append':
    arguments.update(record={'ts': '2026-10-05T00:00:00Z', 'class_id': 'synthetic-class',
        'hypothesis_slug': 'synthetic', 'files': ['hooks/Synthetic.ts'], 'fixture': None}, request_id='recurrence-' + mode)
print(json.dumps(MemoryService(configuration).native(context, operation, arguments)))
