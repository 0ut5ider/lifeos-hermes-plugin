# ABOUTME: Runs actual service admission controls with a separate development user manager.
# ABOUTME: Records completion without changing stable-state admission or workstation watches.
import json,os,subprocess
from pathlib import Path
base=Path('/var/tmp/lifeos-step1-20261006')
repo=base/'remote-tests/repository'
root=base/'service-manager-managed';root.mkdir(exist_ok=True)
(root/'tmp').mkdir(exist_ok=True)
os.chown(root/'tmp',1007,1007)
config=json.loads((base/'evaluation-operations-final-configuration.json').read_text())
env={**os.environ,**config['hermes']['environment'],'HOME':'/home/lifeos-plugin-install-probe',
 'XDG_RUNTIME_DIR':'/run/user/1007','DBUS_SESSION_BUS_ADDRESS':'unix:path=/run/user/1007/bus',
 'LIFEOS_HERMES_SOURCE':config['hermes']['environment']['PYTHONPATH'].split(':')[0],'LIFEOS_MEMORY_SOURCE':str(base/'lifeos-evaluation-final'),'PATH':str(base/'bin')+':'+os.environ['PATH'],'TMPDIR':str(root/'tmp'),'PYTHONPATH':str(repo/'tests')+':'+str(repo)+':'+config['hermes']['environment']['PYTHONPATH']}
python=str(Path(config['hermes']['environment']['PYTHONPATH'].split(':')[-1]).parents[2]/'bin/python')
cmd=[python,'-m','unittest','test_profile_services','test_ownership_setup','test_ownership_setup_host','-v']
(root/'command.json').write_text(json.dumps({'command':cmd,'target_uid':1007,'user_manager':'user@1007.service','environment':{k:env[k] for k in ('HOME','TMPDIR','XDG_RUNTIME_DIR','DBUS_SESSION_BUS_ADDRESS','PYTHONPATH')},'watch_limit':Path('/proc/sys/fs/inotify/max_user_watches').read_text().strip()},indent=2)+'\n')
with (root/'tests.txt').open('w') as f:
 r=subprocess.run(cmd,cwd=repo,env=env,user=1007,group=1007,extra_groups=[],stdout=f,stderr=subprocess.STDOUT)
(root/'run.done').write_text(str(r.returncode)+'\n')
