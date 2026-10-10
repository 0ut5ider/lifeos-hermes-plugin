# ABOUTME: Observes actual native Knowledge rendering before a concurrent owner change or interruption.
# ABOUTME: Returns governed receipts and leaves interrupted publications for recovery tests.
import json
import os
from pathlib import Path
import sys

from lifeos_hook_bridge.memory_access import NativeMemory
from lifeos_hook_bridge.memory_policy import SessionContext
from lifeos_hook_bridge.memory_service import MemoryConfiguration, MemoryService
import lifeos_hook_bridge.memory_knowledge_harvest as harvest

configuration=MemoryConfiguration(Path(sys.argv[1]))
mode=sys.argv[2]
root=Path(configuration.load()['root'])
real_native=NativeMemory._native
changed=False


def native(memory,action,**values):
    global changed
    result=real_native(memory,action,**values)
    if action=='knowledge_harvest' and not changed:
        if mode=='authority':
            configuration.update(lambda value:value['accounts'].clear())
        elif mode=='source':
            (root/harvest.KNOWLEDGE/'_harvest-queue/synthetic.json').write_text(json.dumps({
                'title':'Synthetic concurrent source','content':'Synthetic concurrent source body','domain':'Ideas'}))
        elif mode=='new-source':
            (root/harvest.KNOWLEDGE/'_harvest-queue/later.json').write_text(json.dumps({
                'title':'Synthetic new source','content':'Synthetic new source body','domain':'Ideas'}))
        changed=True
    return result


NativeMemory._native=native
real_publish=harvest.publish


def publish(path,data,**options):
    real_publish(path,data,**options)
    if mode=='interrupt' and path.suffix=='.md':
        os._exit(73)


harvest.publish=publish
real_unlink=Path.unlink


def unlink(path,*arguments,**options):
    result=real_unlink(path,*arguments,**options)
    if mode=='interrupt-expiry' and path.parent.name in harvest.DOMAINS and path.parent.parent.name=='KNOWLEDGE':
        os._exit(73)
    return result


Path.unlink=unlink
context=SessionContext('chat-a','100','200','private',('owner',),'local','native-session')
print(json.dumps(MemoryService(configuration).native(context,'knowledge_harvest',{
    'source':'research','dry_run':False,'max_notes':5,'request_id':'synthetic-process-harvest'})))
