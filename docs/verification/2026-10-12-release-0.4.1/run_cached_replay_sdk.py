# ABOUTME: Repeats SDK registration with the packaged base interpreter and account-home working directory.
# ABOUTME: Tests a source copy without selecting programs or invoking command handlers.
from pathlib import Path
import subprocess,json,hashlib
repo=Path('/home/outsider/Projects/Hermes_agent/LifeOS_plugin')
q=repo/'docs/verification/2026-10-12-release-0.4.1'
code='''import os,pwd,subprocess,json,hashlib
from pathlib import Path
home=Path('/home/lifeos-hermes'); stage=home/'releases/qualification-20261012-041'; job=home/'.hermes/.lifeos-releases/c78b6c52e0724e44b6ed46bdf38f93af'
folder=stage/'cached-replay-sdk-probe'; folder.mkdir(mode=0o700,exist_ok=True)
owner=pwd.getpwnam('lifeos-hermes'); os.chown(folder,owner.pw_uid,owner.pw_gid)
site=job/'python-environment/lib/python3.14/site-packages'
base=job/'dependency-profile/tools/python-3.14.7+20260901-linux-x64/bin/python3'
env=dict(os.environ,HOME=str(home),HERMES_HOME=str(home/'.hermes'),PYTHONDONTWRITEBYTECODE='1',PYTHONPATH=str(job/'package/hermes')+':'+str(site),PATH=str(home/'.local/bin')+':/usr/local/bin:/usr/bin:/bin')
env.pop('PYTHONHOME',None)
bootstrap='import site,runpy,sys; site.addsitedir(sys.argv.pop(1)); script=sys.argv.pop(1); sys.argv[0]=script; runpy.run_path(script,run_name="__main__")'
command=['/usr/sbin/runuser','-u','lifeos-hermes','--',str(base),'-P','-c',bootstrap,str(site),str(stage/'diagnose_candidate_registration.py'),str(job),str(folder),str(stage/'single-pass-bridge')]
r=subprocess.run(command,cwd=home,env=env,capture_output=True,text=True,timeout=60)
sdk=json.loads((folder/'candidate-registration.json').read_bytes())
print(json.dumps({'sdk':sdk,'exit':r.returncode,'stderr':r.stderr,'bridge_sha256':hashlib.sha256((stage/'single-pass-bridge/bridge.py').read_bytes()).hexdigest()}))
'''
r=subprocess.run(['ssh','root@192.168.8.252','python3','-B','-'],input=code,capture_output=True,text=True,timeout=90)
(q/'config-inventory-sdk-replay.stderr').write_text(r.stderr)
assert r.returncode==0,r.stderr
value=json.loads(r.stdout)
assert value['bridge_sha256']==hashlib.sha256((repo/'lifeos_hook_bridge/bridge.py').read_bytes()).hexdigest()
assert value['exit']==0 and value['sdk']['error'] is None
(q/'config-inventory-sdk-replay.json').write_text(json.dumps(value,indent=2)+'\n')
print(json.dumps(value,indent=2))
