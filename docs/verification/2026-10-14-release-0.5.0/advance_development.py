# ABOUTME: Waits for the protected checkpoint and prepares the complete development candidate.
# ABOUTME: Uses the native exact-reference manager bootstrap and leaves package application for owner review.
import hashlib,json,os,subprocess,time
from pathlib import Path

os.umask(0o077)
project=Path(__file__).resolve().parents[3]
source=Path(__file__).resolve().parent
cache=Path('/home/outsider/.cache/lifeos-release-0.5.0-20261014')
out=cache/'development-advance'
assert not out.exists();out.mkdir(mode=0o700)
remote='root@192.168.8.252'
stage='/home/lifeos-hermes/releases/qualification-0.5.0'
python='/home/lifeos-hermes/.hermes/.lifeos-releases/5c37159bb67248b58e536a6c746e1c58/python-environment/bin/python'
commit='04efe633296eb2b1a1d95561ca6d3e9516cd47dc'
operations=[]
def run(command,label,*,input=None,timeout=120):
 started=time.monotonic()
 result=subprocess.run(command,input=input,capture_output=True,text=True,timeout=timeout)
 (out/(label+'.stdout')).write_text(result.stdout);(out/(label+'.stderr')).write_text(result.stderr)
 operations.append({'label':label,'exit_code':result.returncode,'elapsed_seconds':time.monotonic()-started})
 (out/'operations.json').write_text(json.dumps(operations,indent=2)+'\n')
 assert result.returncode==0,label+' refuses; inspect private operation output'
 return result.stdout
try:
 deadline=time.monotonic()+7200
 while True:
  result=subprocess.run(['ssh','-o','BatchMode=yes','root@192.168.8.101',
   'test -f /root/lifeos-release-0.5.0/development-checkpoint/process.done && cat /root/lifeos-release-0.5.0/development-checkpoint/process.done'],capture_output=True,text=True,timeout=30)
  if result.returncode==0:
   assert result.stdout.strip()=='0','Protected development checkpoint fails'
   break
  assert time.monotonic()<deadline,'Protected development checkpoint wait expires'
  time.sleep(20)
 checkpoint=json.loads(run(['ssh','-o','BatchMode=yes','root@192.168.8.101','cat /root/lifeos-release-0.5.0/development-checkpoint/checkpoint.json'],'protected-checkpoint'))
 assert checkpoint['status']=='PASS' and checkpoint['guest']==101 and checkpoint['services_resumed'] is True
 assert checkpoint['daily_guest_changed'] is False and checkpoint['protected_archive'].startswith('PBS-01:backup/ct/101/')
 (source/'development-protected-checkpoint.json').write_text(json.dumps(checkpoint,indent=2)+'\n')
 for name in ('prepare_development.py','run_development_owner_turn.py','verify_development_owner_turn.py','verify_promotion.py'):
  run(['scp',str(source/name),remote+':'+stage+'/'+name],'copy-'+name)
 run(['scp',str(source/'development-prepromotion-baseline.json'),remote+':'+stage+'/development-prepromotion-baseline.json'],'copy-baseline')
 command="runuser -u lifeos-hermes -- env HOME=/home/lifeos-hermes HERMES_HOME=/home/lifeos-hermes/.hermes /home/lifeos-hermes/.local/bin/hermes plugins install https://github.com/0ut5ider/lifeos-hermes-plugin#optional/lifeos_release_manager --ref "+commit+" --force --enable"
 run(['ssh','-o','BatchMode=yes',remote,command],'native-manager-bootstrap',timeout=600)
 verification="""import hashlib,json,tarfile
from pathlib import Path
profile=Path('/home/lifeos-hermes/.hermes')
stage=Path('/home/lifeos-hermes/releases/qualification-0.5.0')
archive=stage/'0.5.0-04efe633.tgz'
assert hashlib.sha256(archive.read_bytes()).hexdigest()=='a6dd0e11b8fb1b5ae30345be20c955db02728839f7bc907f60a70944ad392813'
count=0
with tarfile.open(archive) as tar:
 for item in tar.getmembers():
  prefix='optional/lifeos_release_manager/'
  if item.isfile() and item.name.startswith(prefix):
   assert (profile/'plugins/lifeos-release-manager'/item.name[len(prefix):]).read_bytes()==tar.extractfile(item).read()
   count+=1
assert count==21
baseline=json.loads((stage/'development-prepromotion-baseline.json').read_bytes())
for name,digest in baseline['configuration_file_sha256'].items():
 assert hashlib.sha256((profile/name).read_bytes()).hexdigest()==digest
print(json.dumps({'status':'PASS','method':'native-hermes-plugin-install','ref':'04efe633296eb2b1a1d95561ca6d3e9516cd47dc','manager_files_verified':count,'configuration_file_bytes_preserved':True,'complete_integration_applied':False,'daily_server_changed':False}))
"""
 text=run(['ssh','-o','BatchMode=yes',remote,'runuser -u lifeos-hermes -- '+python+' -B -'],'verify-native-bootstrap',input=verification)
 receipt=json.loads(text);assert receipt['status']=='PASS'
 (source/'development-manager-bootstrap.json').write_text(json.dumps(receipt,indent=2)+'\n')
 run(['ssh','-o','BatchMode=yes',remote,'runuser -u lifeos-hermes -- env XDG_RUNTIME_DIR=/run/user/1008 DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1008/bus systemctl --user restart hermes-dashboard.service'],'restart-development-dashboard')
 run(['ssh','-o','BatchMode=yes',remote,'chown lifeos-hermes:lifeos-hermes '+stage+'/*.py '+stage+'/development-prepromotion-baseline.json; runuser -u lifeos-hermes -- env HOME=/home/lifeos-hermes HERMES_HOME=/home/lifeos-hermes/.hermes '+python+' -B '+stage+'/prepare_development.py'],'prepare-complete-candidate',timeout=1800)
 run(['scp',remote+':'+stage+'/development-preparation.json',str(source/'development-preparation.json')],'export-safe-preparation')
 receipt=json.loads((source/'development-preparation.json').read_bytes());assert receipt['status']=='PASS'
 (out/'process.done').write_text('0\n')
except BaseException:
 (out/'process.done').write_text('1\n');raise
