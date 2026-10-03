# ABOUTME: Exercises malformed and retirement edge cases of the native delta surface.
# ABOUTME: Uses native fixtures, real source policy, and actual Bun output.
import json
from datetime import datetime,timezone
from test_memory_delta import MemoryDeltaTests
for case in ['long_retired','malformed_before_control','health_older_replay']:
 f=MemoryDeltaTests();f.setUp()
 try:
  saved=f.remember('synthetic review duck marker with a long trailing retired phrase past the sample cut off','long')
  f.memory.forget(__import__('test_memory_native').OWNER,saved['reference'],'forget')
  f.remember('synthetic review current gull marker','gull')
  log=f.obs/'memory-writes.jsonl';rows=log.read_text().splitlines()
  if case=='long_retired':
   retired=json.loads(rows[0]);retired['ts']=datetime.now(timezone.utc).isoformat();log.write_text(json.dumps(retired)+'\n'+rows[-1]+'\n')
  elif case=='malformed_before_control':
   wrong=json.loads(rows[-1]);wrong['additions']='synthetic wrong shape';log.write_text(json.dumps(wrong)+'\n'+rows[-1]+'\n')
  else:
   health=f.obs/'memory-health.jsonl';ts=datetime.now(timezone.utc).isoformat()
   health.write_text(json.dumps({'ts':ts,'overall':'critical','findings':[{'severity':'critical','message':'synthetic older critical marker'}]})+'\n'+json.dumps({'ts':ts,'overall':'ok','findings':[{'severity':'ok','message':'synthetic review duck marker with a long trailing retired phrase past the sample cut off'}]})+'\n')
  try:out=f.call();print(json.dumps({'case':case,'output':out}))
  except AssertionError as e:print(json.dumps({'case':case,'observed_fixture_assertion':str(e)}))
 finally:f.doCleanups()
