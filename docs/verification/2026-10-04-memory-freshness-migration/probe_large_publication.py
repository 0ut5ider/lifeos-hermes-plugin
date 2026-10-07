# ABOUTME: Records actual native migration sizes and the real publication receipt.
# ABOUTME: Uses seven synthetic files below the supported per-file source limit.
import json
from pathlib import Path
import sys
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'tests'))
from test_memory_freshness_migration import MemoryFreshnessMigrationTests
from lifeos_hook_bridge.memory_access import NativeMemory
from lifeos_hook_bridge.memory_service import MemoryService
from lifeos_hook_bridge.memory_sources import CORPUS_LIMIT, SOURCE_LIMIT
fixture = MemoryFreshnessMigrationTests()
fixture.setUp()
records = []
try:
    for path in fixture.targets:
        prefix = '# Synthetic large migration body\n'
        path.write_text(prefix + 'x' * (240 * 1024 - len(prefix)) + '\n')
    real_native = NativeMemory._native
    real_operation = NativeMemory._operation
    def native(memory, action, **arguments):
        result = real_native(memory, action, **arguments)
        if action == 'freshness_migration':
            records.append({'source_count': len(arguments['sources']),
                'source_bytes': sum(len(source['content'].encode()) for source in arguments['sources']),
                'maximum_source_bytes': max(len(source['content'].encode()) for source in arguments['sources']),
                'source_limit': SOURCE_LIMIT, 'native_status': result['status'],
                'render_json_bytes': len(json.dumps(result).encode()), 'corpus_limit': CORPUS_LIMIT,
                'publication_count': len(result['publications'])})
        return result
    def operation(memory, scope, request_id, payload, callback):
        result = real_operation(memory, scope, request_id, payload, callback)
        records.append({'receipt': result})
        return result
    with patch.object(NativeMemory, '_native', native), patch.object(NativeMemory, '_operation', operation):
        result = MemoryService(fixture.fixture.fixture.configuration).native(fixture.fixture.fixture.context,
            'freshness_migration', {'dry_run': False, 'state': False})
    print(json.dumps({'result': result, 'measurements': records}, indent=2))
finally:
    fixture.doCleanups()
