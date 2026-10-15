# ABOUTME: Compares read-only removal consumer admission inside an actual disposable user unit.
# ABOUTME: Exports only the admission phase and service definition paths without command or environment content.
import importlib
import json
import os
from pathlib import Path
import sys
import types

os.umask(0o077);home=Path('/home/lifeos-hermes');profile=home/'.hermes'
assert os.getuid()==1000 and Path.home()==home
sys.path.insert(0,str(profile/'.lifeos-releases/3594860cf9014923b2450b51d6214ce0/hermes'))
package=types.ModuleType('portability_coordinator_probe');package.__path__=[str(profile/'plugins/lifeos-release-manager')]
sys.modules[package.__name__]=package
workflow=importlib.import_module(package.__name__+'.memory_workflow')
preparation=importlib.import_module(package.__name__+'.removal_preparation')
auth=importlib.import_module(package.__name__+'.removal_recovery')
job,request=workflow._job(profile,'b3d205d12ac94b41b253fedd63a9d314')
credentials=json.loads((home/'install-input/dashboard-access.json').read_bytes())
owner=auth.authenticate(profile,credentials['username'],credentials['password'],request['owner']);del credentials
source,configuration=workflow._source(profile)
receipt={'status':'FAIL','read_only':True,'daily_changed':False}
def trace(frame,event,argument):
    if event=='exception' and frame.f_code.co_name=='unit_files':
        values=frame.f_locals.get('values',{})
        receipt['definition']=values.get('FragmentPath')
    return trace
try:
    with source.memory_module('installation_lock').installation_lock(profile) as lease:
        services=source.memory_module('profile_services').ProfileServices(profile,Path(configuration.load()['root']),installation_lease=lease)
        sys.settrace(trace)
        preparation._consumers(profile,Path(configuration.load()['root']),services)
        receipt['status']='PASS'
except Exception as error:
    receipt.update(error_type=type(error).__name__,reason=str(error))
finally:
    sys.settrace(None)
    (home/'install-input/coordinator-admission-probe.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt))
