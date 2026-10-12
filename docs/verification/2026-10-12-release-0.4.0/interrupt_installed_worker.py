# ABOUTME: Executes an admitted frozen worker with command diagnostics at its public checkpoint boundary.
# ABOUTME: Keeps raw command output private and exports no credentials or personal records.
import importlib,json,os,subprocess,sys,types
from pathlib import Path
job=Path(sys.argv[1]).absolute()
namespace=types.ModuleType('observed_release_worker');namespace.__path__=[str(job/'worker')];sys.modules[namespace.__name__]=namespace
worker=importlib.import_module(namespace.__name__+'.release_worker')
request=worker.read_private(job/'request.json')
def checkpoint(point):
 if point=='programs-published':os._exit(73)
 if point!='native-mounted':return
 commands=[('prepared',request['runtime']['hermes'])]+[('installed-'+str(i),value) for i,value in enumerate(worker.read_private(job/'plan.json')['launchers'])]
 for label,command in commands:
  result=subprocess.run([command,'lifeos-version'],env=worker.service_environment(request),capture_output=True,text=True,timeout=120)
  worker.publish(job/('observed-'+label+'.json'),(json.dumps({'exit_code':result.returncode,'stdout':result.stdout,'stderr':result.stderr})+'\n').encode())
result=worker.execute(job,'apply',checkpoint=checkpoint)
print(json.dumps(result))
