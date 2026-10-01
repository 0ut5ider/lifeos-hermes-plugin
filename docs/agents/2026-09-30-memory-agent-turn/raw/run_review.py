from pathlib import Path
import json, sys, unittest
root=Path.cwd()
sys.path[:0]=[str(root),str(root/'tests')]
out=root/'docs/agents/2026-09-30-memory-agent-turn/raw'
class EvidenceResult(unittest.TextTestResult):
 def addSuccess(self,test):
  if hasattr(test,'outcome'):
   (out/(test._testMethodName+'.txt')).write_text(json.dumps({'outcome':test.outcome,'http_requests':test.fixture.fixture.received},indent=2)+'\n')
  super().addSuccess(test)
suite=unittest.defaultTestLoader.loadTestsFromNames(['test_memory_agent','test_memory_host','test_memory_model_calls'])
result=unittest.TextTestRunner(verbosity=2,resultclass=EvidenceResult).run(suite)
sys.exit(not result.wasSuccessful())
