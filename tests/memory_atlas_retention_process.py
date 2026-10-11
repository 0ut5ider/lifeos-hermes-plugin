# ABOUTME: Interrupts an actual Atlas retention transaction after archive publication.
# ABOUTME: Leaves the recovery journal for the next independent owner process.
import json
import os
from pathlib import Path
import sys

from lifeos_hook_bridge import memory_atlas_sync
from lifeos_hook_bridge.memory_policy import SessionContext
from lifeos_hook_bridge.memory_service import MemoryConfiguration, MemoryService

original = memory_atlas_sync.publish
selected = sys.argv[3] if len(sys.argv) > 3 else 'archive-manifest.json'
def observe(path, content):
    original(path, content)
    label = 'archive-'+path.name if 'history' in path.parts else path.name
    if label == selected:
        os._exit(73)

memory_atlas_sync.publish = observe
configuration = MemoryConfiguration(Path(sys.argv[1]))
context = SessionContext(**json.loads(sys.argv[2]))
print(json.dumps(MemoryService(configuration).native(context, 'atlas_sync',
    {'collectors': ['gear', 'projects'], 'scope': 'full'})))
