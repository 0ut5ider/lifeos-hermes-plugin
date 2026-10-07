# ABOUTME: Mutates derivative inputs after actual native tracking-state rendering.
# ABOUTME: Interrupts state publication to verify recovery of the state and log pair.
from dataclasses import asdict
import json
import os
from pathlib import Path
import subprocess
import sys
import time

from lifeos_hook_bridge.memory_access import NativeMemory
from lifeos_hook_bridge.memory_policy import SessionContext
from lifeos_hook_bridge.memory_service import MemoryConfiguration, MemoryService
import lifeos_hook_bridge.memory_derived_sync as sync


configuration = MemoryConfiguration(Path(sys.argv[1]))
mode = sys.argv[2]
root = Path(configuration.load()['root'])
context = SessionContext('chat-a', '100', '200', 'private', ('owner',), 'local', 'native-session')
service = MemoryService(configuration)
args = ['--force']
plan = service.native(context, 'derived_sync_plan', {'args': args})
assert plan['ok'] and len(plan['actions']) == 1
environment = dict(os.environ, HOME=str(root.parent), LIFEOS_MEMORY_CONTEXT=json.dumps(asdict(context)))
environment.pop('LIFEOS_MEMORY_INTERNAL', None)
logs = []
for action in plan['actions']:
    assert service.native(context, 'derived_sync_check', {'args': args, 'signature': plan['signature']})['ok']
    started = time.monotonic()
    result = subprocess.run(action['cmd'], env=environment, capture_output=True, text=True, timeout=40)
    assert result.returncode == 0 and result.stderr == '', result.stderr
    logs.append({'cmd': sync._command(action['cmd']), 'exit': result.returncode,
                 'ms': int((time.monotonic() - started) * 1000)})
original_native = NativeMemory._native
rendered = []


def native(memory, action, **values):
    result = original_native(memory, action, **values)
    if action == 'derived_sync_finish':
        rendered.append(result)
        if mode in ('source', 'private'):
            identity = root / 'LIFEOS/USER/PRINCIPAL/PRINCIPAL_IDENTITY.md'
            identity.write_text('# Synthetic principal\n<private>FixtureSurname FixtureGivenname</private>\n'
                                if mode == 'private' else identity.read_text() + 'Synthetic later sync edit\n')
        elif mode == 'authority':
            configuration.update(lambda value: value['accounts'].pop('chat-a:100'))
        elif mode == 'state':
            (root / sync.STATE).write_text('{"fileHashes":{},"lastRun":"2026-10-04T12:00:00.000Z"}\n')
        elif mode == 'log':
            (root / sync.LOG).write_text('{"ts":"2026-10-04T12:00:00.000Z","changed":[],"actions":[],"dryRun":false}\n')
    return result


NativeMemory._native = native
original_publish = sync.publish


def publish(path, data):
    original_publish(path, data)
    if mode == 'interrupt':
        os._exit(73)


sync.publish = publish
result = service.native(context, 'derived_sync_publish', {'args': args, 'signature': plan['signature'],
    'logs': logs, 'failed': [False] * len(logs)})
assert len(rendered) == 1
print(json.dumps(result))
