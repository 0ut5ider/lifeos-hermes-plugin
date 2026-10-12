# ABOUTME: Exercises complete release updates with real native owner authentication and scoped mount grants.
# ABOUTME: Uses an isolated account, synthetic native data, actual HTTP routes, and real user service definitions.
import importlib.util
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys
from threading import Thread
import time
from urllib.error import HTTPError
from urllib.request import Request, urlopen

home=Path.home();profile=home/'.hermes';root=home/'release-fixture'
os.environ.update(HERMES_HOME=str(profile),XDG_RUNTIME_DIR='/run/user/'+str(os.getuid()),DBUS_SESSION_BUS_ADDRESS='unix:path=/run/user/'+str(os.getuid())+'/bus')
os.environ['PATH']=str(home/'.local/bin')+':'+os.environ.get('PATH',os.defpath)
prior_jobs=[f.parent for f in (profile/'.lifeos-releases').glob('*/status.json') if json.loads(f.read_bytes())['state']=='applied']
assert len(prior_jobs)==1
prior_request=json.loads((prior_jobs[0]/'request.json').read_bytes())
sys.path.insert(0,prior_request['runtime']['source'])
# The public preparation driver supplies real HTTP release assets and the pinned manager.
source=(root/'prepare_managed_update_3a.py').read_text().split("report = {'profile':")[0]
exec(compile(source,str(root/'prepare_managed_update_3a.py'),'exec'),globals())
from fastapi import FastAPI,Depends
import uvicorn
from hermes_cli.dashboard_auth.middleware import gated_auth_middleware
from hermes_cli.dashboard_auth.registry import register_global_provider,unregister_global_provider
from plugins.dashboard_auth.basic import BasicAuthProvider,hash_password
from lifeos_development_manager.release_stage import load_bridge
installed=Path(prior_request['installed'])
bridge=load_bridge(profile/'plugins/lifeos-hook-bridge')
drift=bridge.memory_module('version_drift')
baseline_path=drift.default_baseline_path(installed.parent)
prior_baseline=drift.load_baseline(baseline_path,installed)
# This approved synthetic baseline has one prior program variant. The candidate remains unmodified.
variant=installed/'skills/CreateSkill/SKILL.md'
variant.write_text(variant.read_text()+'\n<!-- Synthetic prior installed program variant. -->\n')
drift.save_baseline(drift.create_baseline(Path(prior_baseline['source_root']),installed),baseline_path,renew=True)
units=home/'.config/systemd/user';units.mkdir(parents=True,exist_ok=True,mode=0o700)
for role,unit in {'gateway':'hermes-gateway.service','dashboard':'hermes-dashboard.service','pulse':'com.lifeos.pulse.service'}.items():
 cwd={'gateway':profile,'dashboard':installed.parent,'pulse':installed/'LIFEOS/PULSE'}[role]
 command={'gateway':str(home/'.local/bin/hermes')+' gateway run','dashboard':str(home/'.local/bin/hermes')+' dashboard --no-open --skip-build --port 18999','pulse':str(home/'.local/bin/bun')+' '+str(installed/'LIFEOS/PULSE/server.ts')}[role]
 (units/unit).write_text('[Unit]\nDescription=Synthetic release qualification '+role+'\n[Service]\nType=simple\nWorkingDirectory='+str(cwd)+'\nEnvironment=HERMES_HOME='+str(profile)+'\nExecStart='+command+'\nKillMode=mixed\n')
 (units/unit).chmod(0o600)
subprocess.run(['systemctl','--user','daemon-reload'],check=True,capture_output=True)

spec=importlib.util.spec_from_file_location('synthetic_bridge_dashboard',profile/'plugins/lifeos-hook-bridge/dashboard/plugin_api.py')
bridge_api=importlib.util.module_from_spec(spec);spec.loader.exec_module(bridge_api)
spec=importlib.util.spec_from_file_location('synthetic_release_dashboard',profile/'plugins/lifeos-release-manager/dashboard/plugin_api.py')
release_api=importlib.util.module_from_spec(spec);spec.loader.exec_module(release_api)
password=secrets.token_urlsafe(32)
provider=BasicAuthProvider(username='synthetic-owner',password_hash=hash_password(password),secret=secrets.token_bytes(32))
register_global_provider(provider)
token=provider.complete_password_login(username='synthetic-owner',password=password).access_token
app=FastAPI();app.state.auth_required=True;app.middleware('http')(gated_auth_middleware)
app.include_router(bridge_api.router,prefix='/api/plugins/lifeos-hook-bridge')
app.include_router(release_api.router,prefix='/api/plugins/lifeos-release-manager')
@app.post('/fixture/activate')
def activate(account=Depends(release_api.owner)):
 configuration=bridge_api._memory_preferences().configuration
 candidate=load_bridge(root/'source-3a/lifeos_hook_bridge')
 backup=candidate.memory_module('profile_backup').create(configuration,root/'ownership-backup-3a',account=account)
 transaction=bridge.memory_module('memory_ownership').OwnershipTransaction(configuration)
 plan=transaction.preview(Path(backup['snapshot']),backup['signature'],account=account)
 result=transaction.apply(Path(backup['snapshot']),backup['signature'],plan['signature'],account=account)
 return {'ownership_enabled':configuration.load()['ownership_enabled'],'state':result['state']}
