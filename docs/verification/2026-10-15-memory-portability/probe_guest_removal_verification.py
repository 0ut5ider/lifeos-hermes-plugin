# ABOUTME: Locates an installed removal verification refusal through actual read-only checks.
# ABOUTME: Exports fixed diagnostic metadata without memory contents, credentials, or narration.
import importlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import types

home=Path('/home/lifeos-hermes');profile=home/'.hermes'
if os.getuid()!=1000 or Path.home()!=home:raise RuntimeError('Use the disposable guest owner')
os.umask(0o077)
identifier='4bf8386002c3402a8f0ffb933fb8484c'
job=profile/'.lifeos-portability'/identifier
package=types.ModuleType('portability_verification_probe')
package.__path__=[str(job/'removal/recovery-manager')];sys.modules[package.__name__]=package
state=importlib.import_module(package.__name__+'.removal_state')
workflow=importlib.import_module(package.__name__+'.memory_workflow')
removal=importlib.import_module(package.__name__+'.removal_workflow')
source,configuration,selected,plan=state.retained(profile)
credentials=json.loads((home/'install-input/dashboard-access.json').read_bytes())
owner=importlib.import_module(package.__name__+'.removal_recovery').authenticate(
    profile,credentials['username'],credentials['password'],plan['owner'])
del credentials
receipt={'workflow':identifier,'read_only':True,'model_turn_executed':False,'daily_changed':False,'checks':{}}
phase='stock_identity'
try:
    runtime=removal._stock(job,plan);receipt['checks'][phase]='PASS'
    with source.memory_module('installation_lock').installation_lock(profile) as lease:
        publication=importlib.import_module(package.__name__+'.removal_publication').RemovalPublication(
            profile,plan['signature'],installation_lease=lease)
        phase='program_targets';publication.programs.check_applied();receipt['checks'][phase]='PASS'
        phase='services';publication.services.verify(plan['service_signature']);receipt['checks'][phase]='PASS'
        phase='owner';publication._owner(owner);receipt['checks'][phase]='PASS'
        read=source.memory_module('mount_transaction')._read
        names=('config.yaml','SOUL.md','lifeos-memory.json','memories/MEMORY.md','memories/USER.md')
        captured={name:read(profile/name) for name in names}
        expected={name:captured['memories/'+name][0].decode() for name in ('MEMORY.md','USER.md')}
        original_run=subprocess.run
        def measured_run(*args,**kwargs):
            result=original_run(*args,**kwargs)
            receipt['child']={'exit_code':result.returncode,'stderr_bytes':len(result.stderr.encode()),
                'stdout_bytes':len(result.stdout.encode()),'frames':re.findall(r'File "([^"\n]+)", line (\d+), in ([^\n]+)',result.stderr),
                'exception_types':re.findall(r'^([A-Za-z_][A-Za-z_0-9.]*(?:Error|Unavailable|Rejected)):',result.stderr,re.MULTILINE)}
            return result
        phase='fresh_constructor';subprocess.run=measured_run
        try:proof=workflow._probe(profile,source,expected,runtime=runtime)
        finally:subprocess.run=original_run
        receipt['checks'][phase]='PASS'
        receipt['proof']={key:proof.get(key) for key in ('format','provider','fresh_agent_verified','model_turn_executed','active_plugins','native_providers')}
        receipt['proof']['files_match']=proof.get('files')=={name:metadata for name,(_,metadata) in captured.items()}
        phase='stock_identity_after';removal._stock(job,plan);receipt['checks'][phase]='PASS'
except Exception as error:
    receipt.update(failed_phase=phase,error_type=type(error).__name__)
    frames=[];trace=error.__traceback__
    while trace:
        frames.append({'file':Path(trace.tb_frame.f_code.co_filename).name,'function':trace.tb_frame.f_code.co_name,'line':trace.tb_lineno});trace=trace.tb_next
    receipt['frames']=frames
    if phase=='program_targets':
        fingerprint=importlib.import_module(package.__name__+'.release_programs').fingerprint
        receipt['changed_program_targets']=[]
        for entry in publication.programs._load()['entries']:
            actual=fingerprint(entry['target'],allow_links=entry['allow_links'])
            if actual!=entry['after']:
                receipt['changed_program_targets'].append({'target':entry['target'],'expected':entry['after'],'actual':actual})
output=home/'install-input/removal-verification-probe.json'
output.write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt))
