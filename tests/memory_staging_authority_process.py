# ABOUTME: Revokes caller access after the actual native staged-index render completes.
# ABOUTME: Measures whether reviewed promotion still writes before reporting a refused result.
import json
import os
from pathlib import Path
import sys

from lifeos_hook_bridge.memory_access import NativeMemory
from lifeos_hook_bridge.memory_policy import SessionContext
from lifeos_hook_bridge.memory_service import MemoryConfiguration, MemoryService
import lifeos_hook_bridge.memory_staging as staging

configuration = MemoryConfiguration(Path(sys.argv[1]))
real_native = NativeMemory._native
revoked = False
renders = 0
mode = sys.argv[4] if len(sys.argv)>4 else 'authority'
root = Path(configuration.load()['root'])
source = root / staging.KNOWLEDGE / '_harvest-queue' / (sys.argv[2] + '.md')


def native(memory, action, **arguments):
    global revoked,renders
    result = real_native(memory, action, **arguments)
    if action == 'knowledge_indexes':
        renders += 1
        if mode == 'authority' and not revoked:
            configuration.update(lambda value: value['accounts'].pop('chat-a:100'))
            revoked = True
        elif renders == 2 and mode == 'source':
            source.write_text(source.read_text() + '\nSynthetic concurrent staging edit.\n')
        elif renders == 2 and mode == 'state':
            (root / staging.STATE).write_text(json.dumps({'lastHarvest':'2026-10-01T00:00:00Z',
                'harvestedPaths':['synthetic-later-source.md'],'totalHarvested':17}))
    return result


NativeMemory._native = native
real_plan = staging._rejection_plan
changed = False


def plan(memory,scope,target,all):
    global changed
    result = real_plan(memory,scope,target,all)
    if not changed:
        if mode == 'reject-authority':
            configuration.update(lambda value:value['accounts'].pop('chat-a:100'))
            changed = True
        elif mode == 'reject-source':
            source.write_text(source.read_text() + '\nSynthetic concurrent staging edit.\n')
            changed = True
    return result


staging._rejection_plan = plan
real_unlink = Path.unlink


def unlink(path,*arguments,**keywords):
    result = real_unlink(path,*arguments,**keywords)
    if mode == 'reject-interrupt' and path.suffix == '.md' and path.parent.parent.name == '_harvest-queue':
        os._exit(73)
    return result


Path.unlink = unlink
context = SessionContext('chat-a', '100', '200', 'private', ('owner',), 'local', 'native-session')
if mode.startswith('reject-'):
    result = MemoryService(configuration).native(context,'staged_reject',
        {'target':None if mode=='reject-interrupt' else sys.argv[2], 'all':mode=='reject-interrupt',
         'request_id':'reject-authority'})
else:
    result = MemoryService(configuration).native(context, 'staged_promote',
        {'target': sys.argv[2], 'all': False, 'project': '', 'signature': sys.argv[3],
         'request_id': 'promote-authority'})
print(json.dumps(result))
