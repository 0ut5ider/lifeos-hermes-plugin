# ABOUTME: Creates a protected checkpoint before the development release transition.
# ABOUTME: Drains only the selected development profile and exports safe backup metadata.
import json,os,subprocess,sys,time
from pathlib import Path
os.umask(0o077)
root=Path('/root/lifeos-release-0.5.0');out=root/'development-checkpoint'
assert not out.exists();out.mkdir(mode=0o700)
operations=[]
def run(args,label,*,input=None,timeout=240):
 start=time.monotonic()
 r=subprocess.run(args,input=input,capture_output=True,text=True,timeout=timeout,umask=0o022 if args[0]=='vzdump' else -1)
 (out/(label+'.stdout')).write_text(r.stdout);(out/(label+'.stderr')).write_text(r.stderr)
 operations.append({'label':label,'command':args,'exit_code':r.returncode,'elapsed_seconds':time.monotonic()-start})
 (out/'operations.json').write_text(json.dumps(operations,indent=2)+'\n')
 assert r.returncode==0,label+' refuses'
 return r.stdout
python='/home/lifeos-hermes/.hermes/.lifeos-releases/5c37159bb67248b58e536a6c746e1c58/python-environment/bin/python'
code="""import importlib,json,os,sys
from pathlib import Path
profile=Path('/home/lifeos-hermes/.hermes')
receipt=json.loads((profile/'integration-release.json').read_bytes())
assert receipt['version']=='0.4.3' and receipt['commit']=='a1abb579558edcf29f7cd04ecfd998995d48db54'
sys.path.insert(0,str(profile/'plugins'))
root=Path(json.loads((profile/'lifeos-memory.json').read_bytes())['root'])
os.environ.update(HERMES_HOME=str(profile),XDG_RUNTIME_DIR='/run/user/'+str(os.getuid()),DBUS_SESSION_BUS_ADDRESS='unix:path=/run/user/'+str(os.getuid())+'/bus')
s=importlib.import_module('lifeos-hook-bridge.profile_services').ProfileServices(profile,root)
ACTION
"""
def source(action,label):return run(['pct','exec','101','--','runuser','-u','lifeos-hermes','--',python,'-B','-'],label,input=code.replace('ACTION',action))
result=1;recovery_required=False
try:
 complete=root/'rehearsal-whole-guest-restore/process.done'
 deadline=time.monotonic()+3600
 while not complete.exists():
  assert time.monotonic()<deadline
  time.sleep(5)
 assert complete.read_text().strip()=='0'
 verification=json.loads((complete.parent/'verification.json').read_bytes())
 assert verification['status']=='PASS' and verification['program_commit']=='04efe633296eb2b1a1d95561ca6d3e9516cd47dc'
 recovery_required=True
 source("s.drain(signature=s.preview()['signature']);s.verify_stopped();print('Development writers drained')",'drain-development')
 run(['vzdump','101','--storage','PBS-01','--mode','stop','--notes-template','LifeOS 0.4.3 before complete 0.5.0 transition'],'backup-development',timeout=7200)
 archives=json.loads(run(['pvesh','get','/nodes/pve-tr1950x/storage/PBS-01/content','--content','backup','--vmid','101','--output-format','json'],'archives'))
 archive=max(archives,key=lambda row:row['ctime'])['volid']
 assert archive.startswith('PBS-01:backup/ct/101/')
 source("s.resume();print('Development writers resumed')",'resume-development');recovery_required=False
 (out/'checkpoint.json').write_text(json.dumps({'status':'PASS','guest':101,'version':'0.4.3','program_commit':'a1abb579558edcf29f7cd04ecfd998995d48db54','protected_archive':archive,'writers_drained':True,'services_resumed':True,'daily_guest_changed':False},indent=2)+'\n')
 result=0
finally:
 failure=sys.exc_info()[1]
 try:
  if recovery_required:
   source("s.resume() if s.status()['recovery_required'] else None;print('Development service recovery checked')",'recover-development-services')
 except BaseException as cleanup_error:
  result=1
  if failure is None:raise
  failure.add_note('Development service recovery also fails: '+type(cleanup_error).__name__)
 finally:
  (out/'process.done').write_text(str(result)+'\n')
