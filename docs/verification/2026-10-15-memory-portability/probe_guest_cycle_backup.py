# ABOUTME: Measures profile backup inventory admission after installed software removal and rollback.
# ABOUTME: Authenticates the current owner and exports only safe exception frames and file counts.
import importlib
import json
import os
from pathlib import Path
import sys
import types

home=Path('/home/lifeos-hermes');profile=home/'.hermes'
if os.getuid()!=1000 or Path.home()!=home:raise RuntimeError('Use the disposable guest owner')
os.umask(0o077)
package=types.ModuleType('portability_cycle_inventory_probe')
package.__path__=[str(profile/'plugins/lifeos-release-manager')];sys.modules[package.__name__]=package
credentials=json.loads((home/'install-input/dashboard-access.json').read_bytes())
owner=importlib.import_module(package.__name__+'.removal_recovery').authenticate(profile,
    credentials['username'],credentials['password'],'dashboard:basic:portability-owner')
del credentials
source,configuration=importlib.import_module(package.__name__+'.memory_workflow')._source(profile)
selected=configuration.load();configuration.check_owner(selected,owner)
backup=source.memory_module('profile_backup')
receipt={'read_only':True,'owner_authenticated':True,'daily_changed':False,'phase':'profile_inventory',
    'native_records_read':False,'profile_file_contents_read':False}
try:
    excluded=[];entries=backup._entries(profile,(Path(selected['root']).parent/'.config/LIFEOS/USER').resolve(),excluded)
    receipt.update(status='PASS',entries=len(entries),excluded_entries=len(excluded))
except Exception as error:
    receipt.update(status='REFUSED',error_type=type(error).__name__)
    if str(error) in ('The profile backup exceeds its source count limit','An external profile link requires reviewed source coverage',
        'A profile source belongs to another operating-system owner'):
        receipt['reason']=str(error)
    trace=error.__traceback__;frames=[]
    while trace:
        if trace.tb_frame.f_code.co_name=='_entries':
            locals_=trace.tb_frame.f_locals
            entries=locals_.get('entries',[]);pending=locals_.get('pending',[])
            receipt['count_at_refusal']={'entries':len(entries),'pending':len(pending),
                'portability_workspace_entries':sum(row[0].is_relative_to(profile/'.lifeos-portability') for row in entries),
                'portability_workspace_pending':sum(path.is_relative_to(profile/'.lifeos-portability') for path in pending)}
        frames.append({'file':Path(trace.tb_frame.f_code.co_filename).name,'function':trace.tb_frame.f_code.co_name,'line':trace.tb_lineno});trace=trace.tb_next
    receipt['frames']=frames
(home/'install-input/cycle-backup-inventory-probe.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt))
