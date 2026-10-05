# ABOUTME: Records the real SeedPulse command and its resulting synthetic artifacts.
# ABOUTME: Saves observed child status, output, and artifact bytes without replacing results.
import json, os, sys, unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[3]/'tests'))
from test_memory_seed_pulse import MemorySeedPulseTests
p=Path(__file__).resolve().parent/'native-outcomes'
p.mkdir(exist_ok=True)
for name in unittest.defaultTestLoader.getTestCaseNames(MemorySeedPulseTests):
 test=MemorySeedPulseTests(name)
 test.setUp()
 try:
  result=unittest.TestResult()
  test.run=unittest.TestCase.run.__get__(test)
  getattr(test,name)()
  files={str(path.relative_to(test.root)):{'content':path.read_text(),'mode':oct(path.stat().st_mode & 0o777)}
   for path in (test.summary,test.state) if path.exists()}
  record={'case':name,'events':test.events,'artifacts':files,'native_source':os.environ['LIFEOS_MEMORY_SOURCE']}
  (p/(name+'.json')).write_text(json.dumps(record,indent=2)+'\n')
 finally:
  test.doCleanups()
print('Recorded seven passing SeedPulse controls')
