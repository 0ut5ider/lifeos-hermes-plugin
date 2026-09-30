# ABOUTME: Checks retained-claim refusal after a proposal was already queued.
# ABOUTME: Uses actual native forgetting and each proposal application decision in temporary fixtures.
from pathlib import Path
import sys,json
sys.path.insert(0,str(Path.cwd()));sys.path.insert(0,str(Path.cwd()/'tests'))
from test_memory_proposals import MemoryProposalTests
from test_memory_native import OWNER
for action in ('accept','edit','auto_apply'):
 f=MemoryProposalTests();f.setUp()
 try:
  claim='RULE: forgotten synthetic publication instruction'
  fact=f.fixture.remember(claim,'source-fact','principal')
  saved=f.enqueue(item=f.item(claim if action!='edit' else 'Always preserve the synthetic current rule.',confidence=0.9))
  f.memory.forget(OWNER,fact['reference'],'forget-source')
  kwargs={'content':claim} if action=='edit' else {'confidence_threshold':0.7} if action=='auto_apply' else {}
  result=f.memory.decide_proposal(f.scope,saved['receipt']['proposal_reference'],action,'apply-after-forget',**kwargs)
  assert result['status']=='rejected' and claim not in f.target.read_text(),result
  print(json.dumps({'action':action,'result':result,'target_contains_forgotten_claim':False}),flush=True)
 finally:f.doCleanups()
