# ABOUTME: Observes real Knowledge finding rendering and interrupts actual event publication.
# ABOUTME: Applies synthetic source, grant, and event-history changes without replacing native results.
import json
import os
from pathlib import Path
import sys

from lifeos_hook_bridge.memory_access import NativeMemory
from lifeos_hook_bridge.memory_service import MemoryConfiguration, MemoryService
from lifeos_hook_bridge.memory_policy import SessionContext
import lifeos_hook_bridge.memory_knowledge_conformance as conformance

configuration=MemoryConfiguration(Path(sys.argv[1]))
mode=sys.argv[2]
root=Path(configuration.load()['root'])
original=NativeMemory._native
rendered=False


def observe(memory,action,**values):
    global rendered
    result=original(memory,action,**values)
    if action=='knowledge_conformance':
        rendered=True
        if mode=='authority':configuration.update(lambda value:value['accounts'].clear())
        elif mode=='source':
            path=root/'LIFEOS/MEMORY/KNOWLEDGE/Research/synthetic-private-lint.md'
            path.write_text(path.read_text().replace('quality: 5','quality: 4'))
        elif mode=='history':
            with (root/conformance.EVENTS).open('ab') as stream:stream.write(b'{"type":"SyntheticConcurrentEvent"}\n')
    return result


NativeMemory._native=observe
original_publish=conformance.publish


def publish(path,data,**arguments):
    original_publish(path,data,**arguments)
    if mode=='interrupt':os._exit(73)


conformance.publish=publish
context=SessionContext('chat-a','100','200','private',('owner',),'local','native-session')
result=MemoryService(configuration).native(context,'knowledge_conformance',{'request_id':'synthetic-conformance-process'})
print(json.dumps({'rendered':rendered,'result':result}))
