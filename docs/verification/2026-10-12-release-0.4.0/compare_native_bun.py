# ABOUTME: Compares pinned and fixed Bun runtimes through isolated frozen native installation operations.
# ABOUTME: Retains private command logs and reports case results without changing the active account installation.
import hashlib,importlib.util,json,os,shutil,subprocess,sys,time
from pathlib import Path
job=Path('/home/lifeos-hermes/.hermes/.lifeos-releases/67d6e3a05d24436cae2a4dd41c32028c')
package=job/'package';base=Path('/home/lifeos-hermes/releases/qualification-20261012-stable/bun-comparison');base.mkdir(mode=0o700)
sys.path.insert(0,str(package))
from optional.lifeos_release_manager.release_tools import prepare_bun
fixed_tools=base/'fixed-tools';fixed_tools.mkdir(mode=0o700)
fixed_bun=prepare_bun(fixed_tools,base.parent/'bun-fixed-tools-experiment.json','1.4.3')
bridge=base/'fixed-bridge';shutil.copytree(package/'lifeos_hook_bridge',bridge,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
catalog=bridge/'dependency_locks/catalog.json';value=json.loads(catalog.read_bytes());value['bun_version']='1.4.3';catalog.write_text(json.dumps(value,indent=2)+'\n')
script='import importlib.util,sys;from pathlib import Path;p=Path(sys.argv[1]);spec=importlib.util.spec_from_file_location("probe_install",p/"install_source.py");s=importlib.util.module_from_spec(spec);spec.loader.exec_module(s);s.install_lifeos(Path(sys.argv[2]),Path(sys.argv[3])/".claude",Path(sys.argv[3])/"failed",sys.argv[4],s.SUPPORTED_LIFEOS_COMMIT,p/"patches",s.LIFEOS_PATCHES)'
rows=[];receipt=Path.home()/'.hermes/integration-release.json';before=hashlib.sha256(receipt.read_bytes()).hexdigest()
for version,index in [('1.3.14',1),('1.4.3',1),('1.3.14',2),('1.4.3',2),('1.4.3',3)]:
 home=base/(version+'-'+str(index));home.mkdir(mode=0o700)
 bun=job/'tools/bun' if version=='1.3.14' else fixed_bun
 selected_bridge=package/'lifeos_hook_bridge' if version=='1.3.14' else bridge
 start=time.monotonic()
 with (home/'installer.stdout').open('w') as stdout,(home/'installer.stderr').open('w') as stderr:
  result=subprocess.run([sys.executable,'-B','-c',script,str(selected_bridge),str(package/'lifeos'),str(home),str(bun)],cwd=home,env=dict(os.environ,HOME=str(home),HERMES_HOME=str(home/'.hermes'),PYTHONDONTWRITEBYTECODE='1'),stdout=stdout,stderr=stderr,timeout=700)
 rows.append({'version':version,'case':index,'exit_code':result.returncode,'seconds':round(time.monotonic()-start,3),'native_locks_changed':False,'only_catalog_runtime_version_changed':version=='1.4.3'})
 assert hashlib.sha256(receipt.read_bytes()).hexdigest()==before
 (base/'results.json').write_text(json.dumps({'cases':rows,'active_profile_changed':False},indent=2)+'\n')
(base/'process.done').write_text('0\n')
print(json.dumps({'cases':rows,'active_profile_changed':False},indent=2))
