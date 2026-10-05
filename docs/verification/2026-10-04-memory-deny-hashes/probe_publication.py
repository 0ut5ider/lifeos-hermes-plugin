# ABOUTME: Records actual operation receipts from cold hash publication attempts.
# ABOUTME: Exposes failure reasons without printing salt or environment bytes.
from pathlib import Path
import sys
import json
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'tests'))
from test_memory_deny_hashes import MemoryDenyHashesTests
from lifeos_hook_bridge.memory_access import NativeMemory
from lifeos_hook_bridge.memory_service import MemoryService

original = NativeMemory._operation
receipts = []
def operation(memory, *args, **kwargs):
    result = original(memory, *args, **kwargs)
    receipts.append(result)
    return result
NativeMemory._operation = operation
for index in range(5):
    test = MemoryDenyHashesTests()
    test.setUp()
    try:
        result = MemoryService(test.fixture.configuration).native(test.fixture.context, 'deny_hashes', {'args': []})
        print(json.dumps({'attempt': index, 'ok': result['ok'], 'receipts': receipts}))
        receipts = []
    finally:
        test.doCleanups()
