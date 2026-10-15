# ABOUTME: Completes the synthetic owner's fixed local Pulse HTTP configuration.
# ABOUTME: Verifies real dashboard authority before updating the installed configuration.
import importlib,json,os,sys,time
from pathlib import Path
import httpx
os.umask(0o077)
home=Path('/home/lifeos-hermes');profile=home/'.hermes';stage=home/'releases/qualification-0.5.0'
prepared=json.loads((stage/'fresh-preparation.json').read_bytes())
sys.path[:0]=[str(profile/'plugins'),str(profile/'.lifeos-releases'/prepared['preparation']['identifier']/'hermes')]
module=importlib.import_module('lifeos-hook-bridge.memory_service')
configuration=module.MemoryConfiguration(profile/'lifeos-memory.json')
credentials=json.loads((home/'install-input/dashboard-access.json').read_bytes())
with httpx.Client(base_url='http://127.0.0.1:18819',timeout=90) as client:
 assert client.post('/auth/password-login',json={'provider':'basic',**credentials}).status_code==200
 session=client.get('/api/auth/me').json()
 assert session['provider']=='basic' and session['user_id']=='qualification-owner' and session['expires_at']>time.time()
 account='dashboard:basic:qualification-owner'
 def configure(value):
  configuration.check_owner(value,account)
  assert 'pulse_http' not in value
  value['pulse_http']={'dashboard_base_url':'http://127.0.0.1:18819'}
 configuration.update(configure)
report={'status':'PASS','authenticated_owner_verified':True,'synthetic_fixture_setup_only':True,
 'missing_pulse_http_binding_confirmed':True,'fixed_local_dashboard_binding_configured':True,'product_code_changed':False,'production_guest_changed':False}
(stage/'fresh-http-configuration.json').write_text(json.dumps(report,indent=2)+'\n')
