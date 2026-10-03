from pathlib import Path
import sys,json
r=Path.cwd();sys.path[:0]=[str(r),str(r/'tests')]
import test_memory_model_calls as fixture
from test_memory_native import OWNER
from lifeos_hook_bridge.memory_context import route_identity
from lifeos_hook_bridge.memory_service import MemoryConfiguration
out=r/'docs/agents/2026-09-30-memory-rendered-prompts/closure/raw'
s=(r/'docs/agents/2026-09-30-memory-rendered-prompts/raw/sdk-list-control.py').read_text()
s=s.replace("{'model':route['model'],'messages':messages}","{'model':route['model'],'input':soul}").replace('client.chat.completions.create(**request)','client.responses.create(**request)').replace("**route, session_id='session')","**route, session_id='session', aux_task='compression')").replace("result = response.choices[0].message.content","result = 'SDK_RESPONSE_RECEIVED'")
program=out/'responses-child.py';program.write_text(s);fixture.PROGRAM=program
f=fixture.MemoryModelCallTests();f.setUp()
try:
 f.route['api_mode']='responses';f.fixture.configuration['destinations']['chat-a:200']['model_routes']=[route_identity(**f.route)];MemoryConfiguration(f.fixture.path).save(f.fixture.configuration)
 marker='Synthetic removed cached model marker';saved=f.fixture.fixture.remember('RULE: '+marker,'cached-model','principal');f.fixture.fixture.memory.forget(OWNER,saved['reference'],'cached-model-forget')
 (f.fixture.home/'SOUL.md').write_text('# Synthetic LifeOS\n\n'+marker+'\n')
 result=f.run_call('primary',refresh_after_load=True)
 print(json.dumps({'returncode':result.returncode,'requests':len(f.received),'retired_claim_on_wire':marker in json.dumps(f.received),'stdout':result.stdout,'stderr':result.stderr,'wire':f.received}),flush=True)
finally:f.doCleanups()
