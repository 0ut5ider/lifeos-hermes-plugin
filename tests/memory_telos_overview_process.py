# ABOUTME: Observes actual native overview rendering before changing sources or owner authority.
# ABOUTME: Confirms that the owner response withholds a result from the changed snapshot.
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
    if action == 'telos_overview':
        rendered = True
        directory = root / 'LIFEOS/USER/TELOS'
        if mode == 'authority': configuration.update(lambda value: value['accounts'].clear())
        elif mode == 'source':
            path = directory / 'TELOS.md'
            path.write_text(path.read_text().replace('SyntheticLifeCurrentGoal', 'SyntheticChangedOverviewGoal'))
        elif mode == 'created': (directory / 'IDEAL_STATE/FINANCES.md').write_text('# Synthetic new finances\n')
        elif mode == 'metadata':
            path = directory / 'CURRENT_STATE/SNAPSHOT.md'
            replacement = path.with_suffix('.replacement')
            replacement.write_bytes(path.read_bytes())
            replacement.replace(path)
        else: raise ValueError('Choose a declared overview observation')
    return result


NativeMemory._native = observe
preferences = MemoryPreferences(configuration.path, root, Path(sys.executable),
    Path(__file__).resolve().parents[1] / 'lifeos_hook_bridge/memory_rpc.py')
try:
    preferences.life_response('/api/telos/overview', account='dashboard:basic:synthetic-owner')
except (PermissionError, RuntimeError, OSError, ValueError):
    print(json.dumps({'rendered': rendered, 'withheld': True}))
else:
    print(json.dumps({'rendered': rendered, 'withheld': False}))
