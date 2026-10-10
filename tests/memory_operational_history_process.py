# ABOUTME: Observes anonymous operational snapshots after actual native history rendering.
# ABOUTME: Tests read-only descriptors, changed snapshots, and process-death cleanup.
import fcntl
import json
import os
from pathlib import Path
import sys

from lifeos_hook_bridge.memory_access import NativeMemory
from lifeos_hook_bridge.memory_preferences import MemoryPreferences
from lifeos_hook_bridge.memory_service import MemoryConfiguration


configuration = MemoryConfiguration(Path(sys.argv[1]))
root = Path(configuration.load()['root'])
original = NativeMemory._native
observed = {}


def observe(memory, action, **arguments):
    result = original(memory, action, **arguments)
    if (action == 'validate_source_batch' and sys.argv[2] in ('batch', 'metadata', 'authority')
            and not observed.get('validated')):
        observed['validated'] = True
        path = root / 'LIFEOS/MEMORY/STATE/work-events.jsonl'
        before = path.stat()
        if sys.argv[2] == 'authority': configuration.update(lambda value: value['accounts'].clear())
        elif sys.argv[2] == 'batch':
            path.write_text(path.read_text().replace('1/2', '2/2'))
            os.utime(path, ns=(before.st_atime_ns, before.st_mtime_ns))
        else:
            replacement = path.with_suffix('.replacement')
            replacement.write_bytes(path.read_bytes())
            os.utime(replacement, ns=(before.st_atime_ns, before.st_mtime_ns))
            replacement.replace(path)
    if action == 'operational_view':
        descriptor = arguments['history_descriptor']
        observed.update(rendered=True, anonymous=os.fstat(descriptor).st_nlink == 0,
            readonly=fcntl.fcntl(descriptor, fcntl.F_GETFL) & os.O_ACCMODE == os.O_RDONLY)
        if sys.argv[2] == 'exit':
            print(json.dumps(observed), flush=True)
            os._exit(86)
        elif sys.argv[2] == 'tamper':
            with open(f'/proc/self/fd/{descriptor}', 'wb') as stream: stream.write(b'Synthetic changed snapshot')
        elif sys.argv[2] == 'decode': pass
        elif sys.argv[2] not in ('batch', 'metadata', 'authority'): raise ValueError('Choose a declared history observation')
    return result


NativeMemory._native = observe
preferences = MemoryPreferences(configuration.path, root, Path(sys.executable),
    Path(__file__).resolve().parents[1] / 'lifeos_hook_bridge/memory_rpc.py')
try:
    preferences.life_response('/api/algorithm', account='dashboard:basic:synthetic-owner')
except (PermissionError, RuntimeError, OSError, ValueError) as error:
    observed['withheld'] = True
    if sys.argv[2] == 'decode':
        observed.update(error_type=type(error).__name__, start=getattr(error, 'start', None), end=getattr(error, 'end', None))
else:
    observed['withheld'] = False
print(json.dumps(observed))
