# ABOUTME: Captures and verifies the daily runtime after a later authenticated owner remount.
# ABOUTME: Checks actual selected targets and current mount digests without enabling the earlier release restore.
import argparse,hashlib,importlib,json,os,subprocess,sys,tomllib,types
from pathlib import Path
from ruamel.yaml import YAML
from prove_daily_baseline import baseline_override

parser=argparse.ArgumentParser();parser.add_argument('action',choices=('capture','verify'));parser.add_argument('operation')
args=parser.parse_args();identifier=args.operation
assert len(identifier)==32 and set(identifier)<=set('0123456789abcdef')
home=Path('/home/lifeos-hermes');profile=home/'.hermes';stage=home/'releases/qualification-0.5.0'
os.environ.update(HOME=str(home),HERMES_HOME=str(profile),PYTHONDONTWRITEBYTECODE='1',
 PATH=str(home/'.local/bin')+':'+str(Path(sys.executable).parent)+':/usr/bin:/bin')
namespace=types.ModuleType('daily_checkpoint_manager');namespace.__path__=[str(profile/'plugins/lifeos-release-manager')]
sys.modules[namespace.__name__]=namespace
cli=importlib.import_module(namespace.__name__+'.cli');worker=importlib.import_module(namespace.__name__+'.release_worker')
job,request=cli.operation(profile,identifier)
assert request['version']=='0.5.0' and request['commit']=='04efe633296eb2b1a1d95561ca6d3e9516cd47dc'
assert request['package_sha256']=='a6dd0e11b8fb1b5ae30345be20c955db02728839f7bc907f60a70944ad392813'
assert cli.read_private(job/'status.json')['state']=='applied'
assert hashlib.sha256((job/'download/0.5.0-04efe633.tgz').read_bytes()).hexdigest()==request['package_sha256']
assert hashlib.sha256((job/'download/RELEASE-CERTIFICATE.json').read_bytes()).hexdigest()=='c8a0ac35fa6f084d417951fd7538bee8f9d330ff101a9f71e3855b5da8a2dd20'
assert json.loads((job/'download/RELEASE-CERTIFICATE.json').read_bytes())==request['certificate']
plan=importlib.import_module(namespace.__name__+'.release_operation').validate_plan(job,request)
assert not plan['fresh'] and plan['native_mount_required'] is True
current=worker.recovery_bridge(job,profile)
baseline_path=current.memory_module('version_drift').default_baseline_path(Path(request['installed']).parent)
mount=current.memory_module('mount_transaction').MountTransaction(Path(request['installed']),profile,baseline_path)
mount.check_completed()
manifest=mount._manifest();assert manifest['state']=='committed'
expected_mount_targets={str(profile/name) for name in current.memory_module('mount_transaction').FILES}
assert len(manifest['entries'])==7 and {entry['target'] for entry in manifest['entries']}==expected_mount_targets
assert manifest['binding'] is None and manifest['retain_for_rollback'] is False
assert worker.restore_available(job,request,plan) is False
journal_digest=hashlib.sha256(mount.journal.read_bytes()).hexdigest()
overrides={entry['target']:{'type':'file','mode':entry['after']['mode'],'sha256':entry['after']['digest']} for entry in manifest['entries']}
transaction=importlib.import_module(namespace.__name__+'.release_programs').ProgramTransaction(
 job/'program-snapshot',expected_entries_sha256=plan['program_entries_sha256'])
baseline_target,baseline_expected=baseline_override(job,request,transaction,overrides)
overrides[baseline_target]=baseline_expected
transaction.check_applied(overrides=overrides)
before=json.loads((stage/'daily-prepromotion-baseline.json').read_bytes())
assert before['status']=='PASS' and before['server']=='daily'
assert set(before['configuration_file_sha256'])=={'.env','lifeos-memory.json'}
for name,digest in before['configuration_file_sha256'].items():
 assert hashlib.sha256((profile/name).read_bytes()).hexdigest()==digest
