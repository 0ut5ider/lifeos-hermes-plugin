# ABOUTME: Executes actual SSH and Docker adapter controls on the isolated development server.
# ABOUTME: Binds the complete current sources and retains raw results and image identity.
import hashlib,json,os,subprocess
from pathlib import Path
root=Path('/var/tmp/lifeos-step1-20261006/remote-tests')
repo=root/'repository'
config=json.loads(Path('/var/tmp/lifeos-step1-20261006/evaluation-operations-final-configuration.json').read_text())
python=config['hermes']['command'][0]
source=Path('/var/tmp/lifeos-step1-20261006/hermes-complete')
lifeos=Path('/var/tmp/lifeos-step1-20261006/lifeos-evaluation-final')
image=subprocess.check_output(['docker','image','inspect','lifeos-step1-python-curl:20261006','--format','{{.Id}}'],text=True).strip()
project='/var/tmp/lifeos-step1-20261006/remote-policy-project'
env={**os.environ,**config['hermes']['environment'],'HOME':str(root/'home'),
 'PYTHONPATH':str(repo/'tests')+':'+str(repo)+':'+config['hermes']['environment']['PYTHONPATH'],
 'PATH':'/var/tmp/lifeos-step1-20261006/bin:'+os.environ['PATH'],
 'LIFEOS_DIR':str(root/'home/.claude/LIFEOS'),'LIFEOS_PERMISSION_HOOK':str(lifeos/'hooks/Safety.hook.ts'),
 'LIFEOS_SSH_PROBE_HOST':'127.0.0.1','LIFEOS_SSH_PROBE_USER':'root',
 'LIFEOS_SSH_PROBE_KEY':str(root/'ssh-key'),'LIFEOS_SSH_PROBE_PROJECT':project,
 'LIFEOS_SSH_PROBE_ISA':project+'/ISA.md','LIFEOS_DOCKER_PROBE_IMAGE':image}
env['HERMES_HOME']=str(root/'home/.hermes')
env['LIFEOS_HOOK_SETTINGS']=str(root/'home/.claude/settings.json')
modules=['test_live_ssh_command_policy','test_live_remote_project_hooks','test_live_project_hook_transport',
 'test_live_nested_ssh_hooks','test_live_ssh_web_cache','test_live_remote_isa',
 'test_live_container_command_policy','test_live_container_project_hooks','test_live_container_file_hooks',
 'test_live_container_isa']
command=[python,'-m','unittest',*modules,'-v']
(root.parent/'remote-reviewed/command.json').write_text(json.dumps({'command':command,'environment':{k:v for k,v in env.items()
 if k.startswith('LIFEOS_') or k in ('HOME','PATH','PYTHONPATH')},'docker_image':image,
 'docker_version':subprocess.check_output(['docker','version','--format','{{.Server.Version}}'],text=True).strip(),
 'source_sha256':{str(p.relative_to(repo)):hashlib.sha256(p.read_bytes()).hexdigest() for base in ('lifeos_hook_bridge','tests')
 for p in (repo/base).rglob('*.py')}},indent=2)+'\n')
with (root.parent/'remote-reviewed/tests.txt').open('w') as log:
 result=subprocess.run(command,cwd=repo,env=env,stdout=log,stderr=subprocess.STDOUT)
(root.parent/'remote-reviewed/run.done').write_text(str(result.returncode)+'\n')
