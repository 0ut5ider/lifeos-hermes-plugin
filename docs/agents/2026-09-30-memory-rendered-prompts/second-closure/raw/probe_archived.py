from pathlib import Path
import sys,json
r=Path.cwd();sys.path[:0]=[str(r),str(r/'tests')]
import test_memory_model_calls as fixture
from test_memory_native import OWNER
f=fixture.MemoryModelCallTests();f.setUp()
try:
 marker='Synthetic removed cached model marker'
 saved=f.fixture.fixture.remember('RULE: '+marker,'cached-model','principal');f.fixture.fixture.memory.forget(OWNER,saved['reference'],'cached-model-forget')
 for variant in ['list-control','tuple-messages','tuple-blocks','generator-messages','extra-body']:
  fixture.PROGRAM=r/'docs/agents/2026-09-30-memory-rendered-prompts/raw'/('sdk-'+variant+'.py')
  (f.fixture.home/'SOUL.md').write_text('# Synthetic LifeOS\n\n'+marker+'\n')
  before=len(f.received);a=f.run_call('primary',refresh_after_load=True)
  print(json.dumps({'case':variant,'returncode':a.returncode,'new_requests':len(f.received)-before,'stdout':a.stdout,'stderr':a.stderr}),flush=True)
  assert a.returncode!=0 and len(f.received)==before
finally:f.doCleanups()
