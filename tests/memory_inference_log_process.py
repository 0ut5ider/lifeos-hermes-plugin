# ABOUTME: Exercises actual inference-log conflict and process-death boundaries.
# ABOUTME: Changes destination bytes or authority without replacing publication results.
import json
import os
from pathlib import Path
import sys

from lifeos_hook_bridge.memory_policy import SessionContext
from lifeos_hook_bridge.memory_service import MemoryConfiguration, MemoryService
import lifeos_hook_bridge.memory_pulse_adapters as adapters

configuration = MemoryConfiguration(Path(sys.argv[1]))
mode = sys.argv[2]
root = Path(configuration.load()['root'])
target = root / adapters.INFERENCE_LOG
context = SessionContext('chat-a', '100', '200', 'private', ('owner',), 'local', 'native-session')
entry = {'ts': '2026-10-04T00:00:00.000Z', 'level': 'low', 'requested': 'haiku',
         'expected_tier': 'haiku', 'executed': 'synthetic-flashnext', 'downgraded': True, 'latency_ms': 10}
original_publish = adapters._publish
later = b'{"synthetic_later":"preserved"}\n'


def publication(*args, **kwargs):
    if mode == 'destination':
        target.write_bytes(later)
    elif mode == 'authority':
        configuration.update(lambda value: value['accounts'].pop('chat-a:100'))
    return original_publish(*args, **kwargs)


adapters._publish = publication
original_write = adapters.publish


def write(path, data):
    original_write(path, data)
    if mode == 'interrupt':
        os._exit(73)


adapters.publish = write
result = MemoryService(configuration).native(context, 'inference_log', {'entry': entry})
print(json.dumps({'result': result, 'later_preserved': target.read_bytes() == later}))
