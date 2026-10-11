# ABOUTME: Stages exact Atlas retention source bytes in isolated installed profiles on .252.
# ABOUTME: Records native and Hermes tests while checking unchanged live configuration and services.
import base64
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time


STAGE = Path('/home/lifeos-hermes/development/2026-10-11-atlas-retention')
PACKAGE = Path('/home/lifeos-hermes/migration/2026-10-09/daily-text-0.2.0-11577ed4/package')
PYTHON = '/home/lifeos-hermes/.hermes/installs/995dd15ff6e15ed0/environments/65f4231f26e94a2d989e89eb96b98808/venv/bin/python'
SUITE = ['test_memory_atlas_retention', 'test_memory_atlas_capacity', 'test_memory_atlas_sync',
    'test_memory_atlas', 'test_memory_atlas_insight', 'test_memory_atlas_insight_edges',
    'test_memory_atlas_guest_recovery', 'test_memory_atlas_jobs', 'test_memory_owner_job_command',
    'test_memory_publication_recovery', 'test_footprint_contracts', 'test_plugin_lifecycle']


def guest():
    os.umask(0o077)
    native = PACKAGE/'lifeos/LifeOS/install'
    environment = dict(os.environ, PATH='/home/lifeos-hermes/.bun/bin:/home/lifeos-hermes/.local/bin:/usr/local/bin:/usr/bin:/bin',
        PYTHONDONTWRITEBYTECODE='1', PYTHONPATH=f'{STAGE}:{STAGE/"tests"}:{PACKAGE/"hermes"}',
        LIFEOS_HERMES_SOURCE=str(PACKAGE/'hermes'), LIFEOS_MEMORY_SOURCE=str(native),
        LIFEOS_TASK_HOOK_PATH=str(native/'hooks/TaskGovernance.hook.ts'))
    def state():
        service_environment = dict(environment, XDG_RUNTIME_DIR='/run/user/1008',
            DBUS_SESSION_BUS_ADDRESS='unix:path=/run/user/1008/bus')
        result = subprocess.run(['systemctl','--user','show','hermes-gateway.service','hermes-dashboard.service',
            'com.lifeos.pulse.service','--property=Id,ActiveState,NRestarts'],
            env=service_environment,capture_output=True,text=True,check=True)
        files = {name:hashlib.sha256((Path.home()/'.hermes'/name).read_bytes()).hexdigest()
            for name in ('config.yaml','lifeos-memory.json')}
        return {'services':result.stdout,'profile_configuration_hashes':files}
    hashes = json.loads((STAGE/'source-hashes.json').read_text())
    verify = lambda: all(hashlib.sha256((STAGE/name).read_bytes()).hexdigest()==value for name,value in hashes.items())
    assert verify(), 'The isolated source files differ before verification'
    before = state()
    command = [sys.executable,'-W','error::ResourceWarning','-m','unittest','-v',*SUITE]
    started = time.monotonic()
    with (STAGE/'development.stdout').open('w') as stdout, (STAGE/'development.stderr').open('w') as stderr:
        result = subprocess.run(command, cwd=STAGE, env=environment, stdout=stdout, stderr=stderr, timeout=900)
    after = state()
    report = {'host':'192.168.8.252','exit_code':result.returncode,'command':command,
        'duration_seconds':round(time.monotonic()-started,3),'source_hashes':hashes,
        'source_hashes_unchanged':verify(),'live_before':before,'live_after':after,
        'live_configuration_and_services_unchanged':before==after,
        'native_store_sha256':hashlib.sha256((native/'LIFEOS/ATLAS/Store.ts').read_bytes()).hexdigest(),
        'profile_scope':'Disposable installed Hermes profiles with actual native Atlas and private local HTTP fixtures',
        'daily_guest_modified':False,'live_discord_messages_sent':0}
    (STAGE/'development-verification.json').write_text(json.dumps(report,indent=2)+'\n')
    (STAGE/'development.done').write_text(str(result.returncode)+'\n')


def stage():
    root = Path(__file__).resolve().parents[3]
    files = subprocess.check_output(['git','ls-files','lifeos_hook_bridge','tests'],cwd=root,text=True).splitlines()
    files += ['lifeos_hook_bridge/memory_atlas_history.py','tests/test_memory_atlas_retention.py',
        'tests/memory_atlas_retention_process.py',str(Path(__file__).relative_to(root))]
    files = sorted(set(files))
    payload = {name:base64.b64encode((root/name).read_bytes()).decode() for name in files}
    hashes = {name:hashlib.sha256((root/name).read_bytes()).hexdigest() for name in files}
    script = 'import base64,json,os,pwd,subprocess\nfrom pathlib import Path\n'
    script += f'stage=Path({str(STAGE)!r})\npayload={payload!r}\nhashes={hashes!r}\n'
    script += f'python={PYTHON!r}\noperator={str(Path(__file__).relative_to(root))!r}\n'
    script += '''os.umask(0o077)
assert not stage.exists(), 'The isolated retention stage already exists'
stage.mkdir(mode=0o700)
for name,content in payload.items():
    path=stage/name
    path.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
    path.write_bytes(base64.b64decode(content));path.chmod(0o600)
(stage/'source-hashes.json').write_text(json.dumps(hashes,indent=2)+'\\n')
account=pwd.getpwnam('lifeos-hermes')
for path in [stage,*stage.rglob('*')]:
    os.chown(path,account.pw_uid,account.pw_gid)
with (stage/'process.stdout').open('w') as stdout,(stage/'process.stderr').open('w') as stderr:
    process=subprocess.Popen(['runuser','-u','lifeos-hermes','--',python,'-B',str(stage/operator),'--guest'],
        stdin=subprocess.DEVNULL,stdout=stdout,stderr=stderr,start_new_session=True)
print(json.dumps({'status':'STAGED','pid':process.pid,'path':str(stage),'files':len(payload)}))
'''
    result = subprocess.run(['ssh','-o','BatchMode=yes','root@192.168.8.252','python3 -'],
        input=script,capture_output=True,text=True,timeout=60,check=True)
    print(result.stdout,end='')


if __name__=='__main__':
    guest() if sys.argv[1:] == ['--guest'] else stage()
