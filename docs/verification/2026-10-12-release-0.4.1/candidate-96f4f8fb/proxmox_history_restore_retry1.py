# ABOUTME: Backs up archived Atlas fixtures and verifies their actual off-server restore.
# ABOUTME: Keeps the disposable restore guest disconnected with application services masked.
import argparse
import json
import os
from pathlib import Path
import subprocess
import time

os.umask(0o077)
out=Path('/root/lifeos-release-0.4.1/history-restore-retry1')
parser=argparse.ArgumentParser()
parser.add_argument('--resume-backup',action='store_true')
args=parser.parse_args()
if args.resume_backup:
    assert (out/'archives.stdout').is_file()
    operations=json.loads((out/'operations.json').read_text())
else:
    assert not out.exists();out.mkdir(parents=True,mode=0o700)
    operations=[]
python=os.environ['LIFEOS_STABLE_PYTHON']
package='/home/lifeos-hermes/releases/qualification-20261013-041-96f4f8fb/source'
vmid=110
def run(args,label,*,input=None):
    started=time.monotonic()
    r=subprocess.run(args,input=input,capture_output=True,text=True,timeout=7200 if args[:2]==['pct','restore'] else 3600,
        umask=0o022 if args[0]=='vzdump' or args[:2]==['pct','restore'] else -1)
    (out/(label+'.stdout')).write_text(r.stdout);(out/(label+'.stderr')).write_text(r.stderr)
    operations.append({'label':label,'command':args,'exit_code':r.returncode,'elapsed_seconds':time.monotonic()-started})
    (out/'operations.json').write_text(json.dumps(operations,indent=2)+'\n')
    if r.returncode:raise RuntimeError(label+' fails: '+r.stderr[-1000:])
    print(json.dumps(operations[-1]),flush=True)
    return r.stdout
def source(code,label):
    return run(['pct','exec','101','--','runuser','-u','lifeos-hermes','--',python,'-B','-'],label,input=code)
services_code="""import os,sys,json
from pathlib import Path
profile=Path('/home/lifeos-hermes/.hermes')
root=Path(json.loads((profile/'lifeos-memory.json').read_text())['root'])
sys.path[:0]=[PACKAGE,PACKAGE+'/hermes']
os.environ.update(HERMES_HOME=str(profile),XDG_RUNTIME_DIR='/run/user/1008',DBUS_SESSION_BUS_ADDRESS='unix:path=/run/user/1008/bus')
from lifeos_hook_bridge.profile_services import ProfileServices
s=ProfileServices(profile,root)
ACTION
""".replace('PACKAGE',repr(package))
result=1
drained=False
created=False
try:
    guests=json.loads(run(['pvesh','get','/cluster/resources','--type','vm','--output-format','json'],'inventory'))
    assert all(row['vmid']!=vmid for row in guests),'The disposable guest identifier is already used'
    if args.resume_backup:
        archives=json.loads((out/'archives.stdout').read_text())
        archive=max(archives,key=lambda row:row['ctime'])['volid']
    else:
        source(services_code.replace('ACTION',"s.drain(signature=s.preview()['signature']);s.verify_stopped();print('Source writers drained')"),'drain-source')
        drained=True
        run(['vzdump','101','--storage','PBS-01','--mode','stop','--notes-template','LifeOS 0.4.1 managed release recovery'],'backup-source')
        archives=json.loads(run(['pvesh','get','/nodes/pve-tr1950x/storage/PBS-01/content','--content','backup','--vmid','101','--output-format','json'],'archives'))
        archive=max(archives,key=lambda row:row['ctime'])['volid']
        source(services_code.replace('ACTION',"s.resume();print('Source writers resumed')"),'resume-source')
        drained=False
    run(['pct','restore',str(vmid),archive,'--storage','local-zfs','--unprivileged','1','--onboot','0','--hostname','lifeos-041-recovery'],'restore')
    created=True
    run(['pct','set',str(vmid),'--delete','net0','--onboot','0','--tags','disposable;lifeos-041-recovery'],'disconnect')
    run(['pct','mount',str(vmid)],'mount')
    rootfs=Path('/var/lib/lxc')/str(vmid)/'rootfs'
    units=rootfs/'home/lifeos-hermes/.config/systemd/user'
    for name in ('hermes-dashboard.service','hermes-gateway.service','com.lifeos.pulse.service'):
        p=units/name;p.rename(units/(name+'.before-restore'));p.symlink_to('/dev/null')
    run(['pct','unmount',str(vmid)],'unmount')
    run(['pct','start',str(vmid)],'boot-isolated')
    config=run(['pct','config',str(vmid)],'restored-config')
    assert 'net0:' not in config and 'onboot: 0' in config
    run(['pct','exec',str(vmid),'--','ip','-brief','address'],'network')
    report=json.loads(run(['pct','exec',str(vmid),'--','runuser','-u','lifeos-hermes','--',python,'-B',
        '/home/lifeos-hermes/releases/qualification-20261013-041-96f4f8fb/history_guest_recovery.py','verify',package],'verify-history'))
    assert report['status']=='PASS' and report['version']=='0.4.1' and len(report['cases'])==3
    coverage=json.loads(run(['pct','exec',str(vmid),'--','runuser','-u','lifeos-hermes','--',python,'-B','/home/lifeos-hermes/releases/qualification-20261013-041-96f4f8fb/verify_stable_restored.py',os.environ['LIFEOS_STABLE_OPERATION']], 'verify-stable-programs'))
    assert coverage['status']=='PASS' and coverage['version']==report['version']
    assert coverage['operation']==os.environ['LIFEOS_STABLE_OPERATION']
    coverage.update(backup_archive=archive,source_guest=101,restored_guest=vmid)
    (out/'stable-program-coverage.json').write_text(json.dumps(coverage,indent=2)+'\n')
    (out/'verification.json').write_text(json.dumps({'status':'PASS','archive':archive,'source_guest':101,'restored_guest':vmid,
        'version':coverage['version'],'program_commit':coverage['program_commit'],'archive_sha256':coverage['archive_sha256'],
        'operation':coverage['operation'],
        'network_disconnected':True,'application_services_masked':True,'cases':report['cases'],
        'production_guest_changed':False},indent=2)+'\n')
    run(['pct','shutdown',str(vmid),'--timeout','90'],'shutdown-restore')
    result=0
finally:
    if drained:
        source(services_code.replace('ACTION',"s.resume();print('Source writers resumed after failure')"),'recover-source-services')
    try:
        if created and result==0:
            config=run(['pct','config',str(vmid)],'cleanup-config')
            assert 'hostname: lifeos-041-recovery' in config and 'net0:' not in config
            run(['pct','destroy',str(vmid),'--purge','1'],'destroy-disposable')
    except BaseException:
        result=1
        raise
    finally:
        (out/'process.done').write_text(str(result)+'\n')
