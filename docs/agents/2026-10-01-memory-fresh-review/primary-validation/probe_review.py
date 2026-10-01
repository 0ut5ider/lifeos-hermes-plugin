# ABOUTME: Reproduces memory interface defects against owned native synthetic profiles.
# ABOUTME: Records full request results and preserves source fixture integrity.
import json,traceback,os,subprocess
from pathlib import Path
from dataclasses import asdict
import test_memory_pulse_auth as auth
import test_memory_cortex_health as health
import test_memory_native as native
from lifeos_hook_bridge.memory_service import MemoryService
out=Path(__file__).parent
results=[]
def run(name,fn):
 try: results.append({'probe':name,'result':fn()})
 except Exception: results.append({'probe':name,'exception':traceback.format_exc()})
 (out/'probe-results.json').write_text(json.dumps(results,indent=2))
 print(json.dumps(results[-1]),flush=True)
def dashboard():
 f=auth.MemoryPulseAuthTests(); f.setUp()
 try:
  f.login(); f.configuration.update(lambda c:c['accounts'].pop('dashboard:basic:synthetic-owner'))
  base='/api/plugins/lifeos-hook-bridge/memory'
  rows=[]
  for method,path,body in [('GET','/pulse/snapshot',None),('POST','/review',{'tool':'lifeos_memory_search','arguments':{'query':'authenticated PULSE'}}),('POST','/adoption/preview',{}),('POST','/sharing',{'enabled':True}),('GET','',None)]:
   r=f.client.request(method,base+path,json=body)
   rows.append({'method':method,'path':path,'status':r.status_code,'headers':dict(r.headers),'body':r.json()})
  f.app.state.auth_required=False; f.client.cookies.clear()
  r=f.client.post(base+'/review',json={'tool':'lifeos_memory_search','arguments':{'query':'authenticated PULSE'}})
  rows.append({'anonymous_loopback':True,'status':r.status_code,'body':r.json()})
  return rows
 finally:f.doCleanups()
run('dashboard_revoked_and_unknown_authority',dashboard)
def hot_drift():
 f=native.NativeMemoryTests(); f.setUp()
 try:
  path=f.root/'LIFEOS/USER/PRINCIPAL/PRINCIPAL_MEMORY.md'
  f.memory._native('add',item={'type':'memory','actor':'principal','content':'RULE: Synthetic unmanaged control'})
  before=path.read_text(); saved=f.remember('RULE: Synthetic governed addition','drift-remember','principal'); after=path.read_text()
  try: read=f.memory.read_hot(native.OWNER,'principal')
  except Exception:read=traceback.format_exc()
  return {'before':before,'receipt':saved,'after':after,'read_hot':read,'recall':f.memory.recall(native.OWNER,'governed')}
 finally:f.doCleanups()
run('remember_with_unadopted_hot_content',hot_drift)
def health_keys():
 f=health.MemoryCortexHealthTests();f.setUp()
 try:
  n=f.fixture.fixture
  saved=n.remember('RULE: begins','forget-health-key','principal'); n.memory.forget(native.OWNER,saved['reference'],'retire-health-key')
  p=f.root/'LIFEOS/USER/PRINCIPAL/PRINCIPAL_MEMORY.md';p.write_text(p.read_text().replace('<!-- END ENTRIES -->','<!-- END ENTRIES -->\n<!-- END ENTRIES -->'))
  env=dict(os.environ,HOME=str(n.home),BUN_CONFIG_NO_AUTO_INSTALL='1',LIFEOS_MEMORY_CONTEXT=json.dumps(asdict(f.fixture.context)))
  env.pop('LIFEOS_MEMORY_INTERNAL',None)
  r=subprocess.run(['bun','--no-install',str(f.root/'LIFEOS/TOOLS/MemoryHealthCheck.ts')],cwd=f.root,env=env,capture_output=True,text=True,timeout=45)
  return {'returncode':r.returncode,'stdout':r.stdout,'stderr':r.stderr,'log_exists':(f.obs/'memory-health.jsonl').exists()}
 finally:f.doCleanups()
run('native_health_after_retired_structural_begins',health_keys)
