# ABOUTME: Reruns unchanged SDK reproduction children with complete declared dependencies.
# ABOUTME: Requires policy denial and zero requests rather than accepting an import failure.
from pathlib import Path
import json
import sys

repository = Path.cwd()
sys.path[:0] = [str(repository),str(repository/'tests')]
import test_memory_model_calls as model_fixture
from test_memory_native import OWNER

fixture = model_fixture.MemoryModelCallTests()
fixture.setUp()
try:
    marker = 'Synthetic removed cached model marker'
    saved = fixture.fixture.fixture.remember('RULE: '+marker,'cached-model','principal')
    fixture.fixture.fixture.memory.forget(OWNER,saved['reference'],'cached-model-forget')
    for variant in ('list-control','tuple-messages','tuple-blocks','generator-messages','extra-body'):
        model_fixture.PROGRAM = repository/'docs/agents/2026-09-30-memory-rendered-prompts/raw'/('sdk-'+variant+'.py')
        (fixture.fixture.home/'SOUL.md').write_text('# Synthetic LifeOS\n\n'+marker+'\n')
        before = len(fixture.received)
        result = fixture.run_call('primary',refresh_after_load=True)
        wire = fixture.received[before:]
        print(json.dumps({'case':variant,'returncode':result.returncode,'requests':len(wire),
                          'stdout':result.stdout,'stderr':result.stderr,'wire':wire}),flush=True)
        assert result.returncode != 0 and not wire
        assert ('materialized' if variant=='generator-messages' else 'model system prompt') in result.stderr
finally:
    fixture.doCleanups()
