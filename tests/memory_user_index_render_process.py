# ABOUTME: Observes completed native index rendering before changing synthetic source or owner authority.
# ABOUTME: Executes the real publication service and reports whether it withholds the changed result.
import json
from pathlib import Path
import sys

from lifeos_hook_bridge.memory_access import NativeMemory
from lifeos_hook_bridge.memory_context import SessionContext
from lifeos_hook_bridge.memory_service import MemoryConfiguration, MemoryService

configuration = MemoryConfiguration(Path(sys.argv[1]))
context = SessionContext(**json.loads(sys.argv[2]))
mode = sys.argv[3]
original = NativeMemory._native
rendered = False


def observe(memory, action, **arguments):
    global rendered
    result = original(memory, action, **arguments)
    if action == 'user_index':
        rendered = True
        if mode == 'source':
            (memory.root / 'LIFEOS/USER/TELOS/GOALS.md').write_text('# SyntheticChangedIndexAfterRendering\n')
        elif mode == 'authority':
            configuration.update(lambda value: value['accounts'].clear())
    return result


NativeMemory._native = observe
try:
    result = MemoryService(configuration).native(context, 'user_index',
        {'query': None, 'publish_index': True, 'request_id': 'synthetic-index-render-' + mode})
except (PermissionError, RuntimeError, OSError, ValueError):
    withheld = True
else:
    withheld = not result['ok']
print(json.dumps({'rendered': rendered, 'withheld': withheld}))
