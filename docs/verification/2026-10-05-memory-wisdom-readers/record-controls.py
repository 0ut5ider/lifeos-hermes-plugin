# ABOUTME: Records actual Wisdom frame reads and report publication controls.
# ABOUTME: Saves native process output and synthetic artifact bytes without replacing results.
import json, os, sys, subprocess, unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[3]/'tests'))
from test_memory_wisdom_readers import MemoryWisdomReaderTests
p=Path(__file__).resolve().parent/'native-outcomes'
p.mkdir(exist_ok=True)
original_run=subprocess.run
events=[]
def run(*args,**kwargs):
 result=original_run(*args,**kwargs)
 command=args[0] if args else kwargs.get('args',[])
 events.append({'command':command,'status':result.returncode,'stdout':result.stdout,'stderr':result.stderr})
 return result
subprocess.run=run
count=0
try:
 for cls in (MemoryWisdomReaderTests,):
  for name in unittest.defaultTestLoader.getTestCaseNames(cls):
   test=cls(name)
   test.setUp()
   events=[]
   try:
    getattr(test,name)()
    artifacts={str(path):{'content':path.read_text(),'mode':oct(path.stat().st_mode & 0o777)}
      for path in (test.principles,test.health,) if path.exists()}
    record={'case':name,'events':events,'artifacts':artifacts,'native_source':os.environ['LIFEOS_MEMORY_SOURCE']}
    (p/(cls.__name__+'-'+name+'.json')).write_text(json.dumps(record,indent=2)+'\n')
    count+=1
   finally:
    test.doCleanups()
finally:
 subprocess.run=original_run
print(f'Recorded {count} passing Wisdom reader controls')
