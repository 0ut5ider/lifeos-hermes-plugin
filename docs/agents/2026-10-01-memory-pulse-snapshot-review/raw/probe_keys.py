import json
from test_memory_pulse import MemoryPulseTests
from test_memory_native import OWNER
case=MemoryPulseTests();case.setUp()
try:
    f=case.fixture.fixture.fixture
    marker='SyntheticPulseRetiredKey'
    old=f.remember('RULE: '+marker,'key-old','principal')
    assert f.memory.forget(OWNER,old['reference'],'key-forget')['status']=='committed'
    directory=case.obs/'reviewer-runs/2026-10-01T00-00-00-000Z';directory.mkdir(parents=True)
    (directory/'dispatch.log').write_text('Items: 1 (succeeded=1 failed=0)\nBy type: '+json.dumps({marker:1})+'\n')
    (case.obs/'review-state.json').write_text(json.dumps({'turn_count_since_last_review':1,'nested':{marker:'value'}}))
    output={view:case.snapshot(view) for view in ('runs','state','snapshot')}
    print(json.dumps(output,indent=2))
    assert marker not in json.dumps(output)
finally:case.doCleanups()
