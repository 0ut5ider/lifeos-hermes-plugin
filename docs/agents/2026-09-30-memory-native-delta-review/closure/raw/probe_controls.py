# ABOUTME: Checks current health projection and policy denial after the delta fix.
# ABOUTME: Records real service and native output from disposable synthetic fixtures.
import json
from datetime import datetime,timezone
from test_memory_delta import MemoryDeltaTests
from test_memory_native import OWNER
from lifeos_hook_bridge.memory_service import MemoryService
f=MemoryDeltaTests();f.setUp()
try:
 retired='Synthetic closure retired tern marker'
 saved=f.remember(retired,'tern');f.memory.forget(OWNER,saved['reference'],'forget')
 f.remember('Synthetic closure current gull marker','gull')
 service=MemoryService(f.fixture.configuration)
 log=f.obs/'memory-health.jsonl';ts=datetime.now(timezone.utc).isoformat()
 old={'ts':ts,'overall':'critical','findings':[{'severity':'critical','message':'Synthetic older finding'}]}
 for status in ['critical','warn','ok']:
  row={'ts':ts,'overall':status,'findings':[{'severity':status,'message':retired}]}
  log.write_text(json.dumps(old)+'\n'+json.dumps(row)+'\n')
  source=service.native(f.fixture.context,'read_source',{'path':str(log)})
  output=f.call(standalone=True)
  print(json.dumps({'case':'excluded_latest_'+status,'source':source,'output':output}))
  assert json.loads(source['content'])['overall']==status
  assert retired not in output and 'Synthetic older finding' not in output
  assert ('MEMORY HEALTH: CRITICAL' in output)==(status=='critical')
  if status=='critical':assert 'details are unavailable under the current policy' in output
 log.write_text(json.dumps(old)+'\n{malformed\n')
 output=f.call(standalone=True);print(json.dumps({'case':'malformed_latest_health','output':output}));assert 'Synthetic older finding' not in output
 write_log=f.obs/'memory-writes.jsonl';valid=write_log.read_text().splitlines()[-1];row=json.loads(valid)
 wrong=[]
 for field,value in [('ts','not-a-time'),('file',[]),('additions',[1]),('evictions',False)]:
  item=dict(row);item[field]=value;wrong.append(json.dumps(item))
 write_log.write_text('\n'.join(wrong+[valid])+'\n')
 cursor=f.obs/'memory-delta-cursor.json'
 if cursor.exists():cursor.unlink()
 output=f.call(standalone=True);print(json.dumps({'case':'malformed_rows_control','output':output}));assert '+1 learned' in output
 f.call()
 paths=[cursor,f.root/'LIFEOS/MEMORY/STATE/memory-inject/delta-session.json',f.root/'LIFEOS/MEMORY/STATE/delta-surface-heartbeat']
 before=[p.read_bytes() for p in paths]
 config=f.fixture.configuration.load();config['destinations']['chat-a:200']['projects']=['lab'];f.fixture.configuration.save(config)
 output=f.call();check=service.native(f.fixture.context,'check_sources',{})
 print(json.dumps({'case':'all_categories_restricted_projects','output':output,'check':check,'state_unchanged':before==[p.read_bytes() for p in paths]}))
 assert output=='' and check['ok'] is False and before==[p.read_bytes() for p in paths]
finally:f.doCleanups()
