# ABOUTME: Checks actual Responses transport for a trusted auxiliary task with a retired input claim.
# ABOUTME: Keeps native policy, original input proof and SDK calls real in a synthetic fixture.
from pathlib import Path
import json,sys
sys.path[:0]=[str(Path.cwd()),str(Path.cwd()/'tests')]
import test_memory_model_calls as fixture
from test_memory_native import OWNER
from lifeos_hook_bridge.memory_context import route_identity
from lifeos_hook_bridge.memory_service import MemoryConfiguration
raw=Path.cwd()/'docs/agents/2026-09-30-memory-history-repair/second-closure/raw'
source=Path('tests/memory_model_calls.py').read_text().replace('str(Path(__file__).parents[1])','str(Path.cwd())')
needle="{'aux_task':'compression'} if settings['operation']=='responses-compression' else {}"
assert needle in source
source=source.replace(needle,"{'aux_task':'memory_review'} if settings['operation']=='responses-compression' else {}")
program=raw/'responses_memory_review.py';program.write_text(source);fixture.PROGRAM=program
case=fixture.MemoryModelCallTests();case.setUp()
try:
 marker='Synthetic admitted private model marker'
 saved=case.fixture.fixture.remember(marker,'aux-response-retired')
 case.fixture.fixture.memory.forget(OWNER,saved['reference'],'aux-response-forget')
 route=dict(case.route,api_mode='responses')
 case.fixture.configuration['destinations']['chat-a:200']['model_routes'].append(route_identity(**route))
 MemoryConfiguration(case.fixture.path).save(case.fixture.configuration)
 for operation in ['responses-primary','responses-compression']:
  case.received.clear()
  result=case.run_call(operation,route=route,bind_input=True)
  print(json.dumps({'operation':operation,'aux_task':'memory_review' if operation=='responses-compression' else None,
     'returncode':result.returncode,'stdout':result.stdout,'stderr':result.stderr,'requests':case.received}),flush=True)
finally:case.doCleanups()
