# ABOUTME: Verifies retained runtime invalidation for every implemented proposal outcome.
# ABOUTME: Uses real native target changes and runtime admission with synthetic contexts.
from pathlib import Path
from dataclasses import replace
import sys,json
sys.path.insert(0,str(Path.cwd()));sys.path.insert(0,str(Path.cwd()/'tests'))
from test_memory_runtime import MemoryRuntimeTests
from test_memory_native import OWNER,SOURCE
from lifeos_hook_bridge.memory_runtime import MemoryAdmissionError
for decision in ('accept','edit','auto_apply','reject','applied_elsewhere'):
 f=MemoryRuntimeTests();f.setUp()
 try:
  scope=replace(OWNER,proposals=('create','review','approve','auto_apply'))
  (f.fixture.root/'LIFEOS/PULSE').symlink_to(SOURCE/'LIFEOS/PULSE')
  target=f.fixture.root/'LIFEOS/USER/CONFIG/OPERATIONAL_RULES.md';target.parent.mkdir(parents=True);target.write_text('# Synthetic rules\n')
  item={'type':'proposal','target_kind':'operational-rule','target_file':str(target),'edit':'Always confirm synthetic publication permission.','confidence':0.9,'rationale':'Synthetic rule.'}
  saved=f.fixture.memory.native_add(scope,item,request_id='create',project='');ref=saved['receipt']['proposal_reference']
  f.admit()
  kwargs={'content':'Always record the synthetic alternate rule.'} if decision=='edit' else {'note':'Applied in synthetic hook.'} if decision=='applied_elsewhere' else {'confidence_threshold':0.7} if decision=='auto_apply' else {}
  result=f.fixture.memory.decide_proposal(scope,ref,decision,'decide',**kwargs);assert result['status']=='committed',result
  invalidated=False
  try:f.runtime.check_call(request={},**f.route,session_id='session')
  except MemoryAdmissionError:invalidated=True
  assert invalidated==(decision in ('accept','edit','auto_apply'))
  f.runtime.admit(f.metadata(session='fresh'),**f.route,is_first_turn=True)
  print(json.dumps({'decision':decision,'proposal_status':result['proposal_status'],'retained_context_denied':invalidated,'fresh_context_admitted':True}),flush=True)
 finally:f.runtime.clear();f.doCleanups()
