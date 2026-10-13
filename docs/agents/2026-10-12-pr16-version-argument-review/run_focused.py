# ABOUTME: Runs the bounded release argument and metadata checks with copied native sources.
# ABOUTME: Keeps the sealed runtime and all existing user profiles outside the mutable test workspace.
import json,os,shutil,subprocess,sys,tempfile,time
from pathlib import Path
repo=Path('/home/outsider/Projects/Hermes_agent/LifeOS_plugin');cache=Path('/home/outsider/.cache/lifeos-hermes-managed-20261012');out=Path(__file__).parent
with tempfile.TemporaryDirectory(prefix='pr16-focused-') as temp:
 root=Path(temp);home=root/'home';home.mkdir(mode=0o700)
 host=root/'hermes';shutil.copytree(cache/'packages/0.4.0-a87e7ae9/hermes',host,ignore=shutil.ignore_patterns('__pycache__','*.pyc','.bytecode-fingerprint','.hermes'))
 env={key:value for key,value in os.environ.items() if key in ('PATH','LANG','LC_ALL','SSL_CERT_FILE','SSL_CERT_DIR')}
 env.update(HOME=str(home),TZ='UTC',PYTHONDONTWRITEBYTECODE='1',
 PATH=str(cache/'fixed-bun-tools')+':'+env.get('PATH',os.defpath),PYTHONPATH=str(repo)+':'+str(repo/'tests')+':'+str(host),
 LIFEOS_HERMES_SOURCE=str(host),LIFEOS_FRESH_SOURCE=str(cache/'packages/0.4.0-a87e7ae9/lifeos'),
 LIFEOS_MANAGED_FRESH_OPERATION=str(cache/'fresh-qualification-d4bff560-repeat/.hermes/.lifeos-releases/148fa606a5ae4eb3a436cd523b6ed8ee'))
 command=[sys.executable,'-B','-W','error::ResourceWarning','-m','unittest','-v','test_release_manager_cli','test_release_dashboard','test_release_version','test_native_dependencies']
 start=time.monotonic()
 with (out/'focused.stdout').open('w') as stdout,(out/'focused.stderr').open('w') as stderr:
  r=subprocess.run(command,cwd=repo,env=env,stdout=stdout,stderr=stderr,timeout=600)
 report={'command':command,'exit_code':r.returncode,'elapsed_seconds':time.monotonic()-start,'isolated_home':True,'sealed_hermes_copied':True,'original_sealed_source_mutated':False}
 (out/'focused.json').write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps(report,indent=2));assert r.returncode==0
