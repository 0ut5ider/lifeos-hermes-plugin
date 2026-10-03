# ABOUTME: Checks native health schema and delegated fact source provenance with real connector calls.
# ABOUTME: Keeps all test data inside disposable synthetic HOME profiles.
import json
from pathlib import Path
import test_memory_cortex_health as health
import test_memory_delegation as delegation
from test_memory_native import OWNER

out=Path(__file__).parent

def schema(retired=None,unmanaged=False):
 f=health.MemoryCortexHealthTests(); f.setUp()
 try:
  f.root.joinpath('settings.system.json').write_text(json.dumps({'hooks':['MemoryTurnStart.hook.ts']}))
  if retired:
   saved=f.fixture.fixture.remember('RULE: '+retired,'retire-schema','principal')
   forgotten=f.fixture.fixture.memory.forget(OWNER,saved['reference'],'forget-schema')
  if unmanaged: f.root.joinpath('LIFEOS/USER/CONFIG/memory-access.json').unlink()
  process,report=f.health()
  log=f.obs/'memory-health.jsonl'
  return {'retired':retired,'unmanaged':unmanaged,'exit':process.returncode,'stdout':process.stdout,'stderr':process.stderr,'report':report,'published':log.exists(),'publication':log.read_text() if log.exists() else None}
 finally:f.doCleanups()

def provenance():
 f=delegation.MemoryDelegationTests();f.setUp()
 try:
  native=f.call([{'name':'add','item':{'type':'memory','actor':'principal','content':'RULE: Synthetic delegated provenance'}}, {'name':'add','item':{'type':'knowledge','entity_type':'research','name':'Synthetic delegated provenance','content':'Synthetic delegated provenance'}}])
  recall=f.fixture.memory.recall(OWNER,'Synthetic delegated provenance')
  return {'context_session':f.context.session_id,'context_writer':f.context.transport+':'+f.context.author,'native':native,'recall':recall}
 finally:f.doCleanups()

results={'schema':[schema(),schema('system'),schema('live'),schema('system',True)],'delegated_provenance':provenance()}
(out/'schema-provenance-results.json').write_text(json.dumps(results,indent=2)+'\n')
print(json.dumps({'schema':[{'retired':r['retired'],'unmanaged':r['unmanaged'],'exit':r['exit'],'published':r['published'],'unavailable':'unavailable' in r['report'],'clobber_details':[x.get('detail') for x in r['report'].get('findings',[]) if x.get('id','').startswith('settings-hook-missing')]} for r in results['schema']],'provenance':results['delegated_provenance']},indent=2))
