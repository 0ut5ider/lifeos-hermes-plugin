# ABOUTME: Measures exact native RPC byte limits using real synthetic configuration.
# ABOUTME: Checks the operation-specific exception without widening other request limits.
from test_memory_cortex_health import MemoryCortexHealthTests
from dataclasses import asdict
import subprocess,json,os
c=MemoryCortexHealthTests();c.setUp()
try:
 connector=json.loads((c.root/'LIFEOS/USER/CONFIG/memory-access.json').read_text())
 env=dict(os.environ,LIFEOS_MEMORY_CONTEXT=json.dumps(asdict(c.fixture.context)))
 for operation,limit,args in [('check_sources',131072,{}),('filter_diagnostic',3*1024*1024,{'content':'{}','timestamp':c.now})]:
  raw=json.dumps({'operation':operation,'arguments':args}).encode()
  for size in (limit,limit+1):
   wire=raw+b' '*(size-len(raw))
   result=subprocess.run(connector['command'],input=wire,env=env,capture_output=True,timeout=10)
   data=json.loads(result.stdout)
   assert result.returncode==0 and result.stderr==b''
   assert data['ok'] is (size==limit),(operation,size,data)
   print(json.dumps({'operation':operation,'bytes':size,'response':data}),flush=True)
 raw=json.dumps({'operation':'filter_source','arguments':{'content':'é'*70000,'timestamp':c.now}},ensure_ascii=False).encode()
 result=subprocess.run(connector['command'],input=raw,env=env,capture_output=True,timeout=10)
 data=json.loads(result.stdout);assert not data['ok'] and 'input limit' in data['message']
 print(json.dumps({'case':'multibyte','bytes':len(raw),'characters':len(raw.decode()),'response':data}),flush=True)
finally:c.doCleanups()
