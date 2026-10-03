# ABOUTME: Checks accepted Responses forms alongside the new denial tests.
# ABOUTME: Uses real request admission and SDK transport with synthetic allowed text.
from pathlib import Path
import json,sys
sys.path[:0]=[str(Path.cwd()),str(Path.cwd()/'tests')]
import test_memory_model_calls as fixture
from lifeos_hook_bridge.memory_context import route_identity
from lifeos_hook_bridge.memory_service import MemoryConfiguration
for operation,variant in [('responses-primary','responses-instructions-json'),('responses-compression','')]:
 case=fixture.MemoryModelCallTests();case.setUp()
 try:
  route=dict(case.route,api_mode='responses')
  case.fixture.configuration['destinations']['chat-a:200']['model_routes'].append(route_identity(**route))
  MemoryConfiguration(case.fixture.path).save(case.fixture.configuration)
  result=case.run_call(operation,route=route,bind_input=True,request_variant=variant,aux_task='memory_review')
  outcome={'operation':operation,'variant':variant,'returncode':result.returncode,'stdout':result.stdout,'stderr':result.stderr,'requests':case.received}
  print(json.dumps(outcome),flush=True)
  assert result.returncode==0 and result.stderr=='',outcome
  assert json.loads(result.stdout)['result']=='SYNTHETIC-MODEL-OK',outcome
  assert len(case.received)==1,outcome
 finally:case.doCleanups()
