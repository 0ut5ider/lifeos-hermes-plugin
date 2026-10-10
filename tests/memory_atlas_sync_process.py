# ABOUTME: Interrupts real Atlas graph publication in a disposable managed store.
# ABOUTME: Changes sources or owner authority after a native database publication.
import json
import os
from pathlib import Path
import sys

from lifeos_hook_bridge import memory_atlas_sync
from lifeos_hook_bridge.memory_policy import SessionContext
from lifeos_hook_bridge.memory_service import MemoryConfiguration, MemoryService


configuration = MemoryConfiguration(Path(sys.argv[1]))
context = SessionContext(**json.loads(sys.argv[2]))
mode = sys.argv[3]
root = Path(configuration.load()['root'])
original = memory_atlas_sync.publish

def observed_publish(path, content):
    original(path, content)
    if path.name != 'atlas.db':
        return
    if mode == 'interrupt':
        os._exit(73)
    if mode == 'source':
        (root/'LIFEOS/USER/GEAR.md').write_text('# Synthetic Atlas later source\n')
    elif mode == 'authority':
        configuration.update(lambda value: value['accounts'].clear())
    else:
        raise ValueError('Choose a declared Atlas process boundary')

memory_atlas_sync.publish = observed_publish
print(json.dumps(MemoryService(configuration).native(context, 'atlas_sync',
    {'collectors': ['gear', 'projects'], 'scope': 'full'})))
