import json
from datetime import datetime,timezone
from test_memory_pulse import MemoryPulseTests
from test_memory_native import OWNER
from lifeos_hook_bridge.memory_diagnostics import filter_report
c=MemoryPulseTests();c.setUp()
try:
 f=c.fixture.fixture.fixture
 saved=f.remember('RULE: SyntheticRetiredDynamicField','old-field-save','principal')
 f.memory.forget(OWNER,saved['reference'],'old-field-forget')
 stamp='2000-01-01T00:00:00Z'
 raw={'created_at':stamp,'error':'Synthetic harmless old text','nested':{'SyntheticRetiredDynamicField':1,'unrelated':2},'evidence':{'reviewer':{'status':'ok','ts':stamp}}}
 out=json.loads(filter_report(f.memory,OWNER,json.dumps(raw),stamp)['content'])
 print(json.dumps({'raw':raw,'governed':out},indent=2))
 assert out['created_at']==stamp and out['evidence']['reviewer']['status']=='ok'
 assert 'error' in out and 'Synthetic harmless old text' not in out['error']
 assert out['nested']=={'unrelated':2}
finally:c.doCleanups()
