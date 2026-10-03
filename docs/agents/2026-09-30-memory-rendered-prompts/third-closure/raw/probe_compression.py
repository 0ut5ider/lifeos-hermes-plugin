from pathlib import Path
import sys,json
sys.path[:0]=[str(Path.cwd()),str(Path.cwd()/'tests')]
from test_memory_model_calls import MemoryModelCallTests
from test_memory_native import OWNER
f=MemoryModelCallTests();f.setUp()
try:
 marker='Synthetic removed cached model marker'
 saved=f.fixture.fixture.remember('RULE: '+marker,'cached-model','principal')
 (f.fixture.home/'SOUL.md').write_text('# Synthetic LifeOS\n\n'+marker+'\n')
 f.fixture.fixture.memory.forget(OWNER,saved['reference'],'cached-model-forget')
 result=f.run_call('compression',refresh_after_load=True)
 print(json.dumps({'returncode':result.returncode,'network_requests':len(f.received),'retired_claim_on_wire':marker in json.dumps(f.received),'stdout':result.stdout,'stderr':result.stderr,'wire':f.received}))
finally:f.doCleanups()
