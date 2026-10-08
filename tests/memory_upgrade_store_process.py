# ABOUTME: Observes actual upgrade planning and interrupts owner record or state publication.
# ABOUTME: Applies synthetic source, destination, and authority changes without replacing results.
import json
import os
from pathlib import Path
import sys

from lifeos_hook_bridge.memory_access import NativeMemory
from lifeos_hook_bridge.memory_context import parse_context
from lifeos_hook_bridge.memory_service import MemoryConfiguration,MemoryService
import lifeos_hook_bridge.memory_upgrades as upgrades

configuration=MemoryConfiguration(Path(sys.argv[1]))
context=parse_context(json.loads(sys.argv[2]))
mode=sys.argv[3]
original=NativeMemory._native
rendered=False
root=Path(configuration.load()['root'])
store=root/upgrades.ROOT
selected=None


def observe(memory,action,**arguments):
    global rendered,selected
    result=original(memory,action,**arguments)
    if action=='upgrade_store':
        rendered=True
        if result['publications']:selected=root/result['publications'][0]['path']
        if mode=='authority':configuration.update(lambda value:value['accounts'].clear())
        elif mode=='source':
            path=store/'records/synthetic-upgrade.md'
            path.write_text(path.read_text().replace('SyntheticUpgradeCurrentMarker','SyntheticUpgradeChangedMarker'))
        elif mode=='record':
            selected.parent.mkdir(parents=True,exist_ok=True)
            selected.write_text('Synthetic later record')
        elif mode=='state':(store/'.state.json').write_text('{"synthetic_later_state":true}')
    return result


NativeMemory._native=observe
original_publish=upgrades.publish


def publish(path,data,**arguments):
    original_publish(path,data,**arguments)
    if mode in ('interrupt-add-record','interrupt-status-record','interrupt-expiry-record') and path==selected:
        os._exit(73)
    if mode=='interrupt-add-state' and path.name=='.state.json':os._exit(73)
    if mode=='revoke-after-record' and path==selected:
        configuration.update(lambda value:value['accounts'].clear())


upgrades.publish=publish
action='status' if mode=='interrupt-status-record' else 'expire' if mode=='interrupt-expiry-record' else 'add'
arguments={'input':{'claim':'Synthetic governed upgrade process claim','source':'manual'}} if action=='add' else (
    {'id':'synthetic-upgrade','status':'accepted','opts':{'note':'Synthetic process review'}} if action=='status' else {})
result=MemoryService(configuration).native(context,'upgrade_store',{'action':action,'arguments':arguments,
    'request_id':'synthetic-upgrade-process-'+mode})
print(json.dumps({'rendered':rendered,'withheld':result.get('ok') is not True,'result':result}))
