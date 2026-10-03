# ABOUTME: Checks operational status and dropped-entry reason paths against payload fields.
# ABOUTME: Uses real retirement records and the governed diagnostic RPC in a private fixture.
from datetime import datetime,timezone
import json
from test_memory_cortex_health import MemoryCortexHealthTests
from test_memory_native import OWNER
c=MemoryCortexHealthTests();c.setUp()
try:
 stamp=datetime.now(timezone.utc).isoformat()
 for i,claim in enumerate((stamp,'critical','failed','overlength')):
  saved=c.fixture.fixture.remember('RULE: '+claim,'metadata-'+str(i),'principal')
  assert saved['status']=='committed',saved
  c.fixture.fixture.memory.forget(OWNER,saved['reference'],'forget-metadata-'+str(i))
 fields={'overall':'critical','ts':stamp,'reviewer':{'status':'failed','ts':stamp,'error':{'status':'failed','ts':stamp,'reason':'overlength','overall':'critical'}},
         'evidence':{'reviewer':{'status':'failed','ts':stamp,'error':{'status':'failed','ts':stamp}}},
         'findings':[{'severity':'critical','message':'critical','detail':{'status':'failed','ts':stamp,'error':{'status':'failed','ts':stamp},'dropped':[{'reason':'overlength','entry':'overlength'}]}}],
         'dropped_invalid':[{'reason':'overlength','entry':'overlength'}],
         'samples':[{'status':'failed','ts':stamp,'reason':'overlength','overall':'critical'}]}
 response=c.rpc('filter_diagnostic',{'content':json.dumps(fields),'timestamp':datetime.now(timezone.utc).isoformat()})
 assert response['ok'],response
 report=json.loads(response['content'])
 assert report['overall']=='critical' and report['ts']==stamp
 for value in (report['reviewer'],report['evidence']['reviewer'],report['findings'][0]['detail']):
  assert value['status']=='failed' and value['ts']==stamp
  assert stamp not in json.dumps(value['error']) and 'failed' not in json.dumps(value['error'])
 assert report['findings'][0]['severity']=='critical' and 'critical' not in report['findings'][0]['message']
 for value in (report['dropped_invalid'][0],report['findings'][0]['detail']['dropped'][0]):
  assert value['reason']=='overlength' and 'overlength' not in value['entry']
 for claim in (stamp,'critical','failed','overlength'):assert claim not in json.dumps(report['samples'])
 print(json.dumps({'input':fields,'response':report}),flush=True)
finally:c.doCleanups()
