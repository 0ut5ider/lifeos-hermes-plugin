# ABOUTME: Exercises isolated native health publication, scalar projection, and volume edges.
# ABOUTME: Records real managed and unmanaged subprocess outputs without changing source.
from test_memory_cortex_health import MemoryCortexHealthTests
from test_memory_native import OWNER
from dataclasses import asdict
from datetime import datetime,timezone
import os,json,subprocess,time

def health(c,**extra):
 env=dict(os.environ,HOME=str(c.fixture.fixture.home),BUN_CONFIG_NO_AUTO_INSTALL='1',LIFEOS_MEMORY_CONTEXT=json.dumps(asdict(c.fixture.context)))
 for key in ('LIFEOS_MEMORY_INTERNAL','CORTEX_HEALTH_ROOT','CORTEX_INDEX_MANIFEST','CORTEX_HEALTH_NOW','CORTEX_HEALTH_NO_WRITE','CORTEX_HEALTH_REPORT_PATH'):env.pop(key,None)
 env.update(extra)
 start=time.monotonic()
 try:
  r=subprocess.run(['bun','--no-install',str(c.root/'LIFEOS/TOOLS/MemoryHealthCheck.ts')],cwd=c.root,env=env,capture_output=True,text=True,timeout=5)
  return {'returncode':r.returncode,'stdout':r.stdout,'stderr':r.stderr,'seconds':time.monotonic()-start}
 except subprocess.TimeoutExpired as e:return {'timeout':True,'seconds':time.monotonic()-start,'stdout':str(e.stdout),'stderr':str(e.stderr)}

def run(name,body):
 c=MemoryCortexHealthTests();c.setUp()
 try:body(c)
 finally:c.doCleanups()

def publication(c):
 c.reviewer('Synthetic current publication control')
 target=c.root/'LIFEOS/USER/CONFIG/synthetic-protected-output.json';target.write_text('Synthetic protected config sentinel\n')
 result=health(c,CORTEX_HEALTH_REPORT_PATH=str(target))
 print(json.dumps({'case':'report-path-override','target_changed':target.read_text()!='Synthetic protected config sentinel\n','target_content':target.read_text(),'result':result}),flush=True)

def timestamp(c):
 # A current successful skip is valid native evidence; remember then retire exactly its ISO text.
 stamp=datetime.now(timezone.utc).isoformat()
 saved=c.fixture.fixture.remember('RULE: '+stamp,'timestamp','principal')
 assert saved['status']=='committed',saved
 c.fixture.fixture.memory.forget(OWNER,saved['reference'],'forget-timestamp')
 row={'ts':stamp,'ok':True,'runId':'synthetic-current-run','exchanges':0,'inference_duration_ms':0,'parse_ok':True,'skipped':True}
 (c.obs/'reviewer-runs.jsonl').write_text(json.dumps(row)+'\n')
 managed=c.call()
 (c.root/'LIFEOS/USER/CONFIG/memory-access.json').unlink()
 unmanaged=c.call(context=False)
 print(json.dumps({'case':'retired-timestamp','retired':stamp,'managed':managed,'unmanaged':unmanaged}),flush=True)

def volume(c):
 c.reviewer('Synthetic current volume control')
 hot=c.root/'LIFEOS/USER/PRINCIPAL/PRINCIPAL_MEMORY.md'
 text=hot.read_text(); entries=['RULE: Synthetic overlength diagnostic '+str(i)+' x'*160 for i in range(500)]
 hot.write_text(text.replace('<!-- END ENTRIES -->','\n'.join(entries)+'\n<!-- END ENTRIES -->'))
 managed=health(c)
 (c.root/'LIFEOS/USER/CONFIG/memory-access.json').unlink()
 unmanaged=health(c)
 print(json.dumps({'case':'invalid-hot-volume','entries':len(entries),'hot_bytes':hot.stat().st_size,'managed':managed,'unmanaged':unmanaged}),flush=True)

for name,body in [('publication',publication),('timestamp',timestamp),('volume',volume)]:run(name,body)
