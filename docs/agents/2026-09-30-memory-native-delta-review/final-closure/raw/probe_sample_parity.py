# ABOUTME: Verifies per-row projection retains native post-cursor counts and sample ordering.
# ABOUTME: Compares actual managed and unmanaged output using identical synthetic log bytes.
import json
from test_memory_delta import MemoryDeltaTests
from lifeos_hook_bridge.memory_service import MemoryService
f=MemoryDeltaTests();f.setUp()
try:
 f.remember('Synthetic parity setup','setup')
 def row(ts,adds,drops,writer='MemorySystem.add'):
  return {'ts':f'2026-09-30T00:00:{ts:02}Z','file':'LIFEOS/USER/PRINCIPAL/PRINCIPAL_MEMORY.md','updated_by':writer,'additions':adds,'evictions':drops}
 log=f.obs/'memory-writes.jsonl'
 old=row(1,['RULE: old a','RULE: old b'],['RULE: old drop'])
 log.write_text(json.dumps(old)+'\n')
 initial=f.call(standalone=True)
 cursor=f.obs/'memory-delta-cursor.json';before=cursor.read_bytes()
 rows=[old,row(2,['RULE: ignored writer'],['RULE: ignored drop'],'other-writer'),row(3,['RULE: SmokeTest ignored'],['RULE: smoke drop']),row(4,['RULE: new a','RULE: new b','RULE: new c'],['RULE: new drop','RULE: second drop']),row(5,['RULE: new d'],[])]
 log.write_text(''.join(json.dumps(r)+'\n' for r in rows))
 projected=MemoryService(f.fixture.configuration).native(f.fixture.context,'read_source',{'path':str(log)})
 managed=f.call(standalone=True)
 cursor.write_bytes(before);(f.root/'LIFEOS/USER/CONFIG/memory-access.json').unlink()
 unmanaged=f.call(standalone=True)
 print(json.dumps({'initial':initial,'projected':projected,'managed':managed,'unmanaged':unmanaged,'identical':managed==unmanaged}))
 assert managed==unmanaged
 assert '+4 learned' in managed and '−2 dropped' in managed
 assert 'new a' in managed and 'new b' in managed and 'new drop' in managed
 assert '"principal: RULE: new c"' not in managed and '"principal: RULE: new d"' not in managed and '"RULE: second drop"' not in managed
 assert 'old a' not in managed and 'ignored' not in managed and 'SmokeTest' not in managed
finally:f.doCleanups()
