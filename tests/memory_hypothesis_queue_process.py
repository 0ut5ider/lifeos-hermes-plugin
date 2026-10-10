# ABOUTME: Observes actual native hypothesis queue rendering before synthetic authority or source changes.
# ABOUTME: Verifies the authenticated preference path withholds its result after that change.
import json
from pathlib import Path
import sys

from lifeos_hook_bridge.memory_access import NativeMemory
from lifeos_hook_bridge.memory_preferences import MemoryPreferences
from lifeos_hook_bridge.memory_service import MemoryConfiguration

configuration=MemoryConfiguration(Path(sys.argv[1]))
mode=sys.argv[2]
root=Path(configuration.load()['root'])
original=NativeMemory._native
rendered=False


def observe(memory,action,**arguments):
    global rendered
    result=original(memory,action,**arguments)
    if action=='hypothesis_view':
        rendered=True
        if mode=='authority':configuration.update(lambda value:value['accounts'].clear())
        elif mode=='source':
            path=root/'LIFEOS/MEMORY/WISDOM/FRAMES/_hypotheses/2026-10-08_synthetic-hypothesis.md'
            path.write_text(path.read_text().replace('SyntheticHypothesisCurrentMarker','SyntheticHypothesisChangedMarker'))
    return result


NativeMemory._native=observe
preferences=MemoryPreferences(configuration.path,root,Path(sys.executable),
    Path(__file__).resolve().parents[1]/'lifeos_hook_bridge/memory_rpc.py')
try:
    result=preferences.hypothesis_response('/api/hypotheses',account='dashboard:basic:synthetic-owner')
except (PermissionError,RuntimeError,OSError,ValueError):
    print(json.dumps({'rendered':rendered,'withheld':True}))
else:
    print(json.dumps({'rendered':rendered,'withheld':False,'result':result}))
