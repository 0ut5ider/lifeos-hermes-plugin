# ABOUTME: Changes synthetic hypothesis sources or caller authority after actual native rendering.
# ABOUTME: Reports whether the governed direct-list response withholds the stale result.
import json
from pathlib import Path
import sys

from lifeos_hook_bridge.memory_access import NativeMemory
from lifeos_hook_bridge.memory_context import parse_context
from lifeos_hook_bridge.memory_service import MemoryConfiguration,MemoryService

configuration=MemoryConfiguration(Path(sys.argv[1]))
context=parse_context(json.loads(sys.argv[2]))
mode=sys.argv[3]
original=NativeMemory._native
rendered=False


def observe(memory,action,**arguments):
    global rendered
    result=original(memory,action,**arguments)
    if action=='hypothesis_list':
        rendered=True
        if mode=='authority':configuration.update(lambda value:value['accounts'].clear())
        elif mode=='source':
            path=memory.root/'LIFEOS/MEMORY/WISDOM/FRAMES/_hypotheses/2026-10-08_synthetic-hypothesis.md'
            path.write_text(path.read_text().replace('SyntheticHypothesisCurrentMarker','SyntheticHypothesisChangedMarker'))
    return result


NativeMemory._native=observe
result=MemoryService(configuration).native(context,'hypothesis_list',{})
print(json.dumps({'rendered':rendered,'withheld':result.get('ok') is not True}))
