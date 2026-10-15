# ABOUTME: Verifies the actual default-URL stock installation against the immutable public 0.5.0 assets.
# ABOUTME: Checks sealed programs, preserved model settings, and inactive optional writers without reading personal records.
import hashlib,importlib,json,os,subprocess,sys,types
from pathlib import Path
from ruamel.yaml import YAML

def validate_stock_provenance(baseline,provenance):
 expected={'guest':113,'address':'192.168.8.244',
  'hermes_commit':'71d34bad1045610252eda02ee79549436896e784','hermes_patches':0,
  'stock_source_sha256':'e8acf0dfc6329d85b75c5625412c463798d1cd3ae6507aaf88b717dc74e2c6fc',
  'release_manager_installed':False,'lifeos_installed':False,'production_guest_changed':False}
 assert baseline['status']=='STOCK_DASHBOARD_STARTED'
 assert provenance['status']=='PASS'
 for key,value in expected.items():
  assert type(baseline[key]) is type(value) and baseline[key]==value,key
  assert type(provenance[key]) is type(value) and provenance[key]==value,key
 for key,value in {'source_files_verified':18243,'source_links_verified':0,
  'dashboard_sha256':'e7c93e754de99b6ec66ae17ae313377dc513104da2776a099c391a7aab347bec',
  'dashboard_files_verified':66,'runtime_files_verified':18309,
  'complete_runtime_file_set_verified':True,'public_installation_verified':False}.items():
  assert type(provenance[key]) is type(value) and provenance[key]==value,key

home=Path('/home/lifeos-hermes');profile=home/'.hermes';stage=home/'releases/qualification-0.5.0'
identifier='568cd8927be849e7a92f0d048999d070'
os.environ.update(HOME=str(home),HERMES_HOME=str(profile),XDG_RUNTIME_DIR='/run/user/1000',
 DBUS_SESSION_BUS_ADDRESS='unix:path=/run/user/1000/bus',PATH=str(home/'.local/bin')+':/usr/bin:/bin')
namespace=types.ModuleType('public_installation_manager');namespace.__path__=[str(profile/'plugins/lifeos-release-manager')]
sys.modules[namespace.__name__]=namespace
cli=importlib.import_module(namespace.__name__+'.cli')
worker=importlib.import_module(namespace.__name__+'.release_worker')
job,request=cli.operation(profile,identifier)
assert cli.read_private(job/'status.json')['state']=='applied'
assert request['version']=='0.5.0' and request['commit']=='04efe633296eb2b1a1d95561ca6d3e9516cd47dc'
assert request['package_sha256']=='a6dd0e11b8fb1b5ae30345be20c955db02728839f7bc907f60a70944ad392813'
certificate=job/'download/RELEASE-CERTIFICATE.json'
assert hashlib.sha256(certificate.read_bytes()).hexdigest()=='c8a0ac35fa6f084d417951fd7538bee8f9d330ff101a9f71e3855b5da8a2dd20'
assert request['certificate']==json.loads(certificate.read_bytes())
assert request['certificate']['production_qualified'] is True
assert request['certificate'].get('test_fixture_only',False) is False
assert hashlib.sha256((job/'download/0.5.0-04efe633.tgz').read_bytes()).hexdigest()==request['package_sha256']
plan=importlib.import_module(namespace.__name__+'.release_operation').validate_plan(job,request)
assert plan['fresh'] is True and plan['native_mount_required'] is True
current=worker.recovery_bridge(job,profile)
baseline_path=current.memory_module('version_drift').default_baseline_path(Path(request['installed']).parent)
mount=current.memory_module('mount_transaction').MountTransaction(Path(request['installed']),profile,baseline_path)
worker.check_restore(job,request,plan,mount)
transaction=importlib.import_module(namespace.__name__+'.release_programs').ProgramTransaction(
 job/'program-snapshot',expected_entries_sha256=plan['program_entries_sha256'])
active=json.loads(subprocess.run([str(home/'.local/bin/hermes'),'lifeos-version'],capture_output=True,text=True,check=True,timeout=90).stdout)['active']
assert active['verification']=='verified' and all(active[k]==request[k] for k in ('version','commit','package_sha256'))
baseline=json.loads((stage/'stock-baseline.json').read_bytes())
provenance=json.loads((stage/'public-stock-source-verification.json').read_bytes())
validate_stock_provenance(baseline,provenance)
config=YAML(typ='safe').load((profile/'config.yaml').read_bytes())
settings=config['plugins']['entries']['lifeos-hook-bridge']['settings']
selection={'model':config['model'],'tiers':{key:value for key,value in settings.items()
 if key.startswith(('haiku','sonnet','opus','fable','pinned'))}}
assert hashlib.sha256(json.dumps(selection,sort_keys=True).encode()).hexdigest()==baseline['model_selection_sha256']
services={}
for name in ('hermes-dashboard.service','hermes-gateway.service','com.lifeos.pulse.service'):
 result=subprocess.run(['systemctl','--user','show',name,'--property=ActiveState,SubState','--no-pager'],capture_output=True,text=True,check=True)
 services[name]=dict(line.split('=',1) for line in result.stdout.splitlines() if '=' in line)
assert services['hermes-dashboard.service']=={'ActiveState':'active','SubState':'running'}
assert all(services[name]=={'ActiveState':'inactive','SubState':'dead'} for name in ('hermes-gateway.service','com.lifeos.pulse.service'))
report={'status':'PASS','guest':113,'address':'192.168.8.244','operation':identifier,'active_identity':active,
 'public_certificate_sha256':'c8a0ac35fa6f084d417951fd7538bee8f9d330ff101a9f71e3855b5da8a2dd20',
 'sealed_program_targets':len(transaction._load()['entries']),'native_mount_required':True,
 'prior_stock_source_verified':True,
 'prior_stock_source_receipt_sha256':hashlib.sha256((stage/'public-stock-source-verification.json').read_bytes()).hexdigest(),
 'fresh_installation':True,'selected_model_and_tiers_preserved':True,
 'services':services,'public_catalog_certificate_verified':True,'personal_records_read':False,
 'personal_data_imported_or_reset':False,'production_guest_changed':False,
 'scope':'Actual public native UI installation and exact selected programs. New owner memory activation is a separate setup step.'}
(stage/'public-installation-verification.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
