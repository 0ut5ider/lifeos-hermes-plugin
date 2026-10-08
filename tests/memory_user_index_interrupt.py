# ABOUTME: Interrupts actual synthetic index publication after its atomic file replacement.
# ABOUTME: Leaves the private recovery journal and registry reservation for a fresh process to recover.
import json
import os
from pathlib import Path
import sys
from lifeos_hook_bridge.memory_context import SessionContext
from lifeos_hook_bridge.memory_service import MemoryConfiguration, MemoryService
import lifeos_hook_bridge.memory_user_index_publish as publisher

configuration = MemoryConfiguration(Path(sys.argv[1]))
context = SessionContext(**json.loads(sys.argv[2]))
original = publisher.publish


def interrupt(path, data, **options):
    original(path, data, **options)
    if path.name == 'user-index.json': os._exit(86)


publisher.publish = interrupt
MemoryService(configuration).native(context, 'user_index',
    {'query': None, 'publish_index': True, 'request_id': 'synthetic-index-interrupted'})
raise SystemExit('The synthetic index publication did not reach its interruption point')
