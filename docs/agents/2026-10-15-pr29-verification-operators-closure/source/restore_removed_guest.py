# ABOUTME: Backs up the owned removal fixture and verifies its disconnected cold restore.
# ABOUTME: Preserves other guests and authenticates software rollback without exporting personal content.
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

if sys.flags.optimize:
    raise RuntimeError('Verification requires Python assertions')
os.umask(0o077)
out=Path('/root/lifeos-portability-cold-restore-20261015')
if out.exists():
    raise RuntimeError('The cold restore output already exists; inspect it before another operation')
out.mkdir(mode=0o700)
operations=[]
identifier='ab99723289884679b706440c7005fa5c'
home='/home/lifeos-hermes'
profile=home+'/.hermes'
python=profile+'/.lifeos-portability/'+identifier+'/stock-runtime/python-environment/bin/python'
code=1


def run(arguments,label,timeout=180):
    started=time.monotonic()
    with (out/(label+'.stdout')).open('w') as stdout,(out/(label+'.stderr')).open('w') as stderr:
        result=subprocess.run(arguments,stdout=stdout,stderr=stderr,timeout=timeout,
            umask=0o022 if arguments[0] in ('vzdump','pct') else -1)
    operations.append({'label':label,'command':arguments,'exit_code':result.returncode,
        'elapsed_seconds':time.monotonic()-started})
    (out/'operations.json').write_text(json.dumps(operations,indent=2)+'\n')
    if result.returncode:
        raise RuntimeError('Cold restore operation fails at '+label)
    return (out/(label+'.stdout')).read_text()


def owner(guest,script,*arguments):
    return ['pct','exec',str(guest),'--','runuser','-u','lifeos-hermes','--','env',
        'HOME='+home,'HERMES_HOME='+profile,'XDG_RUNTIME_DIR=/run/user/1000',
        'DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus',
        'PATH='+home+'/.local/bin:/usr/local/bin:/usr/bin:/bin',python,'-B',
        home+'/install-input/'+script,*arguments]


def validate_removed(value):
    assert value['workflow']==identifier and value['workflow_status']['state']=='verified'
    assert value['publication_status']['state']=='verified'
    assert value['workflow_receipt']['application_verified'] is True
    assert not any(value['active_software_present'].values())
    assert value['native_configuration_present'] is False and value['removal_marker_present'] is True
    assert value['recovery_helper_present'] is True
    assert value['services']['hermes-dashboard.service']['ActiveState']=='active'
    assert value['services']['hermes-gateway.service']['ActiveState']=='inactive'


