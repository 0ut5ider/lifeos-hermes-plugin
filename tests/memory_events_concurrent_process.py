# ABOUTME: Starts an actual native event emitter while a finding transaction holds the owner lock.
# ABOUTME: Verifies that the child waits for committed publication and retains both event records.
from dataclasses import asdict
import json
import os
from pathlib import Path
import subprocess
import sys
import time

import lifeos_hook_bridge.memory_knowledge_conformance as conformance
from lifeos_hook_bridge.memory_service import MemoryConfiguration,MemoryService
from lifeos_hook_bridge.memory_policy import SessionContext

configuration=MemoryConfiguration(Path(sys.argv[1]))
root=Path(configuration.load()['root'])
context=SessionContext('chat-a','100','200','private',('owner',),'local','native-session')
original=conformance.publish
child=None
marker=root.parent/'synthetic-event-attempt'
waiting=False


def observe(path,data,**arguments):
    global child,waiting
    original(path,data,**arguments)
    script=('import {writeFileSync} from "node:fs"; import {appendEvent} from '+
        json.dumps(str(root/'hooks/lib/events.ts'))+';writeFileSync('+json.dumps(str(marker))+',"ready");'+
        'appendEvent({type:"SyntheticAfterFinding",source:"SyntheticEmitter"});')
    environment=dict(os.environ,HOME=str(root.parent),LIFEOS_DIR=str(root/'LIFEOS'),
        LIFEOS_MEMORY_CONTEXT=json.dumps(asdict(context)))
    environment.pop('LIFEOS_MEMORY_INTERNAL',None)
    child=subprocess.Popen(['bun','--no-install','-e',script],env=environment,
        stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    deadline=time.monotonic()+5
    while not marker.exists() and time.monotonic()<deadline:
        time.sleep(.01)
    if not marker.exists():raise RuntimeError('The actual emitter did not reach its append')
    time.sleep(.1)
    waiting=child.poll() is None


conformance.publish=observe
result=MemoryService(configuration).native(context,'knowledge_conformance',{'request_id':'synthetic-event-concurrency'})
if child is None:raise RuntimeError('The finding transaction did not publish')
output,error=child.communicate(timeout=40)
print(json.dumps({'result':result,'waiting':waiting,'child_code':child.returncode,'output':output,'error':error}))
