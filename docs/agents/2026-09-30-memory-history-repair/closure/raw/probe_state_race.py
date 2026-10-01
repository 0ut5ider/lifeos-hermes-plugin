# ABOUTME: Pauses a real repair after its state snapshot to expose concurrent admission ordering.
# ABOUTME: Uses trace scheduling only; policy, persistence, native operations and dispatch stay real.
from pathlib import Path
import json,sys,threading
sys.path[:0]=[str(Path.cwd()),str(Path.cwd()/'tests')]
from test_memory_runtime import MemoryRuntimeTests
from test_memory_native import OWNER
from lifeos_hook_bridge.memory_runtime import MemoryRuntime
from lifeos_hook_bridge.memory_service import MemoryConfiguration
fixture=MemoryRuntimeTests();fixture.setUp()
ready=threading.Event(); release=threading.Event(); evidence={}; errors=[]
try:
 saved=fixture.fixture.remember('Synthetic concurrently retired history fact','race-save')
 fixture.admit()
 fixture.fixture.memory.forget(OWNER,saved['reference'],'race-forget')
 def worker():
  def trace(frame,event,arg):
   if event=='line' and frame.f_code.co_name=='_check_call' and 'states' in frame.f_locals and not ready.is_set():
    evidence['repair_snapshot_sessions']=sorted(frame.f_locals['states'])
    ready.set()
    if not release.wait(10):raise RuntimeError('Trace release timeout')
   return trace
  sys.settrace(trace)
  try:
   runtime=MemoryRuntime(fixture.path)
   runtime.project_call(request={'messages':[{'role':'user','content':'Synthetic fresh request'}]},
    next_call=lambda request:evidence.update(dispatched=request),metadata=fixture.metadata(),**fixture.route,session_id='session')
  except Exception as exc:errors.append(repr(exc))
  finally:sys.settrace(None)
 thread=threading.Thread(target=worker);thread.start()
 assert ready.wait(10),'Repair did not reach state snapshot'
 fixture.admit(session='concurrent-session')
 evidence['sessions_after_concurrent_admit']=sorted(json.loads(fixture.runtime.state_path.read_text()))
 release.set();thread.join(10);assert not thread.is_alive()
 evidence['repair_errors']=errors
 evidence['sessions_after_repair']=sorted(json.loads(fixture.runtime.state_path.read_text()))
 # Test the concrete consequence after disabling ownership, as a caller without process-local binding.
 fixture.runtime.clear()
 MemoryConfiguration(fixture.path).update(lambda configuration:configuration.update(ownership_enabled=False))
 runtime=MemoryRuntime(fixture.path)
 try:
  runtime.check_call(request={'messages':[{'role':'assistant','content':'Synthetic concurrently retained private text'}]},
   **fixture.route,session_id='concurrent-session',metadata=fixture.metadata(session='concurrent-session'))
  evidence['inactive_retained_session_check']='allowed'
 except Exception as exc:evidence['inactive_retained_session_check']=repr(exc)
 print(json.dumps(evidence,indent=2))
 assert not errors
 assert 'concurrent-session' not in evidence['sessions_after_repair'],'Race did not reproduce'
finally:
 release.set();fixture.doCleanups()
