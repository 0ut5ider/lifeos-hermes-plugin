# ABOUTME: Verifies the selected stable programs and retained release journals after a disconnected guest restore.
# ABOUTME: Reports file counts and digests without exporting configuration or memory contents.
import hashlib,json,os,sys
from pathlib import Path
from ruamel.yaml import YAML
from dotenv import dotenv_values
os.environ['PYTHONDONTWRITEBYTECODE']='1'
root=Path('/home/lifeos-hermes/releases/qualification-0.4.2-87205092/source')
sys.path.insert(0,str(root))
from optional.lifeos_release_manager.release_programs import fingerprint
from optional.lifeos_release_manager.release_operation import validate_plan
profile=Path.home()/'.hermes';job=profile/'.lifeos-releases'/sys.argv[1]
request=json.loads((job/'request.json').read_bytes())
assert json.loads((job/'status.json').read_bytes())['state']=='applied'
assert request['version']=='0.4.2' and request['commit']=='87205092832c550a09fce6e1cb3ca944fdb69a8c'
programs=json.loads((job/'program-snapshot/programs.json').read_bytes());assert programs['state']=='applied'
plan=validate_plan(job,request)
mount=json.loads((profile/'.lifeos-mount/operation.json').read_bytes());assert mount['state']=='committed'
overrides={row['target']:{'type':'file','mode':row['after']['mode'],'sha256':row['after']['digest']} for row in mount['entries']} if plan['native_mount_required'] else {}
program_targets={row['target'] for row in programs['entries']}
count=0
configuration_checked=False
live='--live' in sys.argv[2:]
for row in programs['entries']:
 path=Path(row['target'])
 if path.parent==Path.home()/'.config/systemd/user':
  if not live:
   assert path.is_symlink() and path.readlink()==Path('/dev/null')
   path=path.with_name(path.name+'.before-restore')
 expected=overrides.get(row['target'],row['after'])
 if path==profile/'config.yaml':
  source=Path(row['source'])
  assert fingerprint(source,allow_links=False)==row['after']
  before=YAML(typ='safe').load(source.read_bytes())
  current=YAML(typ='safe').load(path.read_bytes())
  assert current==dict(before,memory={'provider':'lifeos-hook-bridge','memory_enabled':False,'user_profile_enabled':False})
  assert fingerprint(path,allow_links=False)=={'type':'file','mode':0o600,'sha256':'03277a0723bc4e23fd5c3c942e1e00d1570396ace660deb0346ac06ce12f1908'}
  configuration_checked=True
 else:
  assert fingerprint(path,allow_links=row['allow_links'])==expected,row['target']
 count+=1
for row in mount['entries']:
 if not plan['native_mount_required'] and row['target'] in program_targets:
  continue
 if Path(row['target'])==profile/'.env':
  stage=Path.home()/'releases/qualification-0.4.2-87205092'
  before=dict(dotenv_values(stage/'environment-before-private-development.env'))
  current=dict(dotenv_values(profile/'.env'))
  expected=dict(before)
  for key in ('DISCORD_ALLOWED_CHANNELS','DISCORD_FREE_RESPONSE_CHANNELS','DISCORD_HOME_CHANNEL'):
   expected[key]='1559717651817697361'
  assert current==expected
  assert fingerprint(profile/'.env',allow_links=False)=={'type':'file','mode':0o600,'sha256':'2322e1f8f7245572b14e9e4d1dbe637f1b113ca79e1d0056274e71b420dc4beb'}
  continue
 path=Path(row['target']);assert hashlib.sha256(path.read_bytes()).hexdigest()==row['after']['digest'],row['target']
receipt=json.loads((profile/'integration-release.json').read_bytes())
assert all(receipt[key]==request[key] for key in ('version','commit','package_sha256'))
assert configuration_checked
print(json.dumps({'status':'PASS','operation':job.name,'version':request['version'],'program_commit':request['commit'],'archive_sha256':request['package_sha256'],'program_targets':count,'native_mount_targets':len(mount['entries']),'owner_memory_configuration_verified':True,'network_disconnected':not live,'application_services_masked':not live},indent=2))
