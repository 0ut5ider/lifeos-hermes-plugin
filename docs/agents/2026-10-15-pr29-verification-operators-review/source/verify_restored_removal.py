# ABOUTME: Rechecks a cold restored removal through authenticated native consistency and stock runtime verification.
# ABOUTME: Exports hashes and constructor metadata without exposing memory text or changing ownership.
import hashlib
import importlib
import json
import os
from pathlib import Path
import subprocess
import sys
import types

home=Path('/home/lifeos-hermes');profile=home/'.hermes'
identifier='ab99723289884679b706440c7005fa5c'
if (sys.flags.optimize or os.getuid()!=1000 or Path.home()!=home
        or Path('/etc/hostname').read_text().strip()!='lifeos-portability-restore'):
    raise RuntimeError('Use the owned cold restore guest without optimized Python')
os.umask(0o077)
os.environ.update(HERMES_HOME=str(profile),XDG_RUNTIME_DIR='/run/user/1000',
    DBUS_SESSION_BUS_ADDRESS='unix:path=/run/user/1000/bus')
job=profile/'.lifeos-portability'/identifier
receipt={'status':'FAIL','workflow':identifier,'model_turn_executed':False,
    'raw_record_content_exported':False,'ownership_changed':False,'production_changed':False}
phase='retained_bootstrap'
try:
    result=subprocess.run([str(job/'removal/recover'),'--help'],capture_output=True,timeout=180)
    assert result.returncode==0
    receipt['retained_bootstrap_help_verified']=True
    namespace=types.ModuleType('restored_removal_verification')
    namespace.__path__=[str(job/'removal/recovery-manager')]
    sys.modules[namespace.__name__]=namespace
    state=importlib.import_module(namespace.__name__+'.removal_state')
    source,configuration,selected,plan=state.retained(profile)
    assert selected==job and plan['generation']=='2cac0d6a2cc74063ad49da13cec33395'
    phase='owner_authentication'
    credentials=json.loads((home/'install-input/dashboard-access.json').read_bytes())
    owner=importlib.import_module(namespace.__name__+'.removal_recovery').authenticate(
        profile,credentials['username'],credentials['password'],plan['owner'])
    del credentials
    receipt['owner_authenticated']=True
    workflow=importlib.import_module(namespace.__name__+'.memory_workflow')
    removal=importlib.import_module(namespace.__name__+'.removal_workflow')
    phase='stock_runtime'
    runtime=removal._stock(job,plan)
    receipt['stock_commit']=runtime['stock_source']['commit']
    assert receipt['stock_commit']=='71d34bad1045610252eda02ee79549436896e784'
    before={n:hashlib.sha256((profile/'memories'/n).read_bytes()).hexdigest()
        for n in ('MEMORY.md','USER.md')}
    phase='current_native_and_stock_verification'
    with source.memory_module('installation_lock').installation_lock(profile) as lease:
        publication=importlib.import_module(namespace.__name__+'.removal_publication').RemovalPublication(
            profile,plan['signature'],installation_lease=lease)
        def probe(expected):
            removal._stock(job,plan)
            proof=workflow._probe(profile,source,expected,runtime=runtime)
            removal._stock(job,plan)
            return proof
        result=publication.verify(probe,account=owner)
        assert result['state']=='verified' and result['application_verified'] is True
        proof=result['verification']
        assert proof['fresh_agent_verified'] is True and proof['provider']=='builtin'
        assert proof['model_turn_executed'] is False and not proof['native_providers']
        receipt.update(native_consistency_signature_verified=True,native_signature=plan['native_signature'],
            program_targets_verified=True,stock_runtime_verified=True,fresh_stock_constructor_verified=True)
    after={n:hashlib.sha256((profile/'memories'/n).read_bytes()).hexdigest() for n in before}
    assert before==after
    receipt.update(status='PASS',builtin_files_unchanged=True,builtin_files=after)
except Exception as error:
    receipt.update(failed_phase=phase,error_type=type(error).__name__)
(home/'install-input/pbs-restored-stock-verification.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt))
raise SystemExit(0 if receipt['status']=='PASS' else 1)
