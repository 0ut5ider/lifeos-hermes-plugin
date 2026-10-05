# ABOUTME: Measures hypothesis derivation against actual later source and authority changes.
# ABOUTME: Terminates grouped publication for separate transaction recovery.
import json
import os
from pathlib import Path
import sys

from lifeos_hook_bridge.memory_access import NativeMemory
from lifeos_hook_bridge.memory_policy import SessionContext
from lifeos_hook_bridge.memory_service import MemoryConfiguration, MemoryService
import lifeos_hook_bridge.memory_hypotheses as hypotheses

configuration = MemoryConfiguration(Path(sys.argv[1]))
mode = sys.argv[2]
root = Path(configuration.load()['root'])
original = NativeMemory._native


def native(memory, action, **arguments):
    result = original(memory, action, **arguments)
    if action == 'learning_hypotheses':
        if mode == 'source':
            (root / 'LIFEOS/MEMORY/LEARNING/SIGNALS/ratings.jsonl').write_text('Synthetic later ratings edit\n')
        elif mode == 'authority':
            configuration.update(lambda value: value['accounts'].pop('chat-a:100'))
        elif mode == 'destination':
            path = next(artifact['path'] for artifact in result['publications'] if artifact['path'].endswith('.md'))
            Path(path).write_text('Synthetic later hypothesis edit\n')
    return result


NativeMemory._native = native
original_publish = hypotheses.publish


def publish(path, data):
    original_publish(path, data)
    if mode == 'interrupt':
        os._exit(73)


hypotheses.publish = publish
context = SessionContext('chat-a', '100', '200', 'private', ('owner',), 'local', 'native-session')
print(json.dumps(MemoryService(configuration).native(context, 'learning_hypotheses', {
    'path': str(root / 'LIFEOS/MEMORY/LEARNING/SIGNALS/ratings.jsonl'), 'window': 7,
    'dry_run': False, 'no_inference': True, 'once_daily': False, 'request_id': 'hypotheses-' + mode})))
