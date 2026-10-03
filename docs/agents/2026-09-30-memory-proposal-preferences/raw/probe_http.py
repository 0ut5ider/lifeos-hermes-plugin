from pathlib import Path
import sys,os,json,importlib.util
from unittest.mock import patch
from fastapi import FastAPI
from fastapi.testclient import TestClient
repo=Path.cwd();sys.path[:0]=[str(repo),str(repo/'tests'),'/home/outsider/.cache/lifeos-plugin-memory/source-gate-20260930-proposal-delegation-fixed/hermes']
from test_memory_proposals import MemoryProposalTests
from lifeos_hook_bridge.memory_service import MemoryConfiguration
for decision in ('accept','reject','edit','applied_elsewhere','negative'):
 f=MemoryProposalTests();f.setUp()
 try:
  home=f.fixture.home;cfg=home/'hermes/lifeos-memory.json'
  MemoryConfiguration(cfg).save({'version':1,'root':str(f.fixture.root),'principal':'owner','accounts':{},'destinations':{}})
  saved=f.enqueue();ref=saved['receipt']['proposal_reference'];before=f.target.read_bytes();config_before=cfg.read_bytes();queue=Path(saved['path']);queue_before=queue.read_bytes()
  with patch.dict(os.environ,{'HOME':str(home),'HERMES_HOME':str(cfg.parent)}):
   spec=importlib.util.spec_from_file_location('probe_api',repo/'lifeos_hook_bridge/dashboard/plugin_api.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
   app=FastAPI();app.include_router(mod.router,prefix='/api/plugins/lifeos-hook-bridge')
   with TestClient(app) as client:
    endpoint='/api/plugins/lifeos-hook-bridge/memory/review'
    def call(args):return client.post(endpoint,json={'tool':'lifeos_memory_decide_proposal','arguments':args})
    args={'reference':ref,'decision':decision,'request_id':'probe-'+decision}
    if decision=='negative':
     cases=[dict(args,decision='auto_apply',confidence_threshold=0),dict(args,decision='accept',reference=dict(ref,revision=True)),dict(args,decision='accept',reference=dict(ref,revision=99)),dict(args,decision='edit',content=''),dict(args,decision='applied_elsewhere',note='<private>synthetic</private>'),dict(args,decision='accept',dry_run=True)]
     for i,arg in enumerate(cases):
      arg['request_id']='negative-'+str(i);response=call(arg);result=response.json();assert result['status'] in ('rejected','conflict'),result
      assert f.target.read_bytes()==before and queue.read_bytes()==queue_before
      print(json.dumps({'case':'negative-'+str(i),'http':response.status_code,'result':result}))
     for malformed in ({},{'tool':'lifeos_memory_proposals','arguments':[]},{'tool':'lifeos_memory_proposals','arguments':{},'scope':{'proposals':['auto_apply']}}):
      response=client.post(endpoint,json=malformed);assert response.status_code==400,response.text
      print(json.dumps({'case':'malformed-envelope','http':response.status_code,'result':response.json()}))
    else:
     if decision=='edit':args['content']='Always inspect synthetic HTTP fixture outcomes.'
     if decision=='applied_elsewhere':args['note']='Synthetic change recorded in another fixture.'
     response=call(args);result=response.json();assert result['status']=='committed',result
     assert 'row' not in result
     expected={'accept':'accepted','reject':'rejected','edit':'edited','applied_elsewhere':'applied-elsewhere'}[decision]
     assert result['proposal_status']==expected
     assert client.post(endpoint,json={'tool':'lifeos_memory_proposals','arguments':{}}).json()['results']==[]
     resolved=f.memory.review_proposals(f.scope,include_resolved=True);assert resolved[0]['status']==expected
     if decision in ('reject','applied_elsewhere'):assert f.target.read_bytes()==before
     else:assert (args.get('content') or f.item()['edit']) in f.target.read_text()
     assert call(args).json()==result
     stale=call(dict(args,request_id='stale-'+decision)).json();assert stale['status']=='conflict',stale
     print(json.dumps({'case':decision,'http':response.status_code,'result':result,'stored_status':resolved[0]['status'],'retry_equal':True,'stale':stale}))
    assert cfg.read_bytes()==config_before
 finally:f.doCleanups()
