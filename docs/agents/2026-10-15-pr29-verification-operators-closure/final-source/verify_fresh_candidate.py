# ABOUTME: Verifies a fresh installed candidate against actual program maps and preserved model choices.
# ABOUTME: Keeps model output private and distinguishes private qualification from public catalog acceptance.
import argparse
import hashlib
import importlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import types

from ruamel.yaml import YAML

parser=argparse.ArgumentParser()
parser.add_argument('identifier')
parser.add_argument('--kind',choices=('private','public'),required=True)
args=parser.parse_args()
if sys.flags.optimize:
    raise RuntimeError('Qualification requires Python assertions')
home=Path('/home/lifeos-hermes');profile=home/'.hermes'
if os.getuid()!=1000 or Path.home()!=home or re.fullmatch('[0-9a-f]{32}',args.identifier) is None:
    raise RuntimeError('Use the fresh disposable owner and exact operation identifier')
os.umask(0o077)
os.environ.update(HERMES_HOME=str(profile),XDG_RUNTIME_DIR='/run/user/1000',
    DBUS_SESSION_BUS_ADDRESS='unix:path=/run/user/1000/bus')
sys.path.insert(0,str(profile/'.lifeos-releases'/args.identifier/'hermes'))
output=home/'install-input'/('fresh-'+args.kind+'-verification')
output.mkdir(mode=0o700)
receipt={'status':'FAIL','guest':112,'address':'192.168.8.248','operation':args.identifier,
    'kind':args.kind,'production_guest_changed':False,'personal_records_read':False,
    'personal_data_imported_or_reset':False}
started=time.monotonic();phase='installed_identity'
try:
    namespace=types.ModuleType('fresh_candidate_verification')
    namespace.__path__=[str(profile/'plugins/lifeos-release-manager')]
    sys.modules[namespace.__name__]=namespace
    cli=importlib.import_module(namespace.__name__+'.cli')
    worker=importlib.import_module(namespace.__name__+'.release_worker')
    job,request=cli.operation(profile,args.identifier)
    assert cli.read_private(job/'status.json')['state']=='applied'
    assert request['version']=='0.6.0' and request['commit']=='c86b5887b899ca779afbb217c33843e1ee12c381'
    assert request['package_sha256']=='9e2a1939efbaccc94abaa879b265f1af447f9bdfe0b82aecc76f872f15fa9fb7'
    certificate=request['certificate']
    if args.kind=='private':
        assert certificate['production_qualified'] is False and certificate['test_fixture_only'] is True
    else:
        assert certificate['production_qualified'] is True and certificate.get('test_fixture_only',False) is False
        assert json.loads((job/'download/RELEASE-CERTIFICATE.json').read_bytes())==certificate
    result=subprocess.run([str(home/'.local/bin/hermes'),'lifeos-version'],capture_output=True,text=True,check=True,timeout=90)
    active=json.loads(result.stdout)['active']
    assert active['verification']=='verified' and not active['modified_files']
    assert all(active[key]==request[key] for key in ('version','commit','package_sha256'))
    receipt['active_identity']=active
    phase='sealed_programs'
    plan=importlib.import_module(namespace.__name__+'.release_operation').validate_plan(job,request)
    assert plan['fresh'] is True and plan['native_mount_required'] is True
    current=worker.recovery_bridge(job,profile)
    baseline=current.memory_module('version_drift').default_baseline_path(Path(request['installed']).parent)
    mount=current.memory_module('mount_transaction').MountTransaction(Path(request['installed']),profile,baseline)
    worker.check_restore(job,request,plan,mount)
    transaction=importlib.import_module(namespace.__name__+'.release_programs').ProgramTransaction(
        job/'program-snapshot',expected_entries_sha256=plan['program_entries_sha256'])
    receipt.update(sealed_program_targets=len(transaction._load()['entries']),fresh_installation=True,
        native_mount_required=True)
    phase='selected_configuration'
    config=YAML(typ='safe').load((profile/'config.yaml').read_bytes())
    settings=config['plugins']['entries']['lifeos-hook-bridge']['settings']
    selected={'model':config['model'],'tiers':{key:settings[key] for tier in ('haiku','sonnet','opus','fable')
        for key in (tier+'_model',tier+'_effort')}}
    digest=hashlib.sha256(json.dumps(selected,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    before=json.loads((home/'install-input/fresh-before-application.json').read_bytes())
    assert before['native_store_present'] is False and before['policy_present'] is False
    assert digest==before['model_mapping_sha256']
    receipt.update(selected_model_and_tiers_preserved=True,model_mapping_sha256=digest)
    services={}
    for unit in ('hermes-dashboard.service','hermes-gateway.service','com.lifeos.pulse.service'):
        result=subprocess.run(['systemctl','--user','show',unit,'--property=ActiveState,SubState'],
            capture_output=True,text=True,check=True,timeout=30)
        services[unit]=dict(line.split('=',1) for line in result.stdout.splitlines() if '=' in line)
    assert services['hermes-dashboard.service']=={'ActiveState':'active','SubState':'running'}
    assert all(services[unit]=={'ActiveState':'inactive','SubState':'dead'}
        for unit in ('hermes-gateway.service','com.lifeos.pulse.service'))
    receipt['services']=services
    phase='fresh_model_round_trip'
    query=output/'query.txt'
    query.write_text('Reply exactly D248-FRESH-060-PASS. Do not call any tool.\n')
    with (output/'stdout.jsonl').open('wb') as stdout,(output/'stderr.txt').open('wb') as stderr:
        result=subprocess.run([str(home/'.local/bin/hermes'),'chat','--query-file',str(query),
            '--oneshot','--format','stream-json','--max-turns','3','--run-budget','120'],
            cwd=profile,stdout=stdout,stderr=stderr,timeout=180)
    events=[]
    for line in (output/'stdout.jsonl').read_text().splitlines():
        try:event=json.loads(line)
        except ValueError:continue
        if isinstance(event,dict):events.append(event)
    final=next((event for event in reversed(events) if event.get('type')=='result'),{})
    names=[event.get('name') for event in events if event.get('type')=='tool_use']
    actual=(result.returncode==0 and final.get('exit_code')==0 and not names
        and final.get('tokens',{}).get('output',0)>0 and 'D248-FRESH-060-PASS' in final.get('text',''))
    receipt.update(model_turn_executed=final.get('tokens',{}).get('output',0)>0,
        actual_model_round_trip=actual,model_session=final.get('session_id'),tool_names=names,
        public_catalog_certificate_verified=args.kind=='public')
    assert actual
    receipt['status']='PASS'
except Exception as error:
    receipt.update(failed_phase=phase,error_type=type(error).__name__)
finally:
    receipt['elapsed_seconds']=time.monotonic()-started
    (output/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    (output/'verification.done').write_text('0\n' if receipt['status']=='PASS' else '1\n')
print(json.dumps(receipt))
raise SystemExit(0 if receipt['status']=='PASS' else 1)
