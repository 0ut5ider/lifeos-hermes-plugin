# ABOUTME: Exercises the actual prepared host dashboard mount and auth gates.
# ABOUTME: Uses an installed plugin copy and synthetic owner facts in a temporary home.
from pathlib import Path
import os,sys,json,shutil
ROOT=Path.cwd();HOST=Path('/home/outsider/.cache/lifeos-plugin-memory/source-gate-20260930-native/hermes')
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'tests'))
from test_memory_sharing import MemorySharingTests
from lifeos_hook_bridge.memory_service import MemoryConfiguration
f=MemorySharingTests();f.setUp()
try:
 home=f.fixture.fixture.home;profile=f.fixture.config.parent
 os.environ.update(HOME=str(home),HERMES_HOME=str(profile),HERMES_DASHBOARD_SESSION_TOKEN='synthetic-review-token')
 os.chdir(home)
 plugin=profile/'plugins/lifeos-hook-bridge';plugin.parent.mkdir(parents=True,exist_ok=True)
 shutil.copytree(ROOT/'lifeos_hook_bridge',plugin,ignore=shutil.ignore_patterns('__pycache__'))
 (profile/'config.yaml').write_text('plugins:\n  enabled: [lifeos-hook-bridge]\n')
 MemoryConfiguration(profile/'lifeos-memory.json').save(f.fixture.configuration)
 f.fixture.fixture.remember('Synthetic authenticated dashboard fact','auth-probe')
 sys.path.insert(0,str(HOST))
 from hermes_cli import web_server
 from fastapi.testclient import TestClient
 web_server.app.state.bound_host='127.0.0.1';web_server.app.state.bound_port=8080
 endpoint='/api/plugins/lifeos-hook-bridge/memory'
 client=TestClient(web_server.app,base_url='http://127.0.0.1:8080')
 for mode,headers in [('none',{}),('invalid',{'X-Hermes-Session-Token':'wrong'}),('valid',{'X-Hermes-Session-Token':'synthetic-review-token'})]:
  response=client.post(endpoint+'/review',headers=headers,json={'tool':'lifeos_memory_search','arguments':{'query':'authenticated dashboard'}})
  print(json.dumps({'case':mode,'status':response.status_code,'body':response.json()}),flush=True)
  assert response.status_code==(200 if mode=='valid' else 401)
 web_server.app.state.auth_required=True
 response=client.post(endpoint+'/review',json={'tool':'lifeos_memory_search','arguments':{'query':'authenticated dashboard'}})
 print(json.dumps({'case':'cookie_gate_no_session','status':response.status_code,'body':response.json()}),flush=True)
 assert response.status_code==401
 client.close()
finally:f.doCleanups()
