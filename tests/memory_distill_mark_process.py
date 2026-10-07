# ABOUTME: Changes actual distill inputs after native marking renders its state.
# ABOUTME: Interrupts real state publication to verify journal recovery.
import json
import os
from pathlib import Path
import sys

from lifeos_hook_bridge.memory_access import NativeMemory
from lifeos_hook_bridge.memory_policy import SessionContext
from lifeos_hook_bridge.memory_service import MemoryConfiguration, MemoryService
from lifeos_hook_bridge.memory_transaction import MemoryTransaction
import lifeos_hook_bridge.memory_distill as distill


configuration = MemoryConfiguration(Path(sys.argv[1]))
mode = sys.argv[2]
root = Path(configuration.load()['root'])
digest = root / 'LIFEOS/MEMORY/DIGESTS/2026-10-04-distill.md'
state = root / distill.STATE
original_native = NativeMemory._native
rendered = []
later = b'{"schema_version":1,"surfaced_slugs":{},"item_hashes":{},"last_run":"2000-01-01"}\n'
baseline = configuration.load()
original_prepare = MemoryTransaction.prepare


def prepare(transaction, *args, **kwargs):
    original_prepare(transaction, *args, **kwargs)
    if mode == 'reserved-authority':
        state.write_bytes(later)
        configuration.update(lambda value: value['accounts'].pop('chat-a:100'))


MemoryTransaction.prepare = prepare


def native(memory, action, **arguments):
    result = original_native(memory, action, **arguments)
    if action == 'distill_mark':
        rendered.append(result)
        if mode == 'state':
            state.write_bytes(later)
        elif mode == 'digest':
            digest.write_text('Synthetic later digest edit.\n')
        elif mode == 'authority':
            configuration.update(lambda value: value['accounts'].pop('chat-a:100'))
    return result


NativeMemory._native = native
original_publish = distill.publish


def publish(path, content):
    original_publish(path, content)
    if mode == 'interrupt':
        os._exit(73)


distill.publish = publish
context = SessionContext('chat-a', '100', '200', 'private', ('owner',), 'local', 'native-session')
result = MemoryService(configuration).native(context, 'distill_mark', {'path': str(digest)})
assert len(rendered) == 1
if mode == 'reserved-authority':
    configuration.update(lambda value: value.update(baseline))
    MemoryService(configuration).native(context, 'distill_read', {'args': ['status']})
print(json.dumps({'result': result, 'later_state_preserved': state.exists() and state.read_bytes() == later}))
