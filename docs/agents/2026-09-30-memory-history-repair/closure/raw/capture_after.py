# ABOUTME: Saves successful real agent-turn outcomes and their synthetic HTTP requests.
# ABOUTME: Includes actual native recall, correction, forgetting, and unknown-author denial.
import json
from pathlib import Path
import sys

sys.path[:0] = [str(Path.cwd()),str(Path.cwd()/'tests')]
from test_memory_agent import MemoryAgentTests

for name in sorted(name for name in dir(MemoryAgentTests) if name.startswith('test_')):
    test = MemoryAgentTests()
    test.setUp()
    try:
        getattr(test,name)()
        print(json.dumps({'case':name,'outcome':test.outcome,'requests':test.fixture.fixture.received}),flush=True)
    finally:
        test.doCleanups()
