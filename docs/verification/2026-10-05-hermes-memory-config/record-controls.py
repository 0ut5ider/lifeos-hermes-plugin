# ABOUTME: Records actual Hermes configuration and lasting-store dispatch controls.
# ABOUTME: Saves native process output and synthetic artifact bytes without replacing results.
import json, os, sys, subprocess, unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[3]/'tests'))
from test_hermes_memory_config import HermesMemoryConfigTests
from test_hermes_learning_memory_flags import HermesLearningMemoryFlagsTests
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
 for cls in (HermesMemoryConfigTests, HermesLearningMemoryFlagsTests):
  for name in unittest.defaultTestLoader.getTestCaseNames(cls):
   test=cls(name)
   test.setUp()
   events=[]
   try:
    getattr(test,name)()
    artifacts={}
    record={'case':name,'events':events,'artifacts':artifacts,'native_source':os.environ['LIFEOS_MEMORY_SOURCE']}
    (p/(cls.__name__+'-'+name+'.json')).write_text(json.dumps(record,indent=2)+'\n')
    count+=1
   finally:
    test.doCleanups()
finally:
 subprocess.run=original_run
print(f'Recorded {count} passing Hermes configuration controls')
