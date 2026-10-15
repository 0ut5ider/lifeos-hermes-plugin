# ABOUTME: Admits one synthetic daily-layout update after authenticating the real test owner.
# ABOUTME: Uses the public release admission, private worker receipt, and real owner systemd service manager.
import importlib,json,os,subprocess,sys,types
from pathlib import Path
sys.dont_write_bytecode=True
root=Path('/home/lifeos-hermes/releases/qualification-0.5.0');profile=Path('/home/lifeos-hermes/.hermes')
preparation=json.loads((root/'daily-layout-interruption-preparation.json').read_bytes());job=profile/'.lifeos-releases'/preparation['preparation']['identifier']
request=json.loads((job/'request.json').read_bytes());sys.path.insert(0,request['runtime']['source'])
namespace=types.ModuleType('observed_release_worker');namespace.__path__=[str(job/'worker')];sys.modules[namespace.__name__]=namespace
worker=importlib.import_module(namespace.__name__+'.release_worker')
os.environ.update(HERMES_HOME=str(profile),XDG_RUNTIME_DIR='/run/user/'+str(os.getuid()),DBUS_SESSION_BUS_ADDRESS='unix:path=/run/user/'+str(os.getuid())+'/bus')
plan=worker.validate_plan(job,request)
assert plan['native_mount_required'] is True
build=json.loads((root/'stable-build.json').read_bytes())
assert request['version']=='0.5.0' and request['commit']==build['head']
assert request['package_sha256']==build['archive_sha256']
import httpx,time
credentials=json.loads(Path('/home/lifeos-hermes/install-input/dashboard-access.json').read_bytes())
with httpx.Client(base_url='http://127.0.0.1:18819',timeout=60) as client:
 response=client.post('/auth/password-login',json={'provider':'basic',**credentials});assert response.status_code==200
 response=client.get('/api/auth/me');assert response.status_code==200
 session=response.json();assert session['provider']=='basic' and session['user_id']=='adrian' and session['expires_at']>time.time()
 source=worker.recovery_bridge(job,profile)
 configuration=source.memory_module('memory_service').MemoryConfiguration(profile/'lifeos-memory.json')
 account='dashboard:'+session['provider']+':'+session['user_id']
 configuration.check_owner(configuration.load(),account)
 administration=source.memory_administration()
 authorization=administration.issue(configuration,account,ttl=3600,binding=administration.job_binding(job,request,'apply'))
 recovery_authorization=administration.issue(configuration,account,ttl=3600,binding=administration.job_binding(job,request,'recover'))
 (root/'private-recovery-authority.json').write_text(json.dumps({'authorization':str(recovery_authorization),'operation':job.name,'account':account,'expires_at':session['expires_at']})+'\n')
 (root/'private-recovery-authority.json').chmod(0o600)
home=Path(request['account_home']);assert home==Path('/home/lifeos-hermes')
with worker.operation_lock(job,name='launch.lock'):
 worker.admit_operation(job,request,'apply',authorization=authorization)
 unit='lifeos-release-'+job.name
 command=['systemd-run','--user','--wait','--collect','--unit='+unit,'--setenv=HOME='+str(home),'--setenv=HERMES_HOME='+str(profile),'--setenv=PATH='+str(home/'.local/bin')+':'+os.defpath,'--setenv=PYTHONDONTWRITEBYTECODE=1',request['runtime']['python'],'-B',str(root/'interrupt_rehearsal_worker.py'),str(job)]
 result=subprocess.run(command,capture_output=True,text=True,timeout=900);assert result.returncode==73,result.stderr
 worker.publish(job/'worker-launch.json',json.dumps({'kind':'service','unit':unit}).encode())
(root/'observed-worker-started.json').write_text(json.dumps({'operation':job.name,'test_fixture_only':True,'state':'interrupted','exit_status':result.returncode,'unit_collected':True,'candidate_commit':request['commit'],'authenticated_owner_verified':True,'native_mount_required':True},indent=2)+'\n')
