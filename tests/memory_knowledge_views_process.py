# ABOUTME: Observes native Knowledge view rendering before authority and source changes.
# ABOUTME: Interrupts actual index publication to verify the existing recovery journal.
import json
import os
from pathlib import Path
import sys

from lifeos_hook_bridge.memory_access import NativeMemory
from lifeos_hook_bridge.memory_policy import SessionContext
from lifeos_hook_bridge.memory_service import MemoryConfiguration, MemoryService
import lifeos_hook_bridge.memory_knowledge_views as views

configuration=MemoryConfiguration(Path(sys.argv[1]))
mode=sys.argv[2]
view=sys.argv[3]
root=Path(configuration.load()['root'])
real_native=NativeMemory._native
changed=False


def native(memory,action,**values):
    global changed
    result=real_native(memory,action,**values)
    if action=='knowledge_harvester_view' and not changed:
        if mode=='authority':configuration.update(lambda value:value['accounts'].clear())
        elif mode=='source':
            path=root/views.KNOWLEDGE/'Research/synthetic-view-first.md'
            path.write_text(path.read_text()+'\nSynthetic concurrent source edit\n')
        changed=True
    return result


NativeMemory._native=native
real_publish=views.publish


def publish(path,data,**options):
    real_publish(path,data,**options)
    if mode=='interrupt':os._exit(73)


views.publish=publish
context=SessionContext('chat-a','100','200','private',('owner',),'local','native-session')
print(json.dumps(MemoryService(configuration).native(context,'knowledge_view',{
    'view':view,'request_id':'synthetic-process-index'})))
