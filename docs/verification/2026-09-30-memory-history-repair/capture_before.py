# ABOUTME: Records real correction and forget failures before context repair.
# ABOUTME: Keeps synthetic wire data and native status separate from test assertions.
import json
from pathlib import Path
import sys

sys.path[:0] = [str(Path.cwd()),str(Path.cwd()/'tests')]
from test_memory_agent import MemoryAgentTests
from test_memory_native import OWNER

for operation in ('correct','forget'):
    test = MemoryAgentTests()
    test.setUp()
    try:
        try:
            test.change_fact(operation)
            failure = ''
        except Exception as error:
            failure = str(error)
        print(json.dumps({'operation':operation,'failure':failure,
                          'stdout':getattr(test.fixture,'last_process_output',''),
                          'outcome':getattr(test.fixture,'last_outcome',None),
                          'requests':test.fixture.fixture.received,
                          'native_current':test.fixture.fixture.fixture.fixture.memory.recall(OWNER,'agent conversation claim')}),flush=True)
    finally:
        test.doCleanups()
