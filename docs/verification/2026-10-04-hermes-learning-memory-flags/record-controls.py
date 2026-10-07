# ABOUTME: Records real Hermes graph operations, flags, and preserved synthetic files.
# ABOUTME: Saves native process output for ordinary and queued mutation controls.
import json, os, sys, unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[3]/'tests'))
from test_hermes_learning_memory_flags import HermesLearningMemoryFlagsTests
p=Path(__file__).resolve().parent/'native-outcomes'
p.mkdir(exist_ok=True)
count=0
for name in unittest.defaultTestLoader.getTestCaseNames(HermesLearningMemoryFlagsTests):
 test=HermesLearningMemoryFlagsTests(name)
 test.setUp()
 try:
  before={path.name:path.read_text() for path in (test.home/'memories').iterdir()}
  getattr(test,name)()
  after={path.name:path.read_text() for path in (test.home/'memories').iterdir()}
  (p/(name+'.json')).write_text(json.dumps({'case':name,'before':before,'after':after,'events':test.events,
   'native_source':os.environ['LIFEOS_HERMES_SOURCE']},indent=2)+'\n')
  count+=1
 finally:
  test.doCleanups()
print(f'Recorded {count} passing Hermes learning-memory controls')
