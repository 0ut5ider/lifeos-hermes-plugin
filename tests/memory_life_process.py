# ABOUTME: Observes actual native Life rendering before changing synthetic sources or owner authority.
# ABOUTME: Checks that the authenticated preference operation withholds the rendered response.
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
    if action == 'life_view':
        rendered = True
        if mode == 'authority': configuration.update(lambda value: value['accounts'].clear())
        elif mode == 'source':
            path = root / 'LIFEOS/USER/TELOS/GOALS.md'
            path.write_text(path.read_text().replace('SyntheticLifeCurrentGoal', 'SyntheticLifeChangedGoal'))
    return result


NativeMemory._native = observe
preferences = MemoryPreferences(configuration.path, root, Path(sys.executable),
    Path(__file__).resolve().parents[1] / 'lifeos_hook_bridge/memory_rpc.py')
try:
    result = preferences.life_response('/api/life/home', account='dashboard:basic:synthetic-owner')
except (PermissionError, RuntimeError, OSError, ValueError):
    print(json.dumps({'rendered': rendered, 'withheld': True}))
else:
    print(json.dumps({'rendered': rendered, 'withheld': False, 'result': result}))
