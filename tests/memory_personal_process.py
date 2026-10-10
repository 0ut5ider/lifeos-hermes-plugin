# ABOUTME: Observes actual native personal module rendering before a source or authority change.
# ABOUTME: Records withholding without replacing native parser results or authenticated policy.
import json
import os
from pathlib import Path
import sys

from lifeos_hook_bridge.memory_access import NativeMemory
from lifeos_hook_bridge.memory_preferences import MemoryPreferences
from lifeos_hook_bridge.memory_service import MemoryConfiguration


configuration = MemoryConfiguration(Path(sys.argv[1]))
module, relative, mode = sys.argv[2:5]
root = Path(configuration.load()['root'])
original = NativeMemory._native
rendered = False


def observe(memory, action, **arguments):
    global rendered
    result = original(memory, action, **arguments)
    if action == 'personal_module_view':
        rendered = True
        path = root / relative
        if mode == 'authority': configuration.update(lambda value: value['accounts'].clear())
        elif mode == 'created': path.write_text('# Synthetic source created during rendering\n')
        elif mode == 'selection': path.rename(path.with_name('topology-snapshot-003.md'))
        elif mode == 'source':
            before = path.stat()
            path.write_text(path.read_text().replace('SyntheticPersonalModuleCurrent', 'SyntheticPersonalModuleChanged'))
            os.utime(path, ns=(before.st_atime_ns, before.st_mtime_ns))
        elif mode == 'metadata':
            before = path.stat()
            replacement = path.with_suffix('.replacement')
            replacement.write_bytes(path.read_bytes())
            os.utime(replacement, ns=(before.st_atime_ns, before.st_mtime_ns))
            replacement.replace(path)
        else: raise ValueError('Choose a declared personal module observation')
    return result


NativeMemory._native = observe
preferences = MemoryPreferences(configuration.path, root, Path(sys.executable),
    Path(__file__).resolve().parents[1] / 'lifeos_hook_bridge/memory_rpc.py')
try:
    preferences.life_response('/api/' + module, account='dashboard:basic:synthetic-owner')
except (PermissionError, RuntimeError, OSError, ValueError):
    print(json.dumps({'rendered': rendered, 'withheld': True}))
else:
    print(json.dumps({'rendered': rendered, 'withheld': False}))
