# ABOUTME: Verifies an owned rehearsal reboot before its disconnected whole-guest recovery.
# ABOUTME: Waits for the actual update sequence and retains bounded safe operator receipts.
import json,os,subprocess,time
from pathlib import Path
os.umask(0o077)
root=Path('/root/lifeos-release-0.5.0');out=root/'reboot-and-restore'
assert not out.exists();out.mkdir(mode=0o700)
stage='/home/lifeos-hermes/releases/qualification-0.5.0'
def run(args,label,timeout=180):
 r=subprocess.run(args,capture_output=True,text=True,timeout=timeout)
 (out/(label+'.stdout')).write_text(r.stdout);(out/(label+'.stderr')).write_text(r.stderr)
 if r.returncode:raise RuntimeError(label+' fails')
 return r.stdout
code=1
try:
 deadline=time.monotonic()+2400
 while True:
  r=subprocess.run(['pct','exec','111','--','test','-f',stage+'/recovery-sequence.done'],capture_output=True,text=True,timeout=30)
  if r.returncode==0:break
  assert time.monotonic()<deadline
  time.sleep(5)
 assert run(['pct','exec','111','--','cat',stage+'/recovery-sequence.done'],'sequence-done').strip()=='0'
 prepared=json.loads(run(['pct','exec','111','--','cat',stage+'/final-apply-preparation.json'],'selected-operation'))
 identifier=prepared['preparation']['identifier']
 request=json.loads(run(['pct','exec','111','--','cat','/home/lifeos-hermes/.hermes/.lifeos-releases/'+identifier+'/runtime.json'],'selected-runtime'))
 python=request['python']
 before=run(['pct','exec','111','--','cat','/proc/sys/kernel/random/boot_id'],'before-boot-id').strip()
 run(['pct','reboot','111','--timeout','90'],'reboot-owned-guest',timeout=180)
 deadline=time.monotonic()+120
 while True:
  r=subprocess.run(['pct','exec','111','--','cat','/proc/sys/kernel/random/boot_id'],capture_output=True,text=True,timeout=30)
  if r.returncode==0 and r.stdout.strip()!=before:break
  assert time.monotonic()<deadline
  time.sleep(1)
 after=r.stdout.strip();assert after and after!=before
 run(['pct','exec','111','--','runuser','-u','lifeos-hermes','--',python,'-B',stage+'/verify_rehearsal.py','0.5.0','final-applied'],'verify-reboot',timeout=240)
 (out/'reboot-verification.json').write_text(json.dumps({'status':'PASS','source_guest':111,'operation':identifier,'program_commit':prepared['candidate'],'archive_sha256':prepared['preparation']['package_sha256'],'boot_identity_changed':True,'selected_programs_and_services_verified':True,'model_mapping_and_synthetic_memory_preserved':True,'production_guest_changed':False},indent=2)+'\n')
 env=dict(os.environ,LIFEOS_STABLE_PYTHON=python,LIFEOS_STABLE_OPERATION=identifier)
 with (out/'whole-restore.stdout').open('w') as stdout,(out/'whole-restore.stderr').open('w') as stderr:
  result=subprocess.run(['python3',str(root/'proxmox_rehearsal_restore.py')],env=env,stdout=stdout,stderr=stderr,timeout=14400)
 assert result.returncode==0
 code=0
finally:
 (out/'process.done').write_text(str(code)+'\n')
