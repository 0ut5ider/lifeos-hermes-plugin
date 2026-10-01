# ABOUTME: Reruns the unchanged archived SDK child with real original-input admission.
# ABOUTME: Checks clean primary and compression transport after the auxiliary proof fix.
import json
from pathlib import Path
import sys

sys.path[:0] = [str(Path.cwd()),str(Path.cwd()/'tests')]
import test_memory_model_calls as fixture

fixture.PROGRAM = Path('docs/agents/2026-09-30-memory-history-repair/closure/raw/model_calls_with_proof.py').absolute()
for operation in ('primary','compression'):
    test = fixture.MemoryModelCallTests()
    test.setUp()
    try:
        result = test.run_call(operation)
        outcome = {'operation':operation,'returncode':result.returncode,'stdout':result.stdout,'stderr':result.stderr,
                   'requests':test.received}
        print(json.dumps(outcome),flush=True)
        assert result.returncode == 0, outcome
        assert result.stderr == '', outcome
        assert 'SYNTHETIC-MODEL-OK' in json.loads(result.stdout)['result'], outcome
        assert len(test.received) == 1, outcome
    finally:
        test.doCleanups()
