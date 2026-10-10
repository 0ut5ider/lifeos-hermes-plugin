# ABOUTME: Interrupts the actual governed event append after its native file publication.
# ABOUTME: Leaves the owner recovery journal for a later real memory operation.
import os
from pathlib import Path
import sys

import lifeos_hook_bridge.memory_events as events
from lifeos_hook_bridge.memory_service import MemoryConfiguration,MemoryService
from lifeos_hook_bridge.memory_policy import SessionContext

configuration=MemoryConfiguration(Path(sys.argv[1]))
original=events.publish


def interrupt(path,data,**arguments):
    original(path,data,**arguments)
    os._exit(73)


events.publish=interrupt
context=SessionContext('chat-a','100','200','private',('owner',),'local','native-session')
MemoryService(configuration).native(context,'event_append',{
    'path':str(Path(configuration.load()['root'])/'LIFEOS/MEMORY/STATE/events.jsonl'),
    'event':{'type':'SyntheticInterrupted','source':'SyntheticEmitter'},
    'request_id':'synthetic-event-interrupt'})
