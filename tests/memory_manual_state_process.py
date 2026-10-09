# ABOUTME: Observes actual native state rendering and recoverable publication before controlled changes.
# ABOUTME: Reports withheld delivery and intentional process interruption with synthetic owner data.
import json
import os
from pathlib import Path
import sys

from lifeos_hook_bridge import memory_manual_state as state
from lifeos_hook_bridge.memory_policy import SessionContext
from lifeos_hook_bridge.memory_service import MemoryConfiguration, MemoryService

configuration = MemoryConfiguration(Path(sys.argv[1]))
data = json.loads(sys.argv[2])
data['participants'] = tuple(data['participants'])
context = SessionContext(**data)
mode = sys.argv[3]
root = Path(configuration.load()['root'])
original = state._render
rendered = False


def observe(memory, tool, args, contents):
    global rendered
    result = original(memory, tool, args, contents)
    rendered = True
    path = root / 'LIFEOS/USER/TELOS/CURRENT_STATE/ACTIVITY.md'
    if mode == 'authority': configuration.update(lambda value:value['accounts'].clear())
    elif mode == 'source':
        before = path.stat()
        path.write_bytes(path.read_bytes().replace(b'existing', b'altering'))
        os.utime(path,ns=(before.st_atime_ns,before.st_mtime_ns))
    elif mode == 'metadata':
        before = path.stat()
        replacement = path.with_suffix('.replacement')
        replacement.write_bytes(path.read_bytes())
        os.utime(replacement,ns=(before.st_atime_ns,before.st_mtime_ns))
        replacement.replace(path)
    elif mode == 'created': (root / state.QUEUE).write_text('')
    elif mode != 'publication-kill': raise ValueError('Choose a declared state observation')
    return result


state._render = observe
publish = state.publish

def observe_publication(path, content, **arguments):
    publish(path, content, **arguments)
    if mode == 'publication-kill' and path.is_relative_to(root): os._exit(71)


state.publish = observe_publication
args = ['--source','manual','--target','ACTIVITY','--json','{"name":"SyntheticManualProposal"}'] if mode == 'created' else ['--approve','synthetic-proposal-id']
tool = 'ProposeCurrentStateEntry.ts' if mode == 'created' else 'ApproveCurrentStateEntries.ts'
result = MemoryService(configuration).native(context,'manual_state',{'tool':tool,'args':args})
print(json.dumps({'rendered':rendered,'withheld':result.get('ok') is not True}))
