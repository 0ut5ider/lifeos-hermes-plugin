# ABOUTME: Runs actual context audit publication and recovery in separate processes.
# ABOUTME: Exits after native report publication to measure journal recovery without a fake writer.
from pathlib import Path
import json
import os
import sys

from lifeos_hook_bridge.memory_access import NativeMemory
from lifeos_hook_bridge.memory_policy import SessionContext
from lifeos_hook_bridge.memory_service import MemoryConfiguration, MemoryService


configuration = MemoryConfiguration(Path(sys.argv[1]))
mode = sys.argv[2]
values = json.loads(sys.argv[3])
values['participants'] = tuple(values['participants'])
context = SessionContext(**values)
root = Path(configuration.load()['root'])
if mode == 'recover':
    with NativeMemory(root)._transaction():
        pass
elif mode == 'exit':
    def trace(frame, event, argument):
        if (event == 'return' and frame.f_code.co_name == 'publish'
                and Path(frame.f_code.co_filename).name == 'memory_transaction.py'
                and Path(frame.f_locals['path']).name == 'AUDIT.md'):
            os._exit(73)
        return trace
    sys.settrace(trace)
    result = MemoryService(configuration).native(context, 'context_audit', {'root': str(root), 'json_output': False})
    print(json.dumps(result))
else:
    raise ValueError('Unknown synthetic audit process mode')
