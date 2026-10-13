# ABOUTME: Records safe installation identities and actual user-service state on the synthetic test guest.
# ABOUTME: Compares model settings privately and never exports configuration values or user records.
import json,os,subprocess,sys,hashlib
from pathlib import Path
from ruamel.yaml import YAML
sys.dont_write_bytecode=True
home=Path.home();profile=home/'.hermes';identifier=sys.argv[1]
assert len(identifier)==32 and all(c in '0123456789abcdef' for c in identifier)
job=profile/'.lifeos-releases'/identifier
state=json.loads((job/'status.json').read_bytes())
certificate=json.loads((job/'request.json').read_bytes())['certificate']
report={'operation':state,'memory_ownership_configuration_present':(profile/'lifeos-memory.json').exists(),'native_present':(home/'.claude').is_dir(),'test_fixture_only':certificate.get('test_fixture_only',False),'production_qualified':certificate.get('production_qualified',False)}
receipt=profile/'integration-release.json'
if receipt.is_file():
 value=json.loads(receipt.read_bytes());report['active_release']={k:value[k] for k in ('version','commit','package_sha256')}
programs=job/'program-snapshot/programs.json'
if programs.is_file():
 value=json.loads(programs.read_bytes());report['program_state']=value['state'];report['program_targets']=len(value['entries'])
 for index,entry in enumerate(value['entries']):
  if entry['target']==str(profile/'config.yaml') and entry['before'] is not None:
   before=YAML(typ='safe').load((job/'program-snapshot'/('before-'+str(index))).read_bytes());after=YAML(typ='safe').load((profile/'config.yaml').read_bytes())
   report['model_configuration_preserved']=before.get('model')==after.get('model')
   report['prior_tier_settings_preserved']=all(after.get('plugins',{}).get('entries',{}).get('lifeos-hook-bridge',{}).get('settings',{}).get(k)==v for k,v in before.get('plugins',{}).get('entries',{}).get('lifeos-hook-bridge',{}).get('settings',{}).items() if k.endswith('_model') or k.endswith('_effort'))
services={}
for name in ('hermes-gateway.service','hermes-dashboard.service','com.lifeos.pulse.service','lifeos-release-'+identifier+'.service'):
 result=subprocess.run(['systemctl','--user','show',name,'--property=Id,LoadState,ActiveState,MainPID,ControlGroup,WorkingDirectory,UnitFileState,ExecMainStartTimestamp,ExecMainStatus','--no-pager'],capture_output=True,text=True,check=True)
 assert not result.stderr
 services[name]=dict(line.split('=',1) for line in result.stdout.splitlines() if '=' in line)
report['services']=services
journal=profile/'.lifeos-installation-services/operation.json'
if journal.is_file():report['first_service_journal']=json.loads(journal.read_bytes())
failure=job/'worker-failure.json'
if failure.is_file():report['failure']=json.loads(failure.read_bytes())
marker=home/'.config/LIFEOS/USER/pr18-stage-recovery-synthetic.txt'
report['later_synthetic_preserved']=marker.is_file() and hashlib.sha256(marker.read_bytes()).hexdigest()=='9d2fc12f89c841009aa7d73556d0ac92648435de7d39244a590eafb15ec0a203'
report['later_synthetic_mode']=oct(marker.stat().st_mode & 0o777) if marker.is_file() else None
print(json.dumps(report,indent=2))
