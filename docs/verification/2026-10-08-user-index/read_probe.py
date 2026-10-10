# ABOUTME: Reports metadata-only failures from the synthetic current native user index operation.
# ABOUTME: Uses the same owner fixture and real native calculation as the HTTP gate.
from test_memory_user_index import MemoryUserIndexTests
from lifeos_hook_bridge.memory_preferences import MemoryPreferences
from pathlib import Path
import sys, traceback
fixture = MemoryUserIndexTests('test_all_native_index_slices_preserve_current_fields')
try:
    fixture.setUp()
    fixture.seed()
    memory = fixture.fixture.fixture.fixture.fixture.fixture.memory
    print('user_symlink', (fixture.root/'LIFEOS/USER').is_symlink())
    print('registry', memory._native('user_index_registry'))
    preferences = MemoryPreferences(fixture.fixture.configuration.path, fixture.root, Path(sys.executable),
        Path(__file__).resolve().parents[3]/'lifeos_hook_bridge/memory_rpc.py')
    result = preferences.life_response('/api/user-index',account='dashboard:basic:synthetic-owner')
    print('status', result[0]['status'])
except Exception:
    traceback.print_exc()
finally:
    fixture.doCleanups()
