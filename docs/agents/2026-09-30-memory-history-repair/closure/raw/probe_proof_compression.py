from pathlib import Path
import json,sys
sys.path[:0]=[str(Path.cwd()),str(Path.cwd()/'tests')]
import test_memory_model_calls as fixture
raw=Path.cwd()/'docs/agents/2026-09-30-memory-history-repair/closure/raw'
source=Path('tests/memory_model_calls.py').read_text()
source=source.replace('str(Path(__file__).parents[1])','str(Path.cwd())')
needle="runtime.admit(metadata, **settings['parent_route'], is_first_turn=settings['first'])"
assert needle in source
source=source.replace(needle,"runtime.admit(metadata, **settings['parent_route'], is_first_turn=settings['first'], user_message=settings['marker'])")
program=raw/'model_calls_with_proof.py';program.write_text(source)
fixture.PROGRAM=program
for operation in ('primary','compression'):
 case=fixture.MemoryModelCallTests();case.setUp()
 try:
  result=case.run_call(operation)
  print(json.dumps({'operation':operation,'returncode':result.returncode,'stdout':result.stdout,'stderr':result.stderr,'requests':case.received}),flush=True)
 finally:case.doCleanups()