listener=socket.socket();listener.bind(('127.0.0.1',0));endpoint='http://127.0.0.1:'+str(listener.getsockname()[1])
backend=uvicorn.Server(uvicorn.Config(app,log_level='critical',access_log=False,lifespan='off',ws='none'))
backend_thread=Thread(target=backend.run,kwargs={'sockets':[listener]});backend_thread.start()
while not backend.started:
 assert backend_thread.is_alive();time.sleep(.01)
def http(path,body=None,method='POST',authenticated=True):
 headers={'Origin':endpoint}
 if authenticated:headers['Authorization']='Bearer '+token
 if body is not None:headers['Content-Type']='application/json'
 request=Request(endpoint+path,data=json.dumps(body).encode() if body is not None else None,headers=headers,method=method)
 try:
  with urlopen(request,timeout=300) as response:return response.status,json.loads(response.read())
 except HTTPError as error:
  with error:return error.code,json.loads(error.read())
def wait(job,desired):
 deadline=time.monotonic()+600
 while time.monotonic()<deadline:
  value=cli.read_private(job/'status.json')
  if value['state'] in {'applied','rolled_back','recovery_required','rejected'}:
   assert value['state']==desired,value
   return value
  time.sleep(.2)
 raise TimeoutError('The synthetic detached worker does not complete')
report={'test_fixture_only':True,'personal_data_imported':False,'production_qualified':False,'account_uid':os.getuid(),'candidate_commit':package['head']}
start=time.monotonic()
try:
 assert http('/api/plugins/lifeos-release-manager/operations',method='GET',authenticated=False)[0]==401
 code,claim=http('/api/plugins/lifeos-hook-bridge/memory',method='GET');assert code==200,claim
 report['authenticated_owner_binding']='PASS'
 connector=installed/'LIFEOS/USER/CONFIG/memory-access.json'
 connector.write_text(json.dumps({'version':1,'command':[str(Path(sys.executable)),str(profile/'plugins/lifeos-hook-bridge/memory_rpc.py'),'--configuration',str(profile/'lifeos-memory.json')]}));connector.chmod(0o600)
 # The public owner memory route creates and recalls one synthetic fact through the governed native writer.
 args={'category':'project','project':'release-qualification','title':'Synthetic update marker','content':'Synthetic managed update marker Q-MANAGED-3A-20261012','request_id':'managed-update-3a-20261012'}
 code,saved=http('/api/plugins/lifeos-hook-bridge/memory/review',{'tool':'lifeos_memory_remember','arguments':args});assert code==200 and saved.get('status') in {'committed','saved','ok'},saved
 report['synthetic_memory_save']='PASS'
 if not bridge_api._memory_preferences().configuration.load()['ownership_enabled']:
  code,activation=http('/fixture/activate');assert code==200 and activation['ownership_enabled'] is True,activation
 report['ownership_enabled']=True
 report['governed_ownership_activation']='PASS'
 result=cli.prepare(profile,package['version'],catalog=catalog.ReleaseCatalog(api_origin=origin,asset_origin=origin))
 job,request=cli.operation(profile,result['identifier']);report['operation']=job.name
 code,review=http('/api/plugins/lifeos-release-manager/operations/'+job.name+'/review');assert code==200,review
 assert review['native_mount_required'] is True,review
 report['native_mount_required']=True
 try:cli.launch(profile,job.name,'apply')
 except PermissionError:report['missing_owner_grant_refusal']='PASS'
 else:raise AssertionError('The managed update accepts no owner grant')
 code,admission=http('/api/plugins/lifeos-release-manager/operations/'+job.name+'/apply');assert code==200,admission
 assert cli.read_private(job/'request.json').get('memory_authorization')
 wait(job,'applied');report['authenticated_apply']='PASS'
 assert not list((profile/'.lifeos-memory-admin').glob('*.json'))
 report['grant_revoked_after_apply']='PASS'
 code,recalled=http('/api/plugins/lifeos-hook-bridge/memory/review',{'tool':'lifeos_memory_search','arguments':{'query':'Q-MANAGED-3A-20261012'}})
 assert code==200 and recalled.get('results'),recalled
 report['synthetic_memory_recall_after_apply']='PASS'
 code,admission=http('/api/plugins/lifeos-release-manager/operations/'+job.name+'/restore');assert code==200,admission
 wait(job,'rolled_back');report['authenticated_rollback']='PASS'
 assert not list((profile/'.lifeos-memory-admin').glob('*.json'))
 assert variant.read_text().endswith('<!-- Synthetic prior installed program variant. -->\n')
 code,recalled=http('/api/plugins/lifeos-hook-bridge/memory/review',{'tool':'lifeos_memory_search','arguments':{'query':'Q-MANAGED-3A-20261012'}})
 assert code==200 and recalled.get('results'),recalled
 report['synthetic_memory_recall_after_rollback']='PASS'
 report['grant_revoked_after_rollback']='PASS';report['status']='PASS'
except BaseException as error:
 report.update(status='FAIL',failure_type=type(error).__name__,failure=str(error));raise
finally:
 backend.should_exit=True;backend_thread.join(10);listener.close();unregister_global_provider(provider.name,provider)
 server.shutdown();thread.join();server.server_close()
 report['elapsed_seconds']=time.monotonic()-start
 (root/'managed-update-3a.json').write_text(json.dumps(report,indent=2)+'\n');(root/'managed-update-3a.json').chmod(0o600)
 (root/'managed-update-3a.done').write_text('0\n' if report.get('status')=='PASS' else '1\n')
