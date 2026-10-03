# ABOUTME: Runs original archived reproduction children without regenerating their request bodies.
# ABOUTME: Checks repaired compressor behavior and retired auxiliary Responses denial on real SDK calls.
from pathlib import Path
import json,sys,hashlib
sys.path[:0]=[str(Path.cwd()),str(Path.cwd()/'tests')]
import test_memory_model_calls as fixture
from lifeos_hook_bridge.memory_context import route_identity
from lifeos_hook_bridge.memory_service import MemoryConfiguration
from test_memory_native import OWNER
root=Path.cwd()/'docs/agents/2026-09-30-memory-history-repair'
for child,operations,retire in [('closure/raw/model_calls_with_proof.py',('primary','compression'),False),('second-closure/raw/responses_memory_review.py',('responses-primary','responses-compression'),True)]:
 fixture.PROGRAM=root/child
 for operation in operations:
  case=fixture.MemoryModelCallTests();case.setUp()
  try:
   route=case.route
   if retire:
    saved=case.fixture.fixture.remember('Synthetic admitted private model marker','archived-aux-marker')
    case.fixture.fixture.memory.forget(OWNER,saved['reference'],'archived-aux-forget')
    route=dict(route,api_mode='responses')
    case.fixture.configuration['destinations']['chat-a:200']['model_routes'].append(route_identity(**route))
    MemoryConfiguration(case.fixture.path).save(case.fixture.configuration)
   result=case.run_call(operation,route=route,bind_input=True)
   outcome={'child':child,'sha256':hashlib.sha256(fixture.PROGRAM.read_bytes()).hexdigest(),'operation':operation,
     'returncode':result.returncode,'stdout':result.stdout,'stderr':result.stderr,'requests':case.received}
   print(json.dumps(outcome),flush=True)
   if retire and operation=='responses-compression':
    assert result.returncode!=0 and 'auxiliary prompt' in result.stderr,outcome
    assert case.received==[],outcome
   else:
    assert result.returncode==0 and result.stderr=='',outcome
    assert 'SYNTHETIC-MODEL-OK' in json.loads(result.stdout)['result'],outcome
    assert len(case.received)==1,outcome
  finally:case.doCleanups()
