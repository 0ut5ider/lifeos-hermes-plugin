# ABOUTME: Interrupts actual admitted Conduit publication after an event, retention deletion, or commit.
# ABOUTME: Leaves real owner journals and receipts for exact parent recovery checks.
import json
import os
from pathlib import Path
import sys

from lifeos_hook_bridge import memory_conduit_capture as capture
from lifeos_hook_bridge.memory_policy import SessionContext
from lifeos_hook_bridge.memory_service import MemoryConfiguration, MemoryService
from lifeos_hook_bridge.memory_transaction import MemoryTransaction

configuration,root,context,phase=sys.argv[1:]
root=Path(root)
original_publish=capture.publish
original_unlink=Path.unlink
original_finish=MemoryTransaction.finish

def publish(path,*arguments,**values):
    original_publish(path,*arguments,**values)
    if phase=='events' and path.is_relative_to(root/'LIFEOS/USER/CONDUIT/events'):
        os._exit(73)

capture.publish=publish

def unlink(path,*arguments,**values):
    original_unlink(path,*arguments,**values)
    if phase=='prune' and path==root/'LIFEOS/USER/CONDUIT/events/2000-01-01.jsonl':
        os._exit(73)

Path.unlink=unlink

def finish(transaction):
    if phase=='committed' and transaction.journal.exists():
        operation=json.loads(transaction.journal.read_text())
        if operation['request_id'].startswith('conduit-command-'):os._exit(73)
    original_finish(transaction)

MemoryTransaction.finish=finish
value=MemoryService(MemoryConfiguration(Path(configuration))).native(SessionContext(**json.loads(context)),
    'conduit_command',{'command':'capture','date':None})
print(json.dumps(value))
raise RuntimeError('The selected Conduit publication does not interrupt')
