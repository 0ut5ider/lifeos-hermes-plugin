# ABOUTME: Observes actual native Conduit aggregation before changing its source or authority.
# ABOUTME: Checks withheld delivery and private descriptor integrity without replacing native results.
import json
import os
from pathlib import Path
import sys

from lifeos_hook_bridge.memory_access import NativeMemory
from lifeos_hook_bridge.memory_preferences import MemoryPreferences
from lifeos_hook_bridge.memory_service import MemoryConfiguration


configuration = MemoryConfiguration(Path(sys.argv[1]))
target, relative, mode = sys.argv[2:5]
root = Path(configuration.load()['root'])
original = NativeMemory._native
rendered = False


def observe(memory, action, **arguments):
    global rendered
    result = original(memory, action, **arguments)
    if action == 'conduit_view':
        rendered = True
        path = root / relative
        if mode == 'authority': configuration.update(lambda value: value['accounts'].clear())
        elif mode == 'created': path.write_text('{"project":"SyntheticConduitCreated"}\n')
        elif mode == 'descriptor':
            descriptor = os.open('/proc/self/fd/' + str(arguments['history_descriptor']), os.O_WRONLY)
            with os.fdopen(descriptor, 'wb') as stream: stream.write(b'Synthetic changed descriptor bytes')
        elif mode == 'selection': path.rename(path.with_name('2026-10-09.json'))
        elif mode == 'source':
            before = path.stat()
            path.write_text(path.read_text().replace('SyntheticConduitCurrent', 'SyntheticConduitChanged'))
            os.utime(path, ns=(before.st_atime_ns, before.st_mtime_ns))
        elif mode == 'metadata':
            before = path.stat()
            replacement = path.with_suffix('.replacement')
            replacement.write_bytes(path.read_bytes())
            os.utime(replacement, ns=(before.st_atime_ns, before.st_mtime_ns))
            replacement.replace(path)
        else: raise ValueError('Choose a declared Conduit observation')
    return result


NativeMemory._native = observe
preferences = MemoryPreferences(configuration.path, root, Path(sys.executable),
    Path(__file__).resolve().parents[1] / 'lifeos_hook_bridge/memory_rpc.py')
try:
    preferences.life_response(target, account='dashboard:basic:synthetic-owner')
except (PermissionError, RuntimeError, OSError, ValueError):
    print(json.dumps({'rendered': rendered, 'withheld': True}))
else:
    print(json.dumps({'rendered': rendered, 'withheld': False}))
