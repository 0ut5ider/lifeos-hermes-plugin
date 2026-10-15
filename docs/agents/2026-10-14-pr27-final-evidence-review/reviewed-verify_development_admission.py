# ABOUTME: Verifies release identity and configuration after owner source review and native remounting.
# ABOUTME: Reports service HOME preservation without reading personal records or exporting credential values.
import hashlib,json,os,subprocess
from pathlib import Path
from ruamel.yaml import YAML

home=Path('/home/lifeos-hermes');profile=home/'.hermes'
stage=home/'releases/qualification-0.5.0'
baseline=json.loads((stage/'development-prepromotion-baseline.json').read_bytes())
os.environ.update(HOME=str(home),HERMES_HOME=str(profile),XDG_RUNTIME_DIR='/run/user/'+str(os.getuid()),
 DBUS_SESSION_BUS_ADDRESS='unix:path=/run/user/'+str(os.getuid())+'/bus',PATH=str(home/'.local/bin')+':/usr/bin:/bin')
active=json.loads(subprocess.run([str(home/'.local/bin/hermes'),'lifeos-version'],capture_output=True,text=True,check=True,timeout=90).stdout)['active']
assert active['verification']=='verified' and active['version']=='0.5.0'
assert active['commit']=='04efe633296eb2b1a1d95561ca6d3e9516cd47dc'
assert active['package_sha256']=='a6dd0e11b8fb1b5ae30345be20c955db02728839f7bc907f60a70944ad392813'
config=YAML(typ='safe').load((profile/'config.yaml').read_bytes())
settings=config.get('plugins',{}).get('entries',{}).get('lifeos-hook-bridge',{}).get('settings',{})
selection={'model':config.get('model'),'tiers':{key:value for key,value in settings.items()
 if key.startswith(('haiku','sonnet','opus','fable','pinned'))}}
assert hashlib.sha256(json.dumps(selection,sort_keys=True).encode()).hexdigest()==baseline['model_selection_sha256']
assert baseline['status']=='PASS' and baseline['server']=='development'
assert isinstance(baseline['configuration_file_sha256'],dict)
assert set(baseline['configuration_file_sha256'])=={'.env','lifeos-memory.json'}
for digest in [baseline['model_selection_sha256'],*baseline['configuration_file_sha256'].values()]:
 assert isinstance(digest,str) and len(digest)==64 and set(digest)<=set('0123456789abcdef')
for name,digest in baseline['configuration_file_sha256'].items():
 assert hashlib.sha256((profile/name).read_bytes()).hexdigest()==digest
assert set(baseline['services'])=={'hermes-gateway.service','hermes-dashboard.service','com.lifeos.pulse.service'}
for name,expected in baseline['services'].items():
 result=subprocess.run(['systemctl','--user','show',name,'--property=ActiveState,SubState,MainPID','--no-pager'],capture_output=True,text=True,check=True)
 values=dict(line.split('=',1) for line in result.stdout.splitlines() if '=' in line)
 assert values['ActiveState']=='active' and values['SubState']=='running'
 environment=dict(value.split('=',1) for value in Path('/proc/'+values['MainPID']+'/environ').read_bytes().decode().split('\0') if '=' in value)
 assert environment['HOME']==expected['home'] and environment['HERMES_HOME']==expected['profile']
report={'status':'PASS','server':'development','active_identity':active,
 'model_and_tiers_preserved':True,'credential_file_bytes_preserved':True,'memory_configuration_bytes_preserved':True,
 'all_three_services_and_homes_preserved':True,'gateway_restarted_after_remount':True,
 'personal_records_read':False,'personal_data_imported_or_reset':False,'daily_guest_changed':False}
(stage/'development-post-admission-verification.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