try:
    before=json.loads(run(['pvesh','get','/cluster/resources','--type','vm','--output-format','json'],'guests-before'))
    assert all(row['vmid']!=111 for row in before)
    assert not Path('/etc/pve/lxc/111.conf').exists() and not Path('/etc/pve/qemu-server/111.conf').exists()
    config=run(['pct','config','110'],'source-config')
    assert 'hostname: lifeos-portability-test\n' in config
    assert 'tags: disposable;lifeos-portability\n' in config and 'onboot: 0\n' in config
    source=json.loads(run(owner(110,'observe_guest_removal_state.py',identifier,'--label','pbs-source-before'),'source-state'))
    validate_removed(source)
    before_archives=json.loads(run(['pvesh','get','/nodes/pve-tr1950x/storage/PBS-01/content',
        '--content','backup','--vmid','110','--output-format','json'],'archives-before'))
    run(['vzdump','110','--storage','PBS-01','--mode','stop','--remove','0','--protected','1',
        '--notification-mode','legacy-sendmail','--mailto','',
        '--notes-template','LifeOS 0.6.0 owned removal cold restore'],'backup-source',7200)
    after_archives=json.loads(run(['pvesh','get','/nodes/pve-tr1950x/storage/PBS-01/content',
        '--content','backup','--vmid','110','--output-format','json'],'archives-after'))
    added={row['volid'] for row in after_archives}-{row['volid'] for row in before_archives}
    assert len(added)==1
    archive=added.pop()
    assert archive.startswith('PBS-01:backup/ct/110/')
    (out/'selected-archive.json').write_text(json.dumps({'archive':archive})+'\n')
    run(['pct','restore','111',archive,'--storage','local-zfs','--unprivileged','1',
        '--onboot','0','--hostname','lifeos-portability-restore'],'restore',7200)
    run(['pct','set','111','--delete','net0','--onboot','0','--memory','4096','--cores','2',
        '--tags','disposable;lifeos-portability-restore'],'disconnect')
    config=run(['pct','config','111'],'restored-config')
    assert 'net0:' not in config and 'onboot: 0\n' in config
    assert 'hostname: lifeos-portability-restore\n' in config
    run(['pct','start','111'],'boot-offline')
    for attempt in range(60):
        result=subprocess.run(['pct','exec','111','--','test','-S','/run/user/1000/bus'],capture_output=True,timeout=15)
        if result.returncode==0:break
        time.sleep(2)
    else:raise RuntimeError('The restored user manager does not start')
    restored=json.loads(run(owner(111,'observe_guest_removal_state.py',identifier,'--label','pbs-restored-before'),'restored-state'))
    validate_removed(restored)
    assert restored['builtin_files']==source['builtin_files']
    native=json.loads(run(owner(111,'verify_restored_removal.py'),'restored-native-verification',600))
    assert native['status']=='PASS' and native['native_consistency_signature_verified'] is True
    assert native['builtin_files']=={key:value['sha256'] for key,value in source['builtin_files'].items()}
    authentication=json.loads(run(owner(111,'observe_guest_recovery_auth.py',identifier,'rollback',
        '--label','pbs-restored-060-rollback'),'restored-authentication',240))
    assert authentication['status']=='PASS' and authentication['admitted'] is True
    assert authentication['wrong_password'] is False and authentication['password_echo_disabled'] is True
    for attempt in range(60):
        rolled=json.loads(run(owner(111,'observe_guest_removal_state.py',identifier,
            '--label','pbs-restored-rollback'), 'rollback-state-'+str(attempt)))
        state=rolled['workflow_status']['state']
        if state=='rolled_back':break
        if state in ('failed','conflict'):raise RuntimeError('The restored rollback refuses')
        time.sleep(5)
    else:raise RuntimeError('The restored rollback does not finish')
    assert rolled['publication_status']['state']=='rolled_back'
    assert all(rolled['active_software_present'].values()) and rolled['native_configuration_present'] is True
    assert rolled['removal_marker_present'] is False and rolled['builtin_files']==source['builtin_files']
    version=json.loads(run(['pct','exec','111','--','runuser','-u','lifeos-hermes','--','env',
        'HOME='+home,'HERMES_HOME='+profile,home+'/.local/bin/hermes','lifeos-version'],'restored-version',120))['active']
    assert version['version']=='0.6.0' and version['verification']=='verified' and not version['modified_files']
    assert version['commit']=='c86b5887b899ca779afbb217c33843e1ee12c381'
    assert version['package_sha256']=='9e2a1939efbaccc94abaa879b265f1af447f9bdfe0b82aecc76f872f15fa9fb7'
    run(['pct','shutdown','111','--timeout','90'],'shutdown-restore',120)
    after=json.loads(run(['pvesh','get','/cluster/resources','--type','vm','--output-format','json'],'guests-after'))
    assert {row['vmid']:row['status'] for row in before}=={row['vmid']:row['status'] for row in after if row['vmid']!=111}
    receipt={'status':'PASS','source_guest':110,'restored_guest':111,'archive':archive,
        'archive_protected':True,'network_disconnected':True,'production_guest_changed':False,
        'workflow':identifier,'active_identity':version,'native_consistency':native,
        'retained_helper_authentication':authentication,'builtin_files':source['builtin_files'],
        'software_rollback_verified':True,'restored_guest_stopped':True,
        'all_original_guest_states_preserved':True,
        'operations_sha256':hashlib.sha256((out/'operations.json').read_bytes()).hexdigest()}
    (out/'verification.json').write_text(json.dumps(receipt,indent=2)+'\n')
    code=0
finally:
    (out/'process.done').write_text(str(code)+'\n')
