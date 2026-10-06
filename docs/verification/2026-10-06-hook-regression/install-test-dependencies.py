# ABOUTME: Prepares every native package tree through the actual frozen release installer.
# ABOUTME: Verifies package manifests, locks, installed direct dependencies, and Bun version.
from pathlib import Path
import hashlib,json,os,shutil,subprocess,sys
cache=Path('/home/outsider/.cache/lifeos-hook-completion-20261006')
repo=Path('/home/outsider/Projects/Hermes_agent/LifeOS_plugin')
sys.path.insert(0,str(repo))
from lifeos_hook_bridge.native_dependencies import validate_release_dependencies
from lifeos_hook_bridge.install_source import SUPPORTED_LIFEOS_COMMIT
source=cache/'prepared-final/lifeos/LifeOS/install'
catalog=repo/'lifeos_hook_bridge/dependency_locks'
value=validate_release_dependencies(source,catalog,SUPPORTED_LIFEOS_COMMIT)
bun=shutil.which('bun')
assert subprocess.check_output([bun,'--version'],text=True).strip()==value['bun_version']
root=cache/'complete-native-dependencies';root.mkdir(mode=0o700)
rows=[]
try:
 for name,item in value['packages'].items():
  package=root/name;package.mkdir(parents=True,exist_ok=True,mode=0o700)
  (package/'package.json').write_bytes((source/name/'package.json').read_bytes())
  (package/'bun.lock').write_bytes((catalog/item['lock_file']).read_bytes())
  command=[sys.executable,'-I',str(repo/'lifeos_hook_bridge/native_dependencies.py'),'--executable',bun,'--root',str(root),'--catalog',str(catalog),'--','install']
  result=subprocess.run(command,cwd=package,text=True,capture_output=True,timeout=300)
  record={'name':name,'command':command,'exit_code':result.returncode,'stdout':result.stdout,'stderr':result.stderr}
  rows.append(record)
  if result.returncode:raise RuntimeError('Frozen install fails for '+name)
  assert hashlib.sha256((package/'bun.lock').read_bytes()).hexdigest()==item['lock_sha256']
  manifest=json.loads((package/'package.json').read_text())
  dependencies={**manifest.get('dependencies',{}),**manifest.get('devDependencies',{})}
  record['direct_dependencies']={key:json.loads((package/'node_modules'/key/'package.json').read_text())['version'] for key in dependencies}
  record['package_sha256']=hashlib.sha256((package/'package.json').read_bytes()).hexdigest()
  record['lock_sha256']=item['lock_sha256']
 for name in value['packages']:
  target=source/name/'node_modules'
  if target.is_symlink():target.unlink()
  assert not target.exists()
  target.symlink_to(root/name/'node_modules',target_is_directory=True)
 (cache/'dependencies.done').write_text('0\n')
except BaseException:
 (cache/'dependencies.done').write_text('1\n')
 raise
finally:
 (cache/'dependencies-results.json').write_text(json.dumps({'bun_version':value['bun_version'],'packages':rows},indent=2)+'\n')
