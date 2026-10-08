# ABOUTME: Revokes a real dashboard owner binding after native memory rendering completes.
# ABOUTME: Checks whether the preference response returns after the authenticated authority changes.
import json
from pathlib import Path
import sys

from lifeos_hook_bridge.memory_access import NativeMemory
from lifeos_hook_bridge.memory_preferences import MemoryPreferences
from lifeos_hook_bridge.memory_service import MemoryConfiguration

configuration=MemoryConfiguration(Path(sys.argv[1]))
view=sys.argv[2]
mode=sys.argv[3] if len(sys.argv)>3 else "revoke"
root=Path(configuration.load()['root'])
original=NativeMemory._native
rendered=False
expected={'wiki':'wiki_view','knowledge':'knowledge_view','pulse':'pulse_snapshot'}[view]


def observe(memory,action,**arguments):
    global rendered
    result=original(memory,action,**arguments)
    if action==expected:
        rendered=True
        if mode=='revoke':configuration.update(lambda value:value['accounts'].clear())
        elif mode=='configuration':configuration.update(lambda value:value['destinations'].clear())
    return result


NativeMemory._native=observe
preferences=MemoryPreferences(configuration.path,root,Path(sys.executable),
    Path(__file__).resolve().parents[1]/'lifeos_hook_bridge/memory_rpc.py')
try:
    if view=='wiki':result=preferences.wiki_response('/api/wiki',account='dashboard:basic:synthetic-owner')
    elif view=='knowledge':result=preferences.knowledge_response('/api/knowledge',account='dashboard:basic:synthetic-owner')
    else:result=preferences.pulse_response('snapshot',account='dashboard:basic:synthetic-owner')
except (PermissionError,RuntimeError,OSError,ValueError):
    print(json.dumps({'rendered':rendered,'withheld':True}))
else:
    print(json.dumps({'rendered':rendered,'withheld':False}))
