# ABOUTME: Identifies the actual fixed-destination failure before metadata initialization.
# ABOUTME: Prints the exception without reading or returning environment contents.
from pathlib import Path
import sys
import traceback
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'tests'))
from test_memory_deny_hashes import MemoryDenyHashesTests
from lifeos_hook_bridge.memory_deny_hashes import publication_paths
from lifeos_hook_bridge.memory_service import MemoryService

test = MemoryDenyHashesTests()
test.setUp()
try:
    memory = test.fixture.fixture.memory
    print('database exists:', memory.database.exists())
    try:
        publication_paths(memory, MemoryService(test.fixture.configuration).scope(test.fixture.context))
    except Exception:
        traceback.print_exc()
finally:
    test.doCleanups()
