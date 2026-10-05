# ABOUTME: Identifies the actual service exception after native memory retirement.
# ABOUTME: Uses the same isolated synthetic fixture as the failing soul control.
from pathlib import Path
import sys
import traceback
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'tests'))
from test_memory_hermes_soul_retirement import MemoryHermesSoulRetirementTests
from lifeos_hook_bridge.memory_service import MemoryService

test = MemoryHermesSoulRetirementTests()
test.setUp()
try:
    test.retire('RULE: SyntheticUnrelatedSoulRetirement')
    fixture = test.fixture
    delegation = fixture.fixture.fixture.fixture
    try:
        result = MemoryService(delegation.configuration).native(delegation.context, 'hermes_soul',
            {'args': ['--stdout'], 'home': str(fixture.profile), 'workspace': str(fixture.workspace)})
        print(result)
    except Exception:
        traceback.print_exc()
finally:
    test.doCleanups()
