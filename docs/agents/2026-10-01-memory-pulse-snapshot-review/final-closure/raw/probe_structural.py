import json
from test_memory_pulse import MemoryPulseTests
from test_memory_native import OWNER
c=MemoryPulseTests();c.setUp()
try:
 f=c.fixture.fixture.fixture
 old=f.remember('RULE: status','struct-old','principal')
 assert f.memory.forget(OWNER,old['reference'],'struct-forget')['status']=='committed'
 (c.obs/'review-state.json').write_text(json.dumps({'pending_review':True,'reviewer':{'status':1},'nested':{'status':1}}))
 (c.obs/'pending-proposals.jsonl').write_text(json.dumps({'id':'synthetic-proposal','status':'pending','edit':'Synthetic current proposal','ts':'2026-10-01T00:00:00.000Z'})+'\n')
 raw=f.memory._native('pulse_snapshot',view='snapshot')['snapshot']
 projected=c.snapshot();state=c.snapshot('state')
 result={'raw_proposals':raw['proposalsRecent'],'projected_proposals':projected['proposalsRecent'],'snapshot_state':projected['reviewState'],'state':state}
 print(json.dumps(result,indent=2))
 print(json.dumps({'fixed_proposal_status_preserved':projected['proposalsRecent'][0].get('status')=='pending','dynamic_state_status_removed':'status' not in state['reviewer']}))
finally:c.doCleanups()
