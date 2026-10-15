# ABOUTME: Measures active and retained installation lease compatibility without applying removal.
# ABOUTME: Authenticates the fixture owner and exports only lock admission and safe source-frame metadata.
import importlib
import json
import os
from pathlib import Path
import sys
import types

home=Path('/home/lifeos-hermes');profile=home/'.hermes'
if os.getuid()!=1000 or Path.home()!=home:raise RuntimeError('Use the disposable guest owner')
os.umask(0o077)
namespace=types.ModuleType('portability_lease_probe');namespace.__path__=[str(profile/'plugins/lifeos-release-manager')]
sys.modules[namespace.__name__]=namespace
stage=importlib.import_module(namespace.__name__+'.release_stage')
state=importlib.import_module(namespace.__name__+'.removal_state')
auth=importlib.import_module(namespace.__name__+'.removal_recovery')
credentials=json.loads((home/'install-input/dashboard-access.json').read_bytes())
owner=auth.authenticate(profile,credentials['username'],credentials['password'],'dashboard:basic:portability-owner')
del credentials
active=stage.load_bridge(profile/'plugins/lifeos-hook-bridge')
retained,configuration,job,plan=state.retained(profile)
configuration.check_owner(configuration.load(),owner)
receipt={'read_only':True,'daily_changed':False,'workflow':job.name,'phase':'publication_constructor'}
try:
    publication=importlib.import_module(namespace.__name__+'.removal_publication').RemovalPublication(profile,plan['signature'])
    receipt['phase']='active_lease_borrowed_by_retained_publication'
    with active.memory_module('installation_lock').installation_lock(profile) as lease:
        with publication.source.memory_module('installation_lock').installation_lock(profile,lease=lease):pass
    receipt['active_to_retained']='PASS'
except Exception as error:
    receipt.update(active_to_retained='REFUSED',error_type=type(error).__name__)
    if str(error)=='The installation operation requires an issued owner lease':receipt['reason']=str(error)
    trace=error.__traceback__;frames=[]
    while trace:
        frames.append({'file':Path(trace.tb_frame.f_code.co_filename).name,'function':trace.tb_frame.f_code.co_name,'line':trace.tb_lineno});trace=trace.tb_next
    receipt['frames']=frames
with retained.memory_module('installation_lock').installation_lock(profile) as lease:
    with retained.memory_module('installation_lock').installation_lock(profile,lease=lease):pass
receipt['retained_to_retained']='PASS'
(home/'install-input/removal-lease-probe.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt))
