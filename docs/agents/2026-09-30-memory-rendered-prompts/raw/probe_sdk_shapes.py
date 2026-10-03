from pathlib import Path
import json,sys
repo=Path.cwd();sys.path[:0]=[str(repo),str(repo/'tests')]
import test_memory_model_calls as model_fixture
from test_memory_native import OWNER
out=repo/'docs/agents/2026-09-30-memory-rendered-prompts/raw'
original=(repo/'tests/memory_model_calls.py').read_text().replace("str(Path(__file__).parents[1])",repr(str(repo)))
f=model_fixture.MemoryModelCallTests();f.setUp()
try:
 marker='Synthetic removed cached model marker'
 saved=f.fixture.fixture.remember('RULE: '+marker,'cached-model','principal')
 f.fixture.fixture.memory.forget(OWNER,saved['reference'],'cached-model-forget')
 for variant,mutation in [('list-control',''),('tuple-messages','messages = tuple(messages)'),('tuple-blocks',"messages[0]['content'] = ({'type':'text','text':soul},)"),('generator-messages','messages = (m for m in messages)'),('extra-body',"messages = [{'role':'user','content':settings['marker']}]")]:
  script=original.replace("        if settings['operation'] == 'primary':",'        '+mutation+"\n        if settings['operation'] == 'primary':")
  if variant=='extra-body':script=script.replace("{'model':route['model'],'messages':messages},","{'model':route['model'],'messages':messages,'extra_body':{'messages':[{'role':'system','content':soul}]}},")
  program=out/('sdk-'+variant+'.py');program.write_text(script);model_fixture.PROGRAM=program
  (f.fixture.home/'SOUL.md').write_text('# Synthetic LifeOS\n\n'+marker+'\n')
  before=len(f.received);result=f.run_call('primary',refresh_after_load=True)
  wire=f.received[before:]
  print(json.dumps({'case':variant,'returncode':result.returncode,'network_requests':len(wire),'retired_claim_on_wire':marker in json.dumps(wire),'stdout':result.stdout,'stderr':result.stderr,'wire':wire}),flush=True)
finally:f.doCleanups()
