# ABOUTME: Builds a public-only deployed baseline inventory from the immutable qualified archive.
# ABOUTME: Authenticates source index bytes and frozen dependency locks without consulting a daily baseline.
import hashlib,importlib.util,json,subprocess,tarfile
from pathlib import Path

cache=Path('/home/outsider/.cache/lifeos-release-0.5.0-20261014')
archive=cache/'packages/0.5.0-04efe633.tgz';package=cache/'packages/0.5.0-04efe633'
digest='a6dd0e11b8fb1b5ae30345be20c955db02728839f7bc907f60a70944ad392813'
assert hashlib.sha256(archive.read_bytes()).hexdigest()==digest
source=package/'lifeos/LifeOS/install';base='5e2f2e8c0abde612da0e99c16c0d07d4ec21b88c'
assert subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip()==base
spec=importlib.util.spec_from_file_location('qualified_public_drift',package/'lifeos_hook_bridge/version_drift.py')
drift=importlib.util.module_from_spec(spec);spec.loader.exec_module(drift)
with tarfile.open(archive) as stream:
 def content(name):
  member=stream.getmember(name);assert member.isfile()
  return stream.extractfile(member).read()
 for name in ('index','HEAD','config'):
  assert (package/'lifeos/.git'/name).read_bytes()==content('lifeos/.git/'+name)
 tracked=set(drift._tracked_source_files(source,*drift.CORE_PATHS))|set(drift.PLUGIN_SOURCE_FILES)
 prefix='lifeos/LifeOS/install/'
 regular={member.name for member in stream.getmembers() if member.isfile()}
 selected=sorted(name for name in tracked if drift._eligible(name)
  and not name.startswith(drift.RUNTIME_PATHS) and name not in drift.GENERATED_FILES
  and name.startswith(('LIFEOS/','skills/','hooks/')) and prefix+name in regular)
 files={name:hashlib.sha256(content(prefix+name)).hexdigest() for name in selected}
 assert len(files)==1742
 locks=json.loads(content('lifeos_hook_bridge/dependency_locks/catalog.json'))
 assert locks['bun_version']=='1.4.3' and locks['lifeos_commit']==base and len(locks['packages'])==12
 replaced=[]
 for root,row in locks['packages'].items():
  lock=content('lifeos_hook_bridge/dependency_locks/'+row['lock_file'])
  assert hashlib.sha256(lock).hexdigest()==row['lock_sha256']
  name=root+'/bun.lock'
  if name in files:
   assert hashlib.sha256(content(prefix+root+'/package.json')).hexdigest()==row['package_sha256']
   files[name]=row['lock_sha256'];replaced.append(name)
 assert len(replaced)==5
 native_version=content(prefix+'LIFEOS/VERSION').decode().strip();assert native_version=='7.40.4'
 result={'format':1,'archive_sha256':digest,'source_commit':base,'native_version':native_version,
  'inventory_scope':'Archive tracked CORE_PATHS deployed by DeployCore and InstallHooks, plus fixed plugin sources.',
  'frozen_lock_overrides':sorted(replaced),'files':dict(sorted(files.items()))}
destination=Path(__file__).with_name('daily-baseline-public-programs.json');assert not destination.exists()
destination.write_text(json.dumps(result,sort_keys=True,indent=2)+'\n')
print(json.dumps({'status':'PASS','public_programs':len(files),'frozen_locks':len(replaced),
 'catalog_sha256':hashlib.sha256(destination.read_bytes()).hexdigest(),'live_baseline_used':False},indent=2))
