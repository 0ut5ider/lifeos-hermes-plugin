# ABOUTME: Exercises real two-file distill publication and process-death recovery.
# ABOUTME: Changes declared inputs after native state rendering without replacing its result.
import json
import os
from pathlib import Path
import sys

from lifeos_hook_bridge.memory_access import NativeMemory
from lifeos_hook_bridge.memory_context import parse_context
from lifeos_hook_bridge.memory_service import MemoryConfiguration, MemoryService
import lifeos_hook_bridge.memory_distill as distill


configuration = MemoryConfiguration(Path(sys.argv[1]))
mode = sys.argv[2]
context = parse_context(json.loads(sys.argv[3]))
root = Path(configuration.load()['root'])
service = MemoryService(configuration)
prepared = service.native(context, 'distill_prepare', {'dryRun': False})
assert prepared['ok'], prepared
digest = root / 'LIFEOS/MEMORY/DIGESTS' / (prepared['date'] + '-distill.md')
state = root / distill.STATE
original_native = NativeMemory._native
rendered = []
later = b'{"schema_version":1,"surfaced_slugs":{},"item_hashes":{},"last_run":"2000-01-01"}\n'


def native(memory, action, **arguments):
    result = original_native(memory, action, **arguments)
    if action == 'distill_mark':
        rendered.append(result)
        if mode == 'authority':
            configuration.update(lambda value: value['accounts'].pop('chat-a:100'))
        elif mode == 'destination':
            state.write_bytes(later)
        elif mode == 'source':
            note = next((root / 'LIFEOS/MEMORY/KNOWLEDGE/Research').glob('*.md'))
            note.write_text(note.read_text() + '\nSynthetic later source edit.\n')
    return result


NativeMemory._native = native
original_publish = distill.publish


def publish(path, data):
    original_publish(path, data)
    if mode == 'interrupt':
        os._exit(73)


distill.publish = publish
print(json.dumps({'date': prepared['date']}), flush=True)
result = service.native(context, 'distill_publish', {'dryRun': False, 'date': prepared['date'],
    'signature': prepared['signature'], 'digest': '# Synthetic generated digest\n\n### Synthetic item\n\nSynthetic current observation.\n'})
assert len(rendered) == 1
print(json.dumps({'result': result, 'later_state_preserved': state.read_bytes() == later}))
