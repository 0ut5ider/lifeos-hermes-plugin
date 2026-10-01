from pathlib import Path
import json,sys,unittest
root=Path.cwd();sys.path[:0]=[str(root),str(root/'tests')]
out=root/'docs/agents/2026-09-30-memory-history-repair/second-closure/raw'
class EvidenceResult(unittest.TextTestResult):
 def addSuccess(self,test):
  if hasattr(test,'outcome'):
   (out/(test._testMethodName+'.txt')).write_text(json.dumps({'outcome':test.outcome,'http_requests':test.fixture.fixture.received},indent=2)+'\n')
  super().addSuccess(test)
suite=unittest.defaultTestLoader.loadTestsFromNames(['test_memory_agent','test_memory_history','test_memory_runtime','test_memory_model_calls','test_hermes_memory_provider','test_memory_host'])
result=unittest.TextTestRunner(verbosity=2,resultclass=EvidenceResult).run(suite)
sys.exit(not result.wasSuccessful())
