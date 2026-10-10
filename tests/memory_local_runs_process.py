# ABOUTME: Interrupts actual LocalIntelligence diagnostic publication in a disposable owner process.
# ABOUTME: Leaves the native journal intact for recovery and later-edit comparisons.
import json
import os
from pathlib import Path
import sys
from lifeos_hook_bridge.memory_context import parse_context
from lifeos_hook_bridge.memory_service import MemoryConfiguration, MemoryService
import lifeos_hook_bridge.memory_transaction as transaction

configuration, mode, context, run_id = sys.argv[1:]
original = transaction.publish

def observed(path, data, **arguments):
    original(path, data, **arguments)
    if str(path).endswith('/' + run_id + '.log'):
        if mode == 'later': path.write_text('Synthetic later diagnostic edit')
        os._exit(73)

transaction.publish = observed
MemoryService(MemoryConfiguration(Path(configuration))).native(parse_context(json.loads(context)),
    'local_run_start', {'run_id': run_id})
