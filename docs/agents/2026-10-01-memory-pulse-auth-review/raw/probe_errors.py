import json,traceback
from fastapi.testclient import TestClient
from test_memory_pulse_auth import MemoryPulseAuthTests
c=MemoryPulseAuthTests();c.setUp()
try:
 def summary(r):return {'status':r.status_code,'cache_control':r.headers.get('cache-control'),'body':r.text,'etag_present':'etag' in r.headers}
 out={'anonymous':summary(c.client.get(c.endpoint+'snapshot'))}
 c.login()
 out['invalid_bearer']=summary(c.client.get(c.endpoint+'snapshot',headers={'Authorization':'Bearer invalid-synthetic-token'}))
 out['unsupported_view']=summary(c.client.get(c.endpoint+'graph'))
 out['unsupported_method']=summary(c.client.post(c.endpoint+'snapshot',json={}))
 out['scope_query']=summary(c.client.get(c.endpoint+'snapshot',params={'scope':'owner'}))
 memory=c.fixture.fixture.fixture.fixture.memory
 memory.database.write_bytes(b'Synthetic corrupt registry')
 try:c.client.get(c.endpoint+'snapshot')
 except Exception as e:out['registry_exception']={'class':type(e).__name__,'message':str(e)}
 with TestClient(c.app,raise_server_exceptions=False,cookies=c.client.cookies) as client:
  out['corrupt_registry']=summary(client.get(c.endpoint+'snapshot'))
 print(json.dumps(out,indent=2))
finally:c.doCleanups()
