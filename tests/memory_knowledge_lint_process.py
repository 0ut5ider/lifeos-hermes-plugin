# ABOUTME: Observes an actual native lint render before changing synthetic authority or source bytes.
# ABOUTME: Reports whether the governed service withholds the completed private report.
import json
from pathlib import Path
import sys

from lifeos_hook_bridge.memory_access import NativeMemory
from lifeos_hook_bridge.memory_service import MemoryConfiguration, MemoryService
from lifeos_hook_bridge.memory_policy import SessionContext

configuration=MemoryConfiguration(Path(sys.argv[1]))
mode=sys.argv[2]
root=Path(configuration.load()['root'])
original=NativeMemory._native
rendered=False


def observe(memory,action,**values):
    global rendered
    result=original(memory,action,**values)
    if action=='knowledge_lint':
        rendered=True
        if mode=='authority':configuration.update(lambda value:value['accounts'].clear())
        elif mode=='source':
            path=root/'LIFEOS/MEMORY/KNOWLEDGE/Research/synthetic-private-lint.md'
            path.write_text(path.read_text().replace('invented-state','SyntheticConcurrentLintState'))
    return result


NativeMemory._native=observe
context=SessionContext('chat-a','100','200','private',('owner',),'local','native-session')
result=MemoryService(configuration).native(context,'knowledge_lint',{'json':False,'list':20,'directory':None})
print(json.dumps({'rendered':rendered,'result':result}))
