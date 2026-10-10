# ABOUTME: Terminates a real native Content run after its event append and before its receipt commits.
# ABOUTME: Leaves the owner journal for the parent to verify exact interrupted ledger recovery.
import os
from pathlib import Path
import sys
from lifeos_hook_bridge.memory_access import NativeMemory
from lifeos_hook_bridge.memory_preferences import MemoryPreferences

configuration, root = sys.argv[1:]
original = NativeMemory._native

def interrupt(memory, action, **values):
    result = original(memory, action, **values)
    if action == 'content_run_append': os._exit(73)
    return result

NativeMemory._native = interrupt
preferences = MemoryPreferences(Path(configuration), Path(root), Path(sys.executable),
    Path(__file__).parents[1] / 'lifeos_hook_bridge/memory_mcp.py')
preferences.content_action_response('/api/content/synthetic0/run', {'method': 'POST'},
    account='dashboard:basic:synthetic-owner')
raise RuntimeError('The selected Content append does not interrupt')
