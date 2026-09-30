# ABOUTME: Kills the Python caller after a real native acceptance publishes target and queue.
# ABOUTME: Verifies exact rollback and a single accepted retry using disposable proposal fixtures.
from pathlib import Path
import sys,json,os,hashlib
sys.path.insert(0,str(Path.cwd()));sys.path.insert(0,str(Path.cwd()/'tests'))
from test_memory_proposals import MemoryProposalTests
f=MemoryProposalTests();f.setUp()
try:
 saved=f.enqueue();reference=saved['receipt']['proposal_reference'];queue=Path(saved['path'])
 target_before=f.target.read_bytes();queue_before=queue.read_bytes()
 child=os.fork()
 if child==0:
  original=f.memory._native
  def interrupted(action,**values):
   result=original(action,**values)
   if action=='proposal_decision':os._exit(73)
   return result
  f.memory._native=interrupted
  f.memory.decide_proposal(f.scope,reference,'accept','crashed-accept')
  os._exit(74)
 _,status=os.waitpid(child,0)
 before={'child_exit':os.waitstatus_to_exitcode(status),'target_changed':f.target.read_bytes()!=target_before,'queue_changed':queue.read_bytes()!=queue_before,'journal_present':f.memory.transaction.journal.exists()}
 assert before['child_exit']==73 and before['target_changed'] and before['queue_changed']
 reviewed=f.memory.review_proposals(f.scope)
 after={'target_restored':f.target.read_bytes()==target_before,'queue_restored':queue.read_bytes()==queue_before,'pending':len(reviewed),'journal_present':f.memory.transaction.journal.exists()}
 assert after['target_restored'] and after['queue_restored'] and after['pending']==1 and not after['journal_present']
 retried=f.memory.decide_proposal(f.scope,reference,'accept','crashed-accept')
 assert retried['status']=='committed'
 count=f.target.read_text().count(f.item()['edit']);assert count==1
 print(json.dumps({'before_recovery':before,'after_recovery':after,'retry':retried,'edit_occurrences':count}),flush=True)
finally:f.doCleanups()
