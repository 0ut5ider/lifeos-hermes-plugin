# ABOUTME: Verifies route review from the actual isolated managed Hermes interpreter.
# ABOUTME: Records only dependency failure flags and the resolved nonsecret route identity.
import importlib
import json
import os
from pathlib import Path
import subprocess
import sys
import types

os.umask(0o077)
home=Path('/home/lifeos-hermes');profile=home/'.hermes'
assert os.getuid()==1000 and Path.home()==home
operation=sys.argv[1];label=sys.argv[2]
assert len(operation)==32 and all(x in '0123456789abcdef' for x in operation)
assert label and all(x in 'abcdefghijklmnopqrstuvwxyz0123456789-' for x in label)
host=profile/'.lifeos-releases'/operation/'hermes'
sys.path.insert(0,str(host))
from hermes_cli import _launchers
code='''import importlib,json,types
from pathlib import Path
profile=Path(sys.argv[1])
package=types.ModuleType('portability_route_runtime_probe')
package.__path__=[str(profile/'plugins/lifeos-hook-bridge')]
sys.modules[package.__name__]=package
module=importlib.import_module(package.__name__+'.memory_owner_access')
receipt={'status':'FAIL','managed_runtime':True,'daily_changed':False}
def trace(frame,event,argument):
 if event=='exception' and frame.f_code.co_name=='_route' and frame.f_code.co_filename.endswith('/memory_owner_access.py'):
  result=frame.f_locals.get('result')
  if result is not None:
   receipt['route_child_missing_dotenv']="No module named 'dotenv'" in result.stderr
 return trace
sys.settrace(trace)
try:
 route=module._route(profile,(profile/'config.yaml').read_bytes())
 receipt.update(status='PASS',model=route['model'],provider=route['provider'],model_route=route['model_route'])
except Exception as error:
 receipt['error_type']=type(error).__name__
finally:sys.settrace(None)
print(json.dumps(receipt))
raise SystemExit(0 if receipt['status']=='PASS' else 1)
'''
command=_launchers.runtime_command(host,[str(profile)],code=code)
command.insert(1,'-B')
result=subprocess.run(command,capture_output=True,text=True,timeout=90,
    env=dict(os.environ,HERMES_HOME=str(profile),HOME=str(home)))
receipt=json.loads(result.stdout)
receipt['exit_code']=result.returncode
assert not result.stderr,result.stderr
(home/'install-input'/('route-runtime-'+label+'.json')).write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt))
raise SystemExit(result.returncode)
