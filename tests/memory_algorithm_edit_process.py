# ABOUTME: Terminates an actual native Algorithm edit after a selected owner file publication.
# ABOUTME: Leaves its journal for the parent test to verify multi-file interruption recovery.
import json
import os
from pathlib import Path
import sys
from lifeos_hook_bridge.memory_preferences import MemoryPreferences
import lifeos_hook_bridge.memory_algorithm_edit as edits

configuration, root, count = sys.argv[1:]
root = Path(root)
original = edits.publish
observed = 0

def interrupt(path, content):
    global observed
    result = original(path, content)
    if Path(path).is_relative_to(root / 'LIFEOS/ALGORITHM'):
        observed += 1
        if observed == int(count): os._exit(73)
    return result

edits.publish = interrupt
preferences = MemoryPreferences(Path(configuration), root, Path(sys.executable), Path(__file__).parents[1] / 'lifeos_hook_bridge/memory_mcp.py')
preferences.edit_algorithm('/api/algorithm-tab/doctrine',
    {'content': '# The Algorithm 3.2.1\n\n' + 'Synthetic recoverable doctrine claim. ' * 25,
        'bump': 'patch', 'note': 'Synthetic interrupted version update.'},
    account='dashboard:basic:synthetic-owner')
raise RuntimeError('The selected native publication does not interrupt')
