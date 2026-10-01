import json
from datetime import datetime,timezone
from test_memory_pulse import MemoryPulseTests
from test_memory_native import OWNER
c=MemoryPulseTests();c.setUp()
try:
 f=c.fixture.fixture.fixture
 old=f.remember('RULE: status','namespace-old','principal')
 assert f.memory.forget(OWNER,old['reference'],'namespace-forget')['status']=='committed'
 stamp=datetime.now(timezone.utc).isoformat()
 row={'ts':stamp,'overall':'ok','counts':{'ok':1},'evidence':{'reviewer':{'status':'ok'},'evidence':{'reviewer':{'status':1}}},'error':{'reviewer':{'status':1}}}
 (c.obs/'memory-health.jsonl').write_text(json.dumps(row)+'\n')
 out={v:c.snapshot(v) for v in ('health','snapshot')}
 print(json.dumps(out,indent=2))
 print(json.dumps({'fixed_health_status_preserved':out['health']['evidence']['reviewer']['status']=='ok',
 'nested_content_status_removed':'status' not in out['health']['evidence']['evidence']['reviewer'],
 'error_content_status_removed':'status' not in out['health']['error']['reviewer']}))
finally:c.doCleanups()
