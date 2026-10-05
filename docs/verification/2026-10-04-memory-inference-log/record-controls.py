# ABOUTME: Captures actual inference-log processes and private synthetic publication effects.
# ABOUTME: Retains native output, observed HTTP requests, and recovery results without substitution.
import json, os, sys, subprocess, unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[3]/'tests'))
from test_memory_inference_log import MemoryInferenceLogTests
from test_memory_inference_log_publication import MemoryInferenceLogPublicationTests
p=Path(__file__).resolve().parent/'native-outcomes'
p.mkdir(exist_ok=True)
original_run=subprocess.run
events=[]
def run(*args,**kwargs):
 result=original_run(*args,**kwargs)
 command=args[0] if args else kwargs.get('args',[])
 if command and (Path(command[0]).name=='bun' or any(str(x).endswith('memory_inference_log_process.py') for x in command)):
  events.append({'command':command,'status':result.returncode,'stdout':result.stdout,'stderr':result.stderr})
 return result
subprocess.run=run
count=0
try:
 for cls in (MemoryInferenceLogTests,MemoryInferenceLogPublicationTests):
  for name in unittest.defaultTestLoader.getTestCaseNames(cls):
   test=cls(name)
   test.setUp()
   events=[]
   try:
    before=test.path.read_text() if test.path.exists() else None
    getattr(test,name)()
    files={str(path.relative_to(test.root)):{'content':path.read_text(),'mode':oct(path.stat().st_mode & 0o777)}
      for path in (test.path,test.root.parent/'foreign-verification.jsonl') if path.exists() and path.is_relative_to(test.root)}
    record={'case':name,'events':events,'before':before,'artifacts':files,
      'requests':getattr(test.fixture,'received',[]),'native_source':os.environ['LIFEOS_MEMORY_SOURCE']}
    (p/(cls.__name__+'-'+name+'.json')).write_text(json.dumps(record,indent=2)+'\n')
    count+=1
   finally:
    test.doCleanups()
finally:
 subprocess.run=original_run
print(f'Recorded {count} passing inference log controls')
