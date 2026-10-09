# ABOUTME: Measures the actual native Telos template response at its directory boundary.
# ABOUTME: Records field and byte counts without returning another copy of synthetic source bodies.
import json
from test_memory_telos_template import MemoryTelosTemplateTests
from lifeos_hook_bridge.memory_service import MemoryService
from lifeos_hook_bridge.memory_history import project_value
from lifeos_hook_bridge.memory_operational_views import projection
from lifeos_hook_bridge.memory_telos_template import collect
case = MemoryTelosTemplateTests()
case.setUp()
try:
    for index in range(2030):
        (case.directory / f'extra-{index:04}.md').write_text('Safe bounded source\n')
    memory = case.fixture.fixture.memory
    scope = MemoryService(case.fixture.configuration).scope(case.fixture.context)
    with memory._transaction() as connection:
        sources, fingerprints = collect(memory, scope, connection)
        result = memory._native('telos_template_view', files=sources)
    fields = []
    project_value(result, lambda text: fields.append(text) or False)
    encoded = json.dumps(result)
    print(json.dumps({'files': len(result['files']), 'fields': len(fields), 'response_bytes': len(encoded.encode()),
        'default_projection_available': projection(encoded) is not None,
        'declared_projection_available': projection(encoded, field_limit=2048 * 8 + 1) is not None}, indent=2))
finally: case.doCleanups()
