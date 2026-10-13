# ABOUTME: Admits and starts one actual development update with frozen-worker diagnostics.
# ABOUTME: Uses the public release admission, private worker receipt, and real owner systemd service manager.
import importlib,json,os,subprocess,sys,types
from pathlib import Path
root=Path.home()/'releases/qualification-20261012-041';profile=Path.home()/'.hermes'
preparation=json.loads((root/'development-preparation-interruption.json').read_bytes());job=profile/'.lifeos-releases'/preparation['preparation']['identifier']
request=json.loads((job/'request.json').read_bytes());sys.path.insert(0,request['runtime']['source'])
namespace=types.ModuleType('observed_release_worker');namespace.__path__=[str(job/'worker')];sys.modules[namespace.__name__]=namespace
worker=importlib.import_module(namespace.__name__+'.release_worker')
os.environ.update(HERMES_HOME=str(profile),XDG_RUNTIME_DIR='/run/user/'+str(os.getuid()),DBUS_SESSION_BUS_ADDRESS='unix:path=/run/user/'+str(os.getuid())+'/bus')
with worker.operation_lock(job,name='launch.lock'):
 worker.admit_operation(job,request,'apply')
 unit='lifeos-release-'+job.name
 command=['systemd-run','--user','--collect','--unit='+unit,'--setenv=HOME='+str(Path.home()),'--setenv=HERMES_HOME='+str(profile),'--setenv=PATH='+str(Path.home()/'.local/bin')+':'+os.defpath,'--setenv=PYTHONDONTWRITEBYTECODE=1',request['runtime']['python'],'-B',str(root/'interrupt_installed_worker.py'),str(job)]
 result=subprocess.run(command,capture_output=True,text=True,timeout=30);assert result.returncode==0,result.stderr
 worker.publish(job/'worker-launch.json',json.dumps({'kind':'service','unit':unit}).encode())
(root/'observed-worker-started.json').write_text(json.dumps({'operation':job.name,'test_fixture_only':True,'state':'queued','candidate_commit':request['commit']},indent=2)+'\n')
