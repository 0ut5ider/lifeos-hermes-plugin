# ABOUTME: Measures fixed-path checks with a synthetic Hermes root alias.
# ABOUTME: Records actual checker failures without changing memory or native results.
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'tests'))
from test_memory_profile_alias import MemoryProfileAliasTests
from lifeos_hook_bridge.memory_derived_sync import _directory
from lifeos_hook_bridge.memory_deny_hashes import _marker
fixture = MemoryProfileAliasTests()
fixture.setUp()
try:
    memory = fixture.fixture.fixture.fixture.fixture.memory
    rows = []
    for name, operation in [('pulse-directory', lambda: _directory(memory, 'LIFEOS/PULSE/pages', system=True)),
                            ('hash-consumer-marker', lambda: _marker(memory)),
                            ('environment-publication', lambda: memory._publication_path('.env'))]:
        try:
            value = operation()
            rows.append({'check': name, 'accepted': True, 'value': str(value)})
        except Exception as error:
            rows.append({'check': name, 'accepted': False, 'error': type(error).__name__, 'message': str(error)})
    print(json.dumps({'root': str(memory.root), 'resolved_root': str(memory.root.resolve()), 'checks': rows}, indent=2))
finally:
    fixture.doCleanups()
