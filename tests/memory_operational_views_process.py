# ABOUTME: Observes actual native operational rendering before changing sources or owner authority.
# ABOUTME: Confirms that owner responses withhold results from changed physical snapshots.
import json
from pathlib import Path
import sys

from lifeos_hook_bridge.memory_access import NativeMemory
from lifeos_hook_bridge.memory_preferences import MemoryPreferences
from lifeos_hook_bridge.memory_service import MemoryConfiguration


configuration = MemoryConfiguration(Path(sys.argv[1]))
mode = sys.argv[2]
root = Path(configuration.load()['root'])
original = NativeMemory._native
rendered = False


def observe(memory, action, **arguments):
    global rendered
    result = original(memory, action, **arguments)
    if action == 'operational_view':
        rendered = True
        path = root / 'LIFEOS/MEMORY/STATE/work.json'
        if mode == 'authority': configuration.update(lambda value: value['accounts'].clear())
        elif mode == 'source':
            path.write_text(path.read_text().replace('SyntheticOperationalCurrent', 'SyntheticOperationalChanged'))
        elif mode == 'created':
            (root / 'LIFEOS/MEMORY/STATE/work-events.jsonl').write_text('{"note":"SyntheticCreatedOperational"}\n')
        elif mode == 'metadata':
            replacement = path.with_suffix('.replacement')
            replacement.write_bytes(path.read_bytes())
            replacement.replace(path)
        else: raise ValueError('Choose a declared operational observation')
    return result


NativeMemory._native = observe
preferences = MemoryPreferences(configuration.path, root, Path(sys.executable),
    Path(__file__).resolve().parents[1] / 'lifeos_hook_bridge/memory_rpc.py')
try:
    preferences.life_response('/api/algorithm', account='dashboard:basic:synthetic-owner')
except (PermissionError, RuntimeError, OSError, ValueError):
    print(json.dumps({'rendered': rendered, 'withheld': True}))
else:
    print(json.dumps({'rendered': rendered, 'withheld': False}))
