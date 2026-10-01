import json,sys,threading,time
from concurrent.futures import ThreadPoolExecutor
from test_memory_pulse import MemoryPulseTests
from test_memory_native import OWNER
c=MemoryPulseTests();c.setUp()
try:
 f=c.fixture.fixture.fixture
 saved=f.remember('RULE: Synthetic pulse lock current','lock-save','principal')
 paused=threading.Event();release=threading.Event();started=threading.Event();finished=threading.Event()
 def tracing(frame,event,arg):
  if event=='call' and frame.f_code.co_name=='filter_report' and frame.f_code.co_filename.endswith('memory_diagnostics.py'):
   paused.set();assert release.wait(5)
  return tracing
 def read():
  sys.settrace(tracing)
  try:return c.snapshot()
  finally:sys.settrace(None)
 def forget():
  started.set()
  try:return f.memory.forget(OWNER,saved['reference'],'lock-forget')
  finally:finished.set()
 with ThreadPoolExecutor(max_workers=2) as pool:
  reading=pool.submit(read);assert paused.wait(5)
  writing=pool.submit(forget);assert started.wait(5)
  time.sleep(.1);blocked=not finished.is_set();release.set()
  first=reading.result(timeout=10);receipt=writing.result(timeout=10)
 second=c.snapshot()
 print(json.dumps({'writer_blocked_during_projection':blocked,'first_hot':first['principalMemory'],'forget':receipt,'second_hot':second['principalMemory']},indent=2))
 assert blocked and first['principalMemory']['count']==1 and receipt['status']=='committed' and second['principalMemory']['count']==0
finally:c.doCleanups()
