# ABOUTME: Observes actual registered native delta output after explicit hot memory publication.
# ABOUTME: Uses synthetic label controls and checks hot mutations with a write-only grant.
from dataclasses import replace
import json
from pathlib import Path
import test_memory_delta as delta
import test_memory_native as native
from lifeos_hook_bridge.memory_access import HOT_FILES
out=Path(__file__).parent

def delta_case(control=False):
 f=delta.MemoryDeltaTests();f.setUp()
 try:
  marker='Synthetic current delta review marker'
  saved=f.remember(marker,'saved')
  log=f.obs/'memory-writes.jsonl'
  raw=log.read_text()
  if control:
   rows=[json.loads(line) for line in raw.splitlines()]
   for row in rows:row['updated_by']='MemorySystem.add'
   log.write_text(''.join(json.dumps(row)+'\n' for row in rows))
  output=f.call()
  return {'control_label':control,'receipt':saved,'original_log':raw,'observed_log':log.read_text(),'output':output,'learned_present':'+1 learned' in output}
 finally:f.doCleanups()

def grant(operation):
 f=native.NativeMemoryTests();f.setUp()
 try:
  saved=f.remember('RULE: Synthetic write-only target','target','principal')
  f.remember('RULE: Synthetic neighboring private fact','neighbor','principal')
  scope=replace(native.OWNER,read=(),writer='synthetic:blind-writer')
  path=f.root/HOT_FILES['principal'];before=path.read_text()
  args=[scope,saved['reference']]
  if operation=='correct':args.append('RULE: Synthetic blind replacement')
  args.append('blind-'+operation)
  receipt=getattr(f.memory,operation)(*args)
  return {'operation':operation,'read_grant':scope.read,'write_grant':scope.write,'receipt':receipt,'before':before,'after':path.read_text()}
 finally:f.doCleanups()

result={'delta':[delta_case(),delta_case(True)],'write_only_mutations':[grant('correct'),grant('forget')]}
(out/'delta-grants-results.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
