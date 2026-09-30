# ABOUTME: Exercises managed and standalone proposal state transitions through actual Bun calls.
# ABOUTME: Records malformed connector refusals and synthetic target publication without mocking RPC.
from pathlib import Path
from dataclasses import asdict
import sys,os,json,subprocess
sys.path.insert(0,str(Path.cwd()));sys.path.insert(0,str(Path.cwd()/'tests'))
from test_memory_proposal_delegation import MemoryProposalDelegationTests
from lifeos_hook_bridge.memory_service import MemoryConfiguration
CODE="""
import {pathToFileURL} from 'node:url';
const q=JSON.parse(await Bun.stdin.text());
const p=await import(pathToFileURL(process.env.HOME+'/.claude/LIFEOS/PULSE/lib/memory-proposals.ts').href);
let r;
try {
if(q.action==='accept')r=p.acceptProposal(q.id);
if(q.action==='reject')r=p.rejectProposal(q.id);
if(q.action==='edit')r=p.editProposal(q.id,q.content);
if(q.action==='elsewhere')r=p.markProposalAppliedElsewhere(q.id,q.note);
if(q.action==='auto')r=p.autoApplyProposal(q.id,q.threshold);
if(q.action==='raw_set'){p.writeProposalQueue([]);r={unexpected:true};}
if(q.action==='list')r=p.loadProposalQueue();
console.log(JSON.stringify({result:r}));
}catch(error){console.log(JSON.stringify({error:String(error)}));}
"""
def call(f,action,**kwargs):
 env=dict(os.environ,HOME=str(f.fixture.fixture.home),LIFEOS_DIR=str(f.root/'LIFEOS'),LIFEOS_MEMORY_CONTEXT=json.dumps(asdict(f.context)),BUN_CONFIG_NO_AUTO_INSTALL='1');env.pop('LIFEOS_MEMORY_INTERNAL',None)
 process=subprocess.run(['bun','--no-install','--eval',CODE],input=json.dumps(dict(action=action,**kwargs)),text=True,capture_output=True,env=env,cwd=f.root,timeout=40)
 assert process.returncode==0,process.stderr
 return json.loads(process.stdout)
for managed in (True,False):
 for action in ('accept','reject','edit','elsewhere','auto'):
  f=MemoryProposalDelegationTests();f.setUp()
  try:
   if not managed:(f.root/'LIFEOS/USER/CONFIG/memory-access.json').unlink()
   saved=f.fixture.enqueue(item=f.fixture.item(confidence=0.9));ref=saved['receipt']['proposal_reference']
   result=call(f,action,id=ref['id'],content='Always record the synthetic alternate decision.',note='Applied in a synthetic hook.',threshold=0.7)
   queue=[json.loads(line) for line in Path(saved['path']).read_text().splitlines()]
   expected={'accept':'accepted','reject':'rejected','edit':'edited','elsewhere':'applied-elsewhere','auto':'auto-applied'}[action]
   assert result['result']['ok'] and queue[0]['status']==expected,result
   print(json.dumps({'managed':managed,'action':action,'result':result,'queue_status':queue[0]['status'],'target':f.fixture.target.read_text(),'listed':call(f,'list')}),flush=True)
  finally:f.doCleanups()
for mode in ('dangling','directory','public_permissions','invalid_json','unsupported_version','unavailable_command','raw_set'):
 f=MemoryProposalDelegationTests();f.setUp()
 try:
  saved=f.fixture.enqueue();before=f.fixture.target.read_text();p=f.root/'LIFEOS/USER/CONFIG/memory-access.json'
  if mode=='dangling':p.unlink();p.symlink_to(f.fixture.fixture.home/'missing.json')
  if mode=='directory':p.unlink();p.mkdir()
  if mode=='public_permissions':p.chmod(0o644)
  if mode=='invalid_json':p.write_text('{invalid')
  if mode=='unsupported_version':p.write_text(json.dumps({'version':99,'command':[sys.executable]}))
  if mode=='unavailable_command':p.write_text(json.dumps({'version':1,'command':[str(f.fixture.fixture.home/'missing-executable')]}))
  result=call(f,'raw_set' if mode=='raw_set' else 'accept',id=saved['receipt']['proposal_reference']['id'])
  assert 'error' in result or result['result'].get('ok') is False,result
  assert f.fixture.target.read_text()==before
  assert len(f.fixture.memory.review_proposals(f.fixture.scope))==1
  print(json.dumps({'invalid_connector_case':mode,'result':result,'target_unchanged':True,'pending_unchanged':True}),flush=True)
 finally:f.doCleanups()
