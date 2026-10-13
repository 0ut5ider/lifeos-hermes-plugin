# ABOUTME: Verifies the selected stable programs and retained release journals after a disconnected guest restore.
# ABOUTME: Reports file counts and digests without exporting configuration or memory contents.
import hashlib,json,os,sys
from pathlib import Path
os.environ['PYTHONDONTWRITEBYTECODE']='1'
root=Path('/home/lifeos-hermes/releases/qualification-20261013-041-96f4f8fb/source')
sys.path.insert(0,str(root))
from optional.lifeos_release_manager.release_programs import fingerprint
profile=Path.home()/'.hermes';job=profile/'.lifeos-releases'/sys.argv[1]
request=json.loads((job/'request.json').read_bytes())
assert json.loads((job/'status.json').read_bytes())['state']=='applied'
assert request['version']=='0.4.1' and request['commit']=='96f4f8fbef21f53ee704eb16f34698bc35b5dc77'
programs=json.loads((job/'program-snapshot/programs.json').read_bytes());assert programs['state']=='applied'
mount=json.loads((profile/'.lifeos-mount/operation.json').read_bytes());assert mount['state']=='committed'
overrides={row['target']:{'type':'file','mode':row['after']['mode'],'sha256':row['after']['digest']} for row in mount['entries']}
count=0
for row in programs['entries']:
 path=Path(row['target'])
 if path.parent==Path.home()/'.config/systemd/user':
  path=path.with_name(path.name+'.before-restore')
 assert fingerprint(path,allow_links=row['allow_links'])==overrides.get(row['target'],row['after']),row['target']
 count+=1
for row in mount['entries']:
 path=Path(row['target']);assert hashlib.sha256(path.read_bytes()).hexdigest()==row['after']['digest']
receipt=json.loads((profile/'integration-release.json').read_bytes())
assert all(receipt[key]==request[key] for key in ('version','commit','package_sha256'))
print(json.dumps({'status':'PASS','operation':job.name,'version':request['version'],'program_commit':request['commit'],'archive_sha256':request['package_sha256'],'program_targets':count,'native_mount_targets':len(mount['entries']),'network_disconnected':True,'application_services_masked':True},indent=2))
