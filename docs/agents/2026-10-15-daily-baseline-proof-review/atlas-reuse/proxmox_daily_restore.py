# ABOUTME: Backs up the exact daily runtime and synthetic Atlas fixtures for disconnected recovery.
# ABOUTME: Keeps the disposable restore guest disconnected with application services masked.
import argparse
import json
import os
import re
from pathlib import Path
import subprocess
import shutil
import sys
import time
from prepared_atlas_evidence import verify_preparation

os.umask(0o077)
parser=argparse.ArgumentParser()
parser.add_argument('--resume-backup',action='store_true')
parser.add_argument('--out',type=Path,default=Path('/root/lifeos-release-0.5.0/daily-whole-guest-restore'))
parser.add_argument('--backup-evidence',type=Path)
parser.add_argument('--verifier',type=Path)
parser.add_argument('--prepared-atlas-evidence',type=Path)
args=parser.parse_args()
out=args.out
assert not (args.resume_backup and args.prepared_atlas_evidence)
if args.resume_backup:
    backup_evidence=args.backup_evidence or out
    assert (backup_evidence/'archives.stdout').is_file()
    captured=json.loads((backup_evidence/'capture-program-artifacts.stdout').read_text())
    if backup_evidence!=out:
        assert not out.exists();out.mkdir(parents=True,mode=0o700)
        operations=[]
    else:
        operations=json.loads((out/'operations.json').read_text())
else:
    assert not out.exists();out.mkdir(parents=True,mode=0o700)
    operations=[]
python=os.environ['LIFEOS_STABLE_PYTHON']
identifier=os.environ['LIFEOS_STABLE_OPERATION']
assert len(identifier)==32 and all(c in '0123456789abcdef' for c in identifier)
package='/home/lifeos-hermes/.hermes/.lifeos-releases/'+identifier+'/package'
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
    return run(['pct','exec','102','--','runuser','-u','lifeos-hermes','--',python,'-B','-'],label,input=code)
