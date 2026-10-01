# ABOUTME: Checks whether missing or malformed proposal edit fields are reported truthfully.
# ABOUTME: Records actual governed projection and native output for synthetic queue rows.
import json
from test_memory_diagnostics import MemoryDiagnosticTests
from lifeos_hook_bridge.memory_service import MemoryService
c=MemoryDiagnosticTests();c.setUp()
try:
 s=MemoryService(c.fixture.configuration)
 for name,edit in [('object',{'synthetic':'invalid edit'}),('empty',''),('missing',None)]:
  row=c.proposal(edit)
  if name=='missing':del row['edit']
  path=c.write('pending-proposals.jsonl',[row])
  result=s.native(c.fixture.context,'read_diagnostic',{'path':str(path)})
  output=c.call('MemoryInsights.ts').stdout
  print(json.dumps({'case':name,'result':result,'stdout':output}),flush=True)
finally:c.doCleanups()
