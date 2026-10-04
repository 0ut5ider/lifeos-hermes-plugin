# ABOUTME: Measures whether a later excluded source edit survives timestamp refusal and recovery.
# ABOUTME: Calls the actual native renderer before adding synthetic private markup.
import json
from pathlib import Path
import sys
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'tests'))
from test_memory_freshness import MemoryFreshnessTests
from lifeos_hook_bridge.memory_access import NativeMemory
from lifeos_hook_bridge.memory_service import MemoryService
fixture = MemoryFreshnessTests()
fixture.setUp()
try:
    path = fixture.root / 'LIFEOS/USER/TELOS/TELOS.md'
    real_native = NativeMemory._native
    expected = path.read_text() + '\n<private>Synthetic later excluded edit</private>\n'
    def native(memory, action, **arguments):
        result = real_native(memory, action, **arguments)
        if action == 'freshness_write':
            path.write_text(expected)
        return result
    with patch.object(NativeMemory, '_native', native):
        result = MemoryService(fixture.fixture.configuration).native(fixture.fixture.context,
            'write_freshness', {'kind': 'context', 'path': str(path), 'by': 'synthetic-writer', 'slug': None})
    immediate = path.read_text()
    with fixture.memory._transaction():
        recovered = path.read_text()
    print(json.dumps({'result': result, 'expected': expected, 'immediate': immediate,
        'after_next_transaction': recovered, 'preserved': recovered == expected}, indent=2))
    sys.exit(0 if recovered == expected else 1)
finally:
    fixture.doCleanups()
