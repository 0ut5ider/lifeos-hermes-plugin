# ABOUTME: Exercises verified input handoff with real worker admissions and synthetic state changes.
# ABOUTME: Records dispatch and binding outcomes for invalidation, lost state and concurrent next inputs.
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import json,sys
sys.path[:0]=[str(Path.cwd()),str(Path.cwd()/'tests')]
from test_memory_history import MemoryHistoryTests
from test_memory_native import OWNER
from lifeos_hook_bridge.memory_runtime import _BOUND,MemoryAdmissionError
from lifeos_hook_bridge.memory_service import MemoryConfiguration
from lifeos_hook_bridge.memory_transaction import publish
from lifeos_hook_bridge.memory_history import REMOVED
NEXT='Synthetic admitted next user input'
THIRD='Synthetic concurrently admitted third user input'
for scenario in ('valid','old_input','unapproved_model','changed_author','changed_policy','changed_prompt','lost_state','inactive','third_input','combined_forget'):
 case=MemoryHistoryTests();case.setUp()
 try:
  case.worker_turn();fixture=case.fixture;runtime=fixture.runtime;before=_BOUND.get();request={'messages':[{'role':'user','content':NEXT}]};kwargs={};sent=[]
  if scenario=='old_input':request['messages'][0]['content']='Synthetic previous user input'
  if scenario=='unapproved_model':request['extra_body']={'model':'unapproved-handoff-model'}
  if scenario=='changed_author':kwargs['metadata']=fixture.metadata(user='other')
  if scenario=='changed_policy':MemoryConfiguration(fixture.path).update(lambda config:config['accounts'].update({'chat-b:other':'owner'}))
  if scenario=='changed_prompt':(fixture.home/'SOUL.md').write_text('# Synthetic changed current identity\n')
  if scenario=='lost_state':publish(runtime.state_path,b'{}\n')
  if scenario=='inactive':MemoryConfiguration(fixture.path).update(lambda config:config.update(ownership_enabled=False))
  if scenario=='third_input':
   with ThreadPoolExecutor(max_workers=1) as executor:executor.submit(runtime.admit,fixture.metadata(),**fixture.route,is_first_turn=False,user_message=THIRD).result()
  if scenario=='combined_forget':
   fixture.fixture.memory.forget(OWNER,case.saved['reference'],'combined-handoff-forget')
   request['messages'].append({'role':'assistant','content':case.marker})
  error=None
  try:
   def dispatch(projected):
    runtime.check_call(request=projected,**fixture.route,session_id='session',**kwargs)
    sent.append(projected)
   runtime.project_call(request=request,next_call=dispatch,**fixture.route,session_id='session',**kwargs)
  except MemoryAdmissionError as exc:error=str(exc)
  expected=scenario in ('valid','combined_forget')
  evidence={'scenario':scenario,'error':error,'dispatches':len(sent),'binding_unchanged':_BOUND.get()==before,'sent':sent}
  assert bool(sent)==expected,evidence
  if not expected:assert _BOUND.get()==before,evidence
  if scenario=='combined_forget':assert sent[0]['messages'][1]['content']==REMOVED,evidence
  if scenario=='third_input':
   request['messages'][0]['content']=THIRD
   runtime.project_call(request=request,next_call=sent.append,**fixture.route,session_id='session')
   assert len(sent)==1
   evidence['latest_admitted_input_dispatches']=len(sent)
  print(json.dumps(evidence),flush=True)
 finally:case.doCleanups()
