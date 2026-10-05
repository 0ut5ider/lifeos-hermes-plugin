# ABOUTME: Changes source bytes, cache availability, or authority after actual scan rendering.
# ABOUTME: Retains the native renderer result and reports only the service delivery decision.
import json
from pathlib import Path
import sys

from lifeos_hook_bridge.memory_access import NativeMemory
from lifeos_hook_bridge.memory_service import MemoryConfiguration, MemoryService
from lifeos_hook_bridge.memory_policy import SessionContext


configuration = MemoryConfiguration(Path(sys.argv[1]))
mode = sys.argv[2]
root = Path(configuration.load()['root'])
original = NativeMemory._native
rendered = []


def native(memory, action, **arguments):
    result = original(memory, action, **arguments)
    if action == 'interview_scan':
        rendered.append(result)
        if mode == 'source':
            path = root / 'LIFEOS/USER/DIGITAL_ASSISTANT/DA_IDENTITY.md'
            path.write_text(path.read_text() + '\nSynthetic later scan edit\n')
        elif mode == 'authority':
            configuration.update(lambda value: value['accounts'].pop('chat-a:100'))
        elif mode == 'installation':
            configuration.update(lambda value: value.update(root=str(root.parent / 'foreign-root')))
        elif mode == 'evidence':
            path = root / 'LIFEOS/USER/CACHE/state-evidence.json'
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('{"synthetic_previous":"not used as a source"}')
    return result


NativeMemory._native = native
context = SessionContext('chat-a', '100', '200', 'private', ('owner',), 'local', 'native-session')
result = MemoryService(configuration).native(context, 'interview_scan', {'args': ['--json']})
assert len(rendered) == 1
assert rendered[0]['status'] == 0
assert json.loads(rendered[0]['stdout'])['count'] > 20
print(json.dumps(result))