config=YAML(typ='safe').load((profile/'config.yaml').read_bytes())
settings=config['plugins']['entries']['lifeos-hook-bridge']['settings']
selection={'model':config['model'],'tiers':{k:v for k,v in settings.items() if k.startswith(('haiku','sonnet','opus','fable','pinned'))}}
assert hashlib.sha256(json.dumps(selection,sort_keys=True).encode()).hexdigest()==before['model_selection_sha256']
root=Path(json.loads((profile/'lifeos-memory.json').read_bytes())['root'])
user=root/'LIFEOS/USER/CONFIG/PULSE.user.toml';user_digest=hashlib.sha256(user.read_bytes()).hexdigest()
activation=json.loads((stage/'daily-editor-activation.json').read_bytes())
assert activation['status']=='PASS' and activation['operation']==identifier
assert activation['only_modules_hermes_changed'] is True and user_digest==activation['user_configuration_after_sha256']
parsed=tomllib.loads(user.read_text());assert parsed['modules']['hermes'] is True
morning=[row for row in parsed['job'] if row['name']=='life-morning-brief']
assert len(morning)==1 and morning[0]['schedule']=='0 7 * * *' and morning[0]['enabled'] is True
units=home/'.config/systemd/user';unit_digests={}
for name in ('hermes-dashboard.service','hermes-gateway.service','com.lifeos.pulse.service'):
 path=units/name
 if args.action=='verify':
  assert path.is_symlink() and os.readlink(path)=='/dev/null'
  path=units/(name+'.before-restore')
 assert path.is_file() and not path.is_symlink()
 unit_digests[name]=hashlib.sha256(path.read_bytes()).hexdigest()
checkpoint={'operation':identifier,'program_commit':request['commit'],'archive_sha256':request['package_sha256'],
 'generated_baseline_sha256':baseline_expected['sha256'],
 'current_owner_mount_journal_sha256':journal_digest,'profile_configuration_sha256':hashlib.sha256((profile/'config.yaml').read_bytes()).hexdigest(),
 'pulse_user_configuration_sha256':user_digest,'service_unit_sha256':unit_digests}
path=stage/'daily-current-mount-checkpoint.json'
if args.action=='capture':
 assert not path.exists();path.write_text(json.dumps(checkpoint,indent=2)+'\n');path.chmod(0o600)
else:assert json.loads(path.read_bytes())==checkpoint,'The restored current mount or configuration differs from the daily checkpoint'
mount.check_completed();assert hashlib.sha256(mount.journal.read_bytes()).hexdigest()==journal_digest
active=json.loads(subprocess.run([str(home/'.local/bin/hermes'),'lifeos-version'],capture_output=True,text=True,check=True,timeout=90).stdout)['active']
assert active['verification']=='verified' and all(active[k]==request[k] for k in ('version','commit','package_sha256'))
print(json.dumps({'status':'PASS','action':args.action,'operation':identifier,'version':request['version'],
 'program_commit':request['commit'],'archive_sha256':request['package_sha256'],'program_targets':len(transaction._load()['entries']),
 'native_mount_required':True,'native_mount_targets':len(manifest['entries']),'current_owner_mount_verified':True,
 'current_mount_checkpoint_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
 'prior_release_restore_available':False,'owner_memory_configuration_verified':True,'credential_file_bytes_preserved':True,
 'model_and_tiers_preserved':True,'pulse_editor_enabled':True,'normal_morning_schedule':'0 7 * * *',
 'retained_public_archive_and_certificate_verified':True,
 'generated_baseline_public_programs_verified':1742,
 'generated_baseline_timestamp_scope':'Strict integer bounded by public publication and original apply intent metadata. Exact historical timestamp preservation is not claimed.',
 'application_services_masked':args.action=='verify','personal_records_read':False,'personal_data_imported_or_reset':False,
 'scope':'Current owner mount, selected program targets, and machine configuration. The earlier release journal is not rebound.'},indent=2))
