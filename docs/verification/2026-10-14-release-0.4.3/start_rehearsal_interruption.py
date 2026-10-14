# ABOUTME: Admits one synthetic daily-layout update after authenticating the real test owner.
# ABOUTME: Uses the public release admission, private worker receipt, and real owner systemd service manager.
import importlib,json,os,subprocess,sys,types
from pathlib import Path
sys.dont_write_bytecode=True
root=Path('/home/lifeos-hermes/releases/qualification-0.4.3');profile=Path('/home/lifeos-hermes/.hermes')
preparation=json.loads((root/'daily-layout-interruption-preparation.json').read_bytes());job=profile/'.lifeos-releases'/preparation['preparation']['identifier']
request=json.loads((job/'request.json').read_bytes());sys.path.insert(0,request['runtime']['source'])
namespace=types.ModuleType('observed_release_worker');namespace.__path__=[str(job/'worker')];sys.modules[namespace.__name__]=namespace
worker=importlib.import_module(namespace.__name__+'.release_worker')
os.environ.update(HERMES_HOME=str(profile),XDG_RUNTIME_DIR='/run/user/'+str(os.getuid()),DBUS_SESSION_BUS_ADDRESS='unix:path=/run/user/'+str(os.getuid())+'/bus')
assert worker.validate_plan(job,request)['native_mount_required'] is False, 'This operator does not admit native memory changes'
assert request['version']=='0.4.3' and request['commit']=='a1abb579558edcf29f7cd04ecfd998995d48db54'
import httpx,time
credentials=json.loads(Path('/home/lifeos-hermes/install-input/dashboard-access.json').read_bytes())
with httpx.Client(base_url='http://127.0.0.1:18819',timeout=60) as client:
 response=client.post('/auth/password-login',json={'provider':'basic',**credentials});assert response.status_code==200
 response=client.get('/api/auth/me');assert response.status_code==200
 session=response.json();assert session['provider']=='basic' and session['user_id']=='adrian' and session['expires_at']>time.time()
 source=worker.recovery_bridge(job,profile)
 configuration=source.memory_module('memory_service').MemoryConfiguration(profile/'lifeos-memory.json')
 configuration.check_owner(configuration.load(),'dashboard:'+session['provider']+':'+session['user_id'])
home=Path(request['account_home']);assert home==Path('/home/lifeos-hermes')
with worker.operation_lock(job,name='launch.lock'):
 worker.admit_operation(job,request,'apply')
 unit='lifeos-release-'+job.name
 command=['systemd-run','--user','--wait','--collect','--unit='+unit,'--setenv=HOME='+str(home),'--setenv=HERMES_HOME='+str(profile),'--setenv=PATH='+str(home/'.local/bin')+':'+os.defpath,'--setenv=PYTHONDONTWRITEBYTECODE=1',request['runtime']['python'],'-B',str(root/'interrupt_rehearsal_worker.py'),str(job)]
 result=subprocess.run(command,capture_output=True,text=True,timeout=120);assert result.returncode==73,result.stderr
 worker.publish(job/'worker-launch.json',json.dumps({'kind':'service','unit':unit}).encode())
(root/'observed-worker-started.json').write_text(json.dumps({'operation':job.name,'test_fixture_only':True,'state':'interrupted','exit_status':result.returncode,'unit_collected':True,'candidate_commit':request['commit'],'authenticated_owner_verified':True,'native_mount_required':False},indent=2)+'\n')
