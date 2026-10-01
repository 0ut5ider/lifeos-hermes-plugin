# ABOUTME: Checks clock metadata exceptions against native structured and encoded error data.
# ABOUTME: Uses actual remember/forget, native Cortex collection, and direct governed filtering.
from datetime import datetime,timezone
import json
from test_memory_cortex_health import MemoryCortexHealthTests
from test_memory_native import OWNER
from lifeos_hook_bridge.memory_service import MemoryService
c=MemoryCortexHealthTests();c.setUp()
try:
 stamp=datetime.now(timezone.utc).isoformat()
 saved=c.fixture.fixture.remember('RULE: '+stamp,'nested-clock','principal')
 assert saved['status']=='committed'
 c.fixture.fixture.memory.forget(OWNER,saved['reference'],'forget-nested-clock')
 c.now=datetime.now(timezone.utc).isoformat()
 for name,error in [('plain',stamp),('encoded',json.dumps({'ts':stamp,'message':stamp})),('structured',{'ts':stamp,'message':stamp})]:
  c.reviewer(error)
  result=c.call()
  print(json.dumps({'case':name,'retired':stamp,'result':result}),flush=True)
 fields={'ts':stamp,'error':{'ts':stamp,'message':stamp},'content':{'ts':stamp},'samples':[{'timestamp':stamp}], 'string':json.dumps({'ts':stamp})}
 result=MemoryService(c.fixture.configuration).native(c.fixture.context,'filter_diagnostic',{'content':json.dumps(fields),'timestamp':c.now})
 print(json.dumps({'case':'direct-shapes','retired':stamp,'result':result}),flush=True)
finally:c.doCleanups()
