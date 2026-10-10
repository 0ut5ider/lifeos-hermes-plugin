# ABOUTME: Observes actual native Menubar rendering before a source or authority change.
# ABOUTME: Records withholding without replacing native parser results or authenticated policy.
import json
import os
from pathlib import Path
import sys

from lifeos_hook_bridge.memory_access import NativeMemory
from lifeos_hook_bridge.memory_preferences import MemoryPreferences
from lifeos_hook_bridge.memory_service import MemoryConfiguration


configuration = MemoryConfiguration(Path(sys.argv[1]))
relative, mode = sys.argv[2:4]
root = Path(configuration.load()['root'])
original = NativeMemory._native
rendered = False


def observe(memory, action, **arguments):
    global rendered
    result = original(memory, action, **arguments)
    if action == 'menubar_view':
        rendered = True
        path = root / relative
        if mode == 'authority': configuration.update(lambda value: value['accounts'].clear())
        elif mode == 'created': path.write_text('{"synthetic":"SyntheticMenubarCreated"}')
        elif mode == 'profile':
            profile = configuration.path.parent
            content = configuration.path.read_bytes()
            profile.rename(profile.with_name('synthetic-profile-prior'))
            profile.mkdir()
            configuration.path.write_bytes(content)
        elif mode == 'descriptor':
            descriptor = os.open('/proc/self/fd/' + str(arguments['history_descriptor']), os.O_WRONLY)
            with os.fdopen(descriptor, 'wb') as stream: stream.write(b'Synthetic changed Menubar descriptor bytes')
        elif mode == 'source':
            before = path.stat()
            path.write_text(path.read_text().replace('SyntheticMenubarCurrent', 'SyntheticMenubarChanged'))
            os.utime(path, ns=(before.st_atime_ns, before.st_mtime_ns))
        elif mode == 'metadata':
            before = path.stat()
            replacement = path.with_suffix('.replacement')
            replacement.write_bytes(path.read_bytes())
            os.utime(replacement, ns=(before.st_atime_ns, before.st_mtime_ns))
            replacement.replace(path)
        else: raise ValueError('Choose a declared Menubar observation')
    return result


NativeMemory._native = observe
preferences = MemoryPreferences(configuration.path, root, Path(sys.executable),
    Path(__file__).resolve().parents[1] / 'lifeos_hook_bridge/memory_rpc.py')
try:
    preferences.life_response('/api/menubar', account='dashboard:basic:synthetic-owner')
except (PermissionError, RuntimeError, OSError, ValueError):
    print(json.dumps({'rendered': rendered, 'withheld': True}))
else:
    print(json.dumps({'rendered': rendered, 'withheld': False}))
