from pathlib import Path
import sys,json
sys.path[:0]=[str(Path.cwd()),str(Path.cwd()/'tests')]
from test_memory_model_calls import MemoryModelCallTests
f=MemoryModelCallTests();f.setUp()
try:
 (f.fixture.home/'SOUL.md').write_text('# Synthetic allowed public constitution\n')
 for variant in ('tuple-messages','tuple-blocks','extra-body'):
  before=len(f.received);r=f.run_call('primary',request_variant=variant)
  print(json.dumps({'case':variant,'returncode':r.returncode,'stdout':r.stdout,'stderr':r.stderr,'wire':f.received[before:]}),flush=True)
  assert r.returncode==0 and len(f.received)==before+1
finally:f.doCleanups()
