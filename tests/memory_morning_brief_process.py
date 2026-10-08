# ABOUTME: Observes actual native morning rendering before a controlled source or authority change.
# ABOUTME: Verifies that the current service withholds narration after the change.
import json
from pathlib import Path
import sys

from lifeos_hook_bridge.memory_access import NativeMemory
from lifeos_hook_bridge.memory_service import MemoryConfiguration,MemoryService
from lifeos_hook_bridge.memory_policy import SessionContext

configuration=MemoryConfiguration(Path(sys.argv[1]))
mode=sys.argv[2]
root=Path(configuration.load()['root'])
context=SessionContext(**json.loads(sys.argv[3]))
original=NativeMemory._native
rendered=False


def observe(memory,action,**arguments):
    global rendered
    result=original(memory,action,**arguments)
    if action=='morning_brief':
        rendered=True
        if mode=='authority':configuration.update(lambda value:value['accounts'].clear())
        elif mode=='source':
            path=root/'LIFEOS/USER/TELOS/GOALS.md'
            path.write_text(path.read_text().replace('Synthetic first goal','Synthetic changed goal'))
    return result


NativeMemory._native=observe
result=MemoryService(configuration).native(context,'morning_brief',{})
print(json.dumps({'rendered':rendered,'withheld':result.get('ok') is False}))
