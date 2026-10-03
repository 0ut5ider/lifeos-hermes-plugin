# ABOUTME: Records controls for native health shape and source access authorization.
# ABOUTME: Uses synthetic native sources and real Python file-open audit events.
import json,traceback,sys,subprocess,os
from pathlib import Path
from dataclasses import asdict
from datetime import datetime,timezone
import test_memory_cortex_health as health
import test_memory_native as native
out=Path(__file__).parent; results=[]
def health_control(retire,managed):
 f=health.MemoryCortexHealthTests();f.setUp()
 try:
  n=f.fixture.fixture
  if retire:
   s=n.remember('RULE: begins','shape-word','principal');n.memory.forget(native.OWNER,s['reference'],'shape-forget')
  p=f.root/'LIFEOS/USER/PRINCIPAL/PRINCIPAL_MEMORY.md';p.write_text(p.read_text().replace('<!-- END ENTRIES -->','<!-- END ENTRIES -->\n<!-- END ENTRIES -->'))
  if not managed:(f.root/'LIFEOS/USER/CONFIG/memory-access.json').unlink()
  env=dict(os.environ,HOME=str(n.home),BUN_CONFIG_NO_AUTO_INSTALL='1',LIFEOS_MEMORY_CONTEXT=json.dumps(asdict(f.fixture.context)));env.pop('LIFEOS_MEMORY_INTERNAL',None)
  r=subprocess.run(['bun','--no-install',str(f.root/'LIFEOS/TOOLS/MemoryHealthCheck.ts')],cwd=f.root,env=env,capture_output=True,text=True,timeout=45)
  return {'retire':retire,'managed':managed,'code':r.returncode,'stdout':r.stdout,'stderr':r.stderr,'published':(f.obs/'memory-health.jsonl').exists()}
 finally:f.doCleanups()
for args in [(False,True),(True,True),(True,False)]:
 results.append({'probe':'health_controls','result':health_control(*args)})
 (out/'control-results.json').write_text(json.dumps(results,indent=2))
def access_before_grant():
 f=native.NativeMemoryTests();f.setUp();events=[];enabled=False
 path=str(f.root/'LIFEOS/USER/PRINCIPAL/PRINCIPAL_MEMORY.md')
 def audit(event,args):
  if enabled and event=='open' and isinstance(args[0],str) and args[0]==path:events.append({'event':event,'args':list(args)})
 sys.addaudithook(audit)
 try:
  s=f.remember('RULE: Synthetic private authorization marker','private-source','principal')
  enabled=True
  receipt=f.memory.forget(native.READER,s['reference'],'denied-source-probe')
  enabled=False
  return {'receipt':receipt,'source_open_events':events}
 finally:enabled=False;f.doCleanups()
results.append({'probe':'source_authority_before_journal','result':access_before_grant()})
(out/'control-results.json').write_text(json.dumps(results,indent=2))
print(json.dumps(results,indent=2))