services_code="""import os,sys,json,subprocess
from pathlib import Path
profile=Path('/home/lifeos-hermes/.hermes')
root=Path(json.loads((profile/'lifeos-memory.json').read_text())['root'])
sys.path[:0]=[PACKAGE,PACKAGE+'/hermes']
os.environ.update(HERMES_HOME=str(profile),XDG_RUNTIME_DIR='/run/user/'+str(os.getuid()),DBUS_SESSION_BUS_ADDRESS='unix:path=/run/user/'+str(os.getuid())+'/bus')
from lifeos_hook_bridge.profile_services import ProfileServices
s=ProfileServices(profile,root)
def verify_running():
 for name in ('hermes-dashboard.service','hermes-gateway.service','com.lifeos.pulse.service'):
  r=subprocess.run(['systemctl','--user','show',name,'--property=ActiveState,SubState','--no-pager'],capture_output=True,text=True,check=True)
  values=dict(line.split('=',1) for line in r.stdout.splitlines() if '=' in line)
  assert values=={'ActiveState':'active','SubState':'running'},name
ACTION
""".replace('PACKAGE',repr(package))
result=1
recovery_required=False
created=False
try:
    guests=json.loads(run(['pvesh','get','/cluster/resources','--type','vm','--output-format','json'],'inventory'))
    assert all(row['vmid']!=vmid for row in guests),'The disposable guest identifier is already used'
    if not args.resume_backup:
        ready=json.loads(source("from pathlib import Path;import json;print((Path('/home/lifeos-hermes/releases/qualification-0.5.0')/'daily-editor-activation.json').read_text())",'editor-checkpoint'))
        assert ready['status']=='PASS' and ready['operation']==identifier and ready['only_modules_hermes_changed'] is True
        if args.prepared_atlas_evidence:
            preparation=verify_preparation(args.prepared_atlas_evidence,python,identifier)
            checked=json.loads(source('''import hashlib,json,stat
from pathlib import Path
folder=Path('/home/lifeos-hermes/deployment/history-recovery-0.5.0-04efe633')
report=json.loads((folder/'prepare.json').read_bytes())
assert json.dumps(report,sort_keys=True)==json.dumps(EXPECTED,sort_keys=True)
for row in report['cases']:
 selected=folder/row['case'];home=selected/'home'
 prepared=json.loads((selected/'prepared.json').read_bytes())
 assert prepared['case']==row['case'] and Path(prepared['home'])==home
 assert len(prepared['captured'])==row['files']
 for name,entry in prepared['captured'].items():
  path=Path(name);assert path.is_relative_to(home) and path.resolve()==path
  info=path.lstat();assert stat.S_ISREG(info.st_mode)
  assert hashlib.sha256(path.read_bytes()).hexdigest()==entry['sha256']
  assert stat.S_IMODE(info.st_mode)==entry['mode']
print(json.dumps(report))
'''.replace('EXPECTED',repr(preparation['report'])),'check-existing-synthetic-atlas'))
            assert json.dumps(checked,sort_keys=True)==json.dumps(preparation['report'],sort_keys=True)
            (out/'reused-atlas-preparation.json').write_text(json.dumps(preparation,indent=2)+'\n')
        else:
            run(['pct','exec','102','--','runuser','-u','lifeos-hermes','--',python,'-B',
                '/home/lifeos-hermes/releases/qualification-0.5.0/history_guest_recovery.py','prepare',package],'prepare-synthetic-atlas')
    if args.resume_backup:
        archives=json.loads((backup_evidence/'archives.stdout').read_text())
        archive=max(archives,key=lambda row:row['ctime'])['volid']
        recovery_required=True
        source(services_code.replace('ACTION',"s.resume() if s.status()['recovery_required'] else None;assert not s.status()['recovery_required'];verify_running();print('Source writers active after backup continuation')"),'verify-resumed-source')
        recovery_required=False
    else:
        recovery_required=True
        source(services_code.replace('ACTION',"s.resume() if s.status()['recovery_required'] else None;s.drain(signature=s.preview()['signature']);s.verify_stopped();print('Source writers drained')"),'drain-source')
        current_mount=json.loads(run(['pct','exec','102','--','runuser','-u','lifeos-hermes','--',python,'-B',
            '/home/lifeos-hermes/releases/qualification-0.5.0/verify_daily_restored_programs.py','capture',identifier],'capture-current-owner-mount'))
        assert current_mount['status']=='PASS' and current_mount['prior_release_restore_available'] is False
        captured=json.loads(run(['pct','exec','102','--','runuser','-u','lifeos-hermes','--',python,'-B',
            '/home/lifeos-hermes/releases/qualification-0.5.0/program_artifact_receipt.py','capture',os.environ['LIFEOS_STABLE_OPERATION']], 'capture-program-artifacts'))
        run(['vzdump','102','--storage','PBS-01','--mode','snapshot','--notes-template','LifeOS 0.5.0 daily complete release recovery'],'backup-source')
        archives=json.loads(run(['pvesh','get','/nodes/pve-tr1950x/storage/PBS-01/content','--content','backup','--vmid','102','--output-format','json'],'archives'))
        archive=max(archives,key=lambda row:row['ctime'])['volid']
        source(services_code.replace('ACTION',"s.resume();verify_running();print('Source writers resumed')"),'resume-source')
        recovery_required=False
    assert archive.startswith('PBS-01:backup/ct/102/')
    run(['pvesh','set','/nodes/pve-tr1950x/storage/PBS-01/content/'+archive,'--protected','1'],'protect-archive')
    protection=json.loads(run(['pvesh','get','/nodes/pve-tr1950x/storage/PBS-01/content/'+archive,'--output-format','json'],'verify-protection'))
    assert protection['protected'] is True
    run(['pct','restore',str(vmid),archive,'--storage','lifeos-050-tests','--rootfs','lifeos-050-tests:120','--unprivileged','1','--onboot','0','--hostname','lifeos-050-daily-recovery'],'restore')
    created=True
    restored_config=run(['pct','config',str(vmid)],'restored-config-before-disconnect')
    for interface in re.findall(r'(?m)^(net\d+):',restored_config):
        run(['pct','set',str(vmid),'--delete',interface],'disconnect-'+interface)
    run(['pct','set',str(vmid),'--onboot','0','--tags','disposable;lifeos-050-daily-recovery'],'disable-automatic-start')
    disconnected=run(['pct','config',str(vmid)],'verify-disconnected-before-boot')
    assert not re.search(r'(?m)^(?:net\d+:|lxc\.net\.)',disconnected)
    assert 'onboot: 0' in disconnected and 'unprivileged: 1' in disconnected
    run(['pct','mount',str(vmid)],'mount')
    rootfs=Path('/var/lib/lxc')/str(vmid)/'rootfs'
    if args.verifier:
        verifier=rootfs/'home/lifeos-hermes/releases/qualification-0.5.0/verify_daily_restored_programs.py'
        prior=verifier.stat()
        shutil.copyfile(args.verifier,verifier)
        os.chown(verifier,prior.st_uid,prior.st_gid)
        os.chmod(verifier,prior.st_mode & 0o777)
    units=rootfs/'home/lifeos-hermes/.config/systemd/user'
    for name in ('hermes-dashboard.service','hermes-gateway.service','com.lifeos.pulse.service'):
        p=units/name;p.rename(units/(name+'.before-restore'));p.symlink_to('/dev/null')
    run(['pct','unmount',str(vmid)],'unmount')
    run(['pct','start',str(vmid)],'boot-isolated')
    config=run(['pct','config',str(vmid)],'restored-config')
    assert not re.search(r'(?m)^(?:net\d+:|lxc\.net\.)',config) and 'onboot: 0' in config
    run(['pct','exec',str(vmid),'--','ip','-brief','address'],'network')
    report=json.loads(run(['pct','exec',str(vmid),'--','runuser','-u','lifeos-hermes','--',python,'-B',
        '/home/lifeos-hermes/releases/qualification-0.5.0/history_guest_recovery.py','verify',package],'verify-history'))
    assert report['status']=='PASS' and report['version']=='0.5.0' and len(report['cases'])==3
    artifacts=json.loads(run(['pct','exec',str(vmid),'--','runuser','-u','lifeos-hermes','--',python,'-B',
        '/home/lifeos-hermes/releases/qualification-0.5.0/program_artifact_receipt.py','verify',os.environ['LIFEOS_STABLE_OPERATION']], 'verify-program-artifacts'))
    assert artifacts['status']=='PASS' and artifacts['private_map_sha256']==captured['private_map_sha256']
    assert artifacts['artifacts']==captured['artifacts'] and artifacts['program_commit']==captured['program_commit']
    (out/'program-artifact-coverage.json').write_text(json.dumps(artifacts,indent=2)+'\n')
    coverage=json.loads(run(['pct','exec',str(vmid),'--','runuser','-u','lifeos-hermes','--',python,'-B','/home/lifeos-hermes/releases/qualification-0.5.0/verify_daily_restored_programs.py','verify',os.environ['LIFEOS_STABLE_OPERATION']], 'verify-stable-programs'))
    assert coverage['status']=='PASS' and coverage['version']==report['version']
    assert coverage['operation']==os.environ['LIFEOS_STABLE_OPERATION']
    coverage.update(backup_archive=archive,source_guest=102,restored_guest=vmid)
    (out/'stable-program-coverage.json').write_text(json.dumps(coverage,indent=2)+'\n')
    (out/'verification.json').write_text(json.dumps({'status':'PASS','archive':archive,'source_guest':102,'restored_guest':vmid,
        'version':coverage['version'],'program_commit':coverage['program_commit'],'archive_sha256':coverage['archive_sha256'],
        'operation':coverage['operation'],
        'network_disconnected':True,'application_services_masked':True,'cases':report['cases'],
        'source_programs_or_personal_data_changed':False,'source_synthetic_fixtures_created':True,'source_writers_resumed':True,'backup_pruning_protection_verified':True,'runtime_artifact_coverage':artifacts},indent=2)+'\n')
    run(['pct','shutdown',str(vmid),'--timeout','90'],'shutdown-restore')
    result=0
finally:
    failure=sys.exc_info()[1]
    try:
        if recovery_required:
            try:
                source(services_code.replace('ACTION',"s.resume() if s.status()['recovery_required'] else None;verify_running();print('Source service recovery checked')"),'recover-source-services')
            except BaseException as cleanup_error:
                result=1
                if failure is None:raise
                failure.add_note('Source service recovery also fails: '+type(cleanup_error).__name__)
        if created and result==0:
            config=run(['pct','config',str(vmid)],'cleanup-config')
            assert 'hostname: lifeos-050-daily-recovery' in config and not re.search(r'(?m)^(?:net\d+:|lxc\.net\.)',config)
            assert 'tags: disposable;lifeos-050-daily-recovery' in config
            run(['pct','destroy',str(vmid),'--purge','1'],'destroy-disposable')
    except BaseException:
        result=1
        raise
    finally:
        (out/'process.done').write_text(str(result)+'\n')
