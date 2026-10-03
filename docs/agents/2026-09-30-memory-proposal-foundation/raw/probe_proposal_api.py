# ABOUTME: Checks malformed proposal requests and reference validation through the actual service.
# ABOUTME: Uses temporary native proposal targets and explicit owner and creator grants.
from pathlib import Path
from dataclasses import replace
import sys,json
sys.path.insert(0,str(Path.cwd()));sys.path.insert(0,str(Path.cwd()/'tests'))
from test_memory_proposals import MemoryProposalTests
from lifeos_hook_bridge.memory_service import MemoryConfiguration,MemoryService
from lifeos_hook_bridge.memory_policy import SessionContext
f=MemoryProposalTests();f.setUp()
try:
 path=f.fixture.home/'hermes/probe-memory.json';cfg=MemoryConfiguration(path)
 grant={'visibility':'private','participants':['owner'],'read':['principal','assistant','project'],'write':[],'projects':['*'],'model_routes':['local'],'proposals':['create','review','approve']}
 value={'version':1,'root':str(f.fixture.root),'principal':'owner','accounts':{'chat:owner':'owner'},'destinations':{'chat:private':grant},'sharing_enabled':True,'clients':{'creator':{'enabled':True,'read':['principal','assistant','project'],'write':[],'projects':['*'],'model_route':'unknown','proposals':['create','review']}}}
 cfg.save(value);service=MemoryService(cfg);ctx=SessionContext('chat','owner','private','private',('owner',),'local','synthetic')
 def call(name,arguments):return service.call_context(ctx,name,arguments)
 changes=[{'target_kind':'invalid'},{'confidence':True},{'edit':[]},{'rationale':'<private>synthetic private rationale</private>'},{'observed_across_sessions':0},{'target_kind':'identity','target_file':str(f.fixture.home/'outside.md')},{'unexpected':'field'}]
 for i,change in enumerate(changes):
  result=call('lifeos_memory_propose',{'proposal':f.item(**change),'request_id':'invalid-'+str(i)})
  assert result['status']=='rejected',result
  print(json.dumps({'case':'invalid-'+str(i),'change':change,'result':result}),flush=True)
 saved=call('lifeos_memory_propose',{'proposal':f.item(),'request_id':'valid'});ref=saved['proposal_reference']
 for i,reference in enumerate([dict(ref,revision=True),dict(ref,extra='field'),dict(ref,revision=0),{'id':[], 'revision':1}]):
  result=call('lifeos_memory_decide_proposal',{'reference':reference,'decision':'accept','request_id':'bad-ref-'+str(i)})
  assert result['status']=='rejected';print(json.dumps({'case':'bad-reference-'+str(i),'result':result}),flush=True)
 result=service.call_client('creator','lifeos_memory_decide_proposal',{'reference':ref,'decision':'accept','request_id':'client-denied'})
 assert result['status']=='rejected';print(json.dumps({'case':'external-cannot-approve','result':result}),flush=True)
 queue=Path(saved['destination']);rows=[json.loads(line) for line in queue.read_text().splitlines()];rows[0]['edit']='Synthetic changed proposal text';queue.write_text(''.join(json.dumps(row)+'\n' for row in rows))
 result=call('lifeos_memory_decide_proposal',{'reference':ref,'decision':'accept','request_id':'changed-row'})
 assert result['status']=='conflict';assert f.item()['edit'] not in f.target.read_text();print(json.dumps({'case':'changed-native-row','result':result}),flush=True)
finally:f.doCleanups()
