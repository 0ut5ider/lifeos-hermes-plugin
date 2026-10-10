# ABOUTME: Observes actual native tab rendering before controlled source, timestamp, or authority changes.
# ABOUTME: Verifies the owner dashboard withholds the result without substituting native responses.
import json
import os
from pathlib import Path
import sys

from lifeos_hook_bridge.memory_access import NativeMemory
from lifeos_hook_bridge.memory_preferences import MemoryPreferences
from lifeos_hook_bridge.memory_service import MemoryConfiguration

configuration=MemoryConfiguration(Path(sys.argv[1]))
mode=sys.argv[2]
root=Path(configuration.load()['root'])
original=NativeMemory._native
rendered=False


def observe(memory,action,**arguments):
    global rendered
    result=original(memory,action,**arguments)
    if action=='tab_freshness_view':
        rendered=True
        path=root/'LIFEOS/USER/TELOS/TELOS.md'
        if mode=='authority':configuration.update(lambda value:value['accounts'].clear())
        elif mode=='source':path.write_text(path.read_text().replace('SyntheticTelosFreshnessMarker','SyntheticChangedFreshnessMarker'))
        elif mode=='timestamp':
            before=path.stat()
            os.utime(path,ns=(before.st_atime_ns,before.st_mtime_ns-86400000000000))
    return result


NativeMemory._native=observe
preferences=MemoryPreferences(configuration.path,root,Path(sys.executable),
    Path(__file__).resolve().parents[1]/'lifeos_hook_bridge/memory_rpc.py')
try:
    result=preferences.tab_freshness_response('/api/tab-freshness?tab=telos',account='dashboard:basic:synthetic-owner')
except (PermissionError,RuntimeError,OSError,ValueError):
    print(json.dumps({'rendered':rendered,'withheld':True}))
else:
    print(json.dumps({'rendered':rendered,'withheld':False,'result':result}))
