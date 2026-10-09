# ABOUTME: Measures native text admission for complete public skill scan inputs.
# ABOUTME: Records public source paths and validator differences without installed personal data.
import json
import os
from pathlib import Path
import shutil
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'tests'))
from test_memory_skill_hygiene import MemorySkillHygieneTests
from lifeos_hook_bridge import memory_skill_hygiene as module
from lifeos_hook_bridge.memory_service import MemoryService
case = MemorySkillHygieneTests()
case.setUp()
try:
    case.seed()
    source = Path(os.environ['LIFEOS_MEMORY_SOURCE']) / 'skills'
    shutil.copytree(source, case.skills, dirs_exist_ok=True)
    memory = case.fixture.fixture.memory
    service = MemoryService(case.fixture.configuration)
    scope = service.scope(case.fixture.context)
    rows = []
    native = memory._native('skill_hygiene_inventory', skill=None)
    batch, names = [], []
    def flush():
        accepted = memory._native('validate_source_batch', contents=batch)['accepted']
        for name, content, valid in zip(names, batch, accepted, strict=True):
            if not valid:
                rows.append({'path': name, 'bytes': len(content.encode()),
                    'controls': [{'offset': i, 'code': ord(char)} for i, char in enumerate(content)
                        if ord(char) < 32 and char not in '\t\r\n' or 127 <= ord(char) <= 159]})
        batch.clear(); names.clear()
    for name in native['files']:
        content = (case.skills / name).read_text()
        if sum(len(value.encode()) for value in batch) + len(content.encode()) > 1024 * 1024: flush()
        batch.append(content + '\n' + name)
        names.append(name)
    if batch: flush()
    error = None
    try:
        with memory._transaction() as connection:
            module.collect(memory, scope, connection, None, None, lambda: None)
    except Exception as failure: error = {'type': type(failure).__name__, 'message': str(failure)}
    observations = []
    original_collect = module.collect
    original_render = module.render
    def observe_collect(*args):
        value = original_collect(*args)
        observations.append({'stage': 'collect', 'value': value})
        return value
    def observe_render(*args):
        value = original_render(*args)
        observations.append({'stage': 'render', 'exit_code': value.returncode,
            'stdout': value.stdout, 'stderr': value.stderr})
        return value
    module.collect = observe_collect
    module.render = observe_render
    run_error = None
    try:
        admitted = case.fixture.configuration.load()
        module.run(memory, scope, args=['--json'],
            check_current=lambda: service._check_current_context(admitted, case.fixture.context, scope))
    except Exception as failure: run_error = {'type': type(failure).__name__, 'message': str(failure)}
    finally:
        module.collect = original_collect
        module.render = original_render
    collections = [row['value'] for row in observations if row['stage'] == 'collect']
    comparisons = {'runs': len(collections)}
    if len(collections) == 2:
        comparisons.update(equal=collections[0] == collections[1],
            selection_equal=collections[0][0] == collections[1][0],
            sorted_files_equal=sorted(collections[0][0]['files']) == sorted(collections[1][0]['files']),
            sorted_fingerprints_equal=sorted(collections[0][1]) == sorted(collections[1][1]))
    print(json.dumps({'files': len(native['files']), 'undeclared': [name for name in native['files'] if not module.declared('skills/' + name)], 'rejected': rows, 'collection_error': error, 'run_error': run_error, 'comparisons': comparisons, 'render': [row for row in observations if row['stage'] == 'render']}, indent=2))
finally: case.doCleanups()
