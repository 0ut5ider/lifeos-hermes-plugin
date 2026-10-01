import json
from test_memory_pulse import MemoryPulseTests
from test_memory_native import OWNER
case=MemoryPulseTests(); case.setUp()
try:
    native=case.fixture.fixture.fixture
    old=native.remember('RULE: Synthetic PULSE baseline setting','old','principal')
    new=native.memory.correct(OWNER,old['reference'],'RULE: Synthetic PULSE baseline setting now revised','new')
    current=native.memory.get(OWNER,new['reference'])
    snapshot=case.snapshot()
    print(json.dumps({'old':old,'new':new,'current':current,'snapshot':snapshot},indent=2))
    assert snapshot['principalMemory']['entries']==[current['content']]
finally: case.doCleanups()
