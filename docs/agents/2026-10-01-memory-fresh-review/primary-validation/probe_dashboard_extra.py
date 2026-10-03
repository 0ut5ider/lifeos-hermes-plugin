# ABOUTME: Tests installation owner bindings for a distinct real dashboard login.
# ABOUTME: Checks revoked write authority against native synthetic facts.
import json,secrets,os,subprocess
from pathlib import Path
from dataclasses import asdict
from datetime import datetime,timezone
import test_memory_pulse_auth as auth
from plugins.dashboard_auth.basic import BasicAuthProvider,hash_password
from hermes_cli.dashboard_auth.registry import register_global_provider,restore_registration
from lifeos_hook_bridge.memory_diagnostics import filter_report
from test_memory_native import OWNER
out=Path(__file__).parent;results=[]
def emit(value):
 results.append(value);(out/'dashboard-extra-results.json').write_text(json.dumps(results,indent=2));print(json.dumps(value),flush=True)
f=auth.MemoryPulseAuthTests();f.setUp()
try:
 unknown=BasicAuthProvider(username='synthetic-other',password_hash=hash_password('synthetic-other-password'),secret=secrets.token_bytes(32))
 register_global_provider(unknown)
 try:
  response=f.client.post('/auth/password-login',json={'provider':'basic','username':'synthetic-other','password':'synthetic-other-password'})
  base='/api/plugins/lifeos-hook-bridge/memory'
  pulse=f.client.get(base+'/pulse/snapshot');review=f.client.post(base+'/review',json={'tool':'lifeos_memory_search','arguments':{'query':'authenticated PULSE'}})
  emit({'probe':'distinct_authenticated_unknown_account','login':response.status_code,'pulse_status':pulse.status_code,'review_status':review.status_code,'review':review.json()})
 finally:restore_registration('basic',unknown,f.provider)
 f.client.cookies.clear();f.login();f.configuration.update(lambda c:c['accounts'].pop('dashboard:basic:synthetic-owner'))
 search=f.client.post(base+'/review',json={'tool':'lifeos_memory_search','arguments':{'query':'authenticated PULSE'}}).json();ref=search['results'][0]['reference']
 forgot=f.client.post(base+'/review',json={'tool':'lifeos_memory_forget','arguments':{'reference':ref,'request_id':'revoked-owner-forget'}})
 emit({'probe':'revoked_owner_mutation','forget_status':forgot.status_code,'forget_body':forgot.json(),'native_recall_after':f.fixture.fixture.fixture.fixture.memory.recall(OWNER,'authenticated PULSE')})
finally:f.doCleanups()
f=auth.MemoryPulseAuthTests();f.setUp()
try:
 n=f.fixture.fixture.fixture.fixture
 s=n.remember('RULE: begins','isolated-contract','principal');n.memory.forget(OWNER,s['reference'],'isolated-contract-forget')
 report={'findings':[{'severity':'critical','detail':{'begins':1,'ends':2,'inverted':False}}]}
 projected=filter_report(n.memory,OWNER,json.dumps(report),datetime.now(timezone.utc).isoformat())
 module=str(f.fixture.root/'LIFEOS/TOOLS/lib/MemoryAccess.ts')
 code='const m=await import('+json.dumps(module)+');try {console.log(JSON.stringify({ok:true,report:m.filterMemoryDiagnostic('+json.dumps(report)+','+json.dumps(datetime.now(timezone.utc).isoformat())+')}))} catch(e) {console.log(JSON.stringify({ok:false,message:String(e)}))}'
 env=dict(os.environ,HOME=str(n.home),LIFEOS_MEMORY_CONTEXT=json.dumps(asdict(f.fixture.fixture.fixture.context)),BUN_CONFIG_NO_AUTO_INSTALL='1');env.pop('LIFEOS_MEMORY_INTERNAL',None)
 r=subprocess.run(['bun','--no-install','-e',code],cwd=f.fixture.root,env=env,capture_output=True,text=True,timeout=45)
 emit({'probe':'native_shape_contract_exact','python_response':projected,'native_code':r.returncode,'native_stdout':r.stdout,'native_stderr':r.stderr})
finally:f.doCleanups()
