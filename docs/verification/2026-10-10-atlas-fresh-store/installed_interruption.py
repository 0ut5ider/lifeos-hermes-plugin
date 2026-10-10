# ABOUTME: Interrupts the installed Atlas operation after real database publication.
# ABOUTME: Leaves the existing publication journal for explicit acceptance recovery.
from dataclasses import asdict
import importlib
import json
import os
from pathlib import Path
import sys

stage = Path('/home/lifeos-hermes/migration/2026-10-09/daily-text-581d76a7')
prepared = json.loads((stage/'applications-prepared.json').read_text())
profile = Path(prepared['profile'])
sys.path.insert(0, str(profile/'plugins'))
module = lambda name: importlib.import_module('lifeos-hook-bridge.'+name)
context = module('memory_policy').SessionContext(**json.loads(sys.argv[1]))
sync = module('memory_atlas_sync')
original = sync.publish

def observed(path, content):
    original(path, content)
    if path.name == 'atlas.db':
        os._exit(73)

sync.publish = observed
configuration = module('memory_service').MemoryConfiguration(profile/'lifeos-memory.json')
print(json.dumps(module('memory_service').MemoryService(configuration).native(context, 'atlas_sync',
    {'collectors':['gear','projects'],'scope':'full'})))
