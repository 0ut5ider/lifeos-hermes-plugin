# ABOUTME: Reports the actual scan service result behind the native CLI refusal.
# ABOUTME: Uses an isolated synthetic fixture and preserves the native error detail.
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'tests'))
from test_memory_interview_scan import MemoryInterviewScanTests
from lifeos_hook_bridge.memory_service import MemoryService

test = MemoryInterviewScanTests()
test.setUp()
try:
    result = MemoryService(test.fixture.fixture.fixture.configuration).native(
        test.fixture.fixture.fixture.context, 'interview_scan', {'args': ['--json']})
    print(json.dumps(result, indent=2))
finally:
    test.doCleanups()
