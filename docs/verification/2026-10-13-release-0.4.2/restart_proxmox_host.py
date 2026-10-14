# ABOUTME: Restarts the authorized Proxmox host after graceful guest shutdown and a completed sync.
# ABOUTME: Refuses forced guest stops and retains metadata for post-restart verification.
import json,os,subprocess,time
from pathlib import Path
os.umask(0o077)
out=Path('/root/lifeos-release-0.4.2/host-restart');out.mkdir(mode=0o700,exist_ok=True)
rows=[]
def run(command,label,timeout=30):
 start=time.monotonic()
 try:
  r=subprocess.run(command,capture_output=True,text=True,timeout=timeout)
  result={'label':label,'command':command,'exit_code':r.returncode,'stdout':r.stdout,'stderr':r.stderr,'elapsed_seconds':time.monotonic()-start}
 except subprocess.TimeoutExpired as error:
  result={'label':label,'command':command,'controller_timeout':timeout,'stdout':(error.stdout or b'').decode() if isinstance(error.stdout,bytes) else error.stdout or '', 'stderr':(error.stderr or b'').decode() if isinstance(error.stderr,bytes) else error.stderr or '', 'elapsed_seconds':time.monotonic()-start}
 rows.append(result);(out/'operations.json').write_text(json.dumps(rows,indent=2)+'\n')
 return result
try:
 (out/'original-boot-id').write_text(Path('/proc/sys/kernel/random/boot_id').read_text())
 run(['qm','shutdown','801','--timeout','180'],'graceful-vm-shutdown',210)
 state=run(['qm','status','801'],'verify-vm-stopped')
 assert state.get('exit_code')==0 and state['stdout'].strip()=='status: stopped','VM801 does not stop gracefully'
 for guest in [100,101,102]:
  run(['pct','shutdown',str(guest),'--timeout','90'],'graceful-ct-'+str(guest),120)
  state=run(['pct','status',str(guest)],'verify-ct-'+str(guest)+'-stopped')
  assert state.get('exit_code')==0 and state['stdout'].strip()=='status: stopped','An existing guest does not stop gracefully'
 synced=run(['sync'],'sync-host',120)
 assert synced.get('exit_code')==0,'Host sync does not complete'
 (out/'reboot-admission.json').write_text(json.dumps({'user_approved':True,'original_running_guests':[100,101,102,801],'all_original_running_guests_stopped':True,'host_sync_complete':True,'forced_guest_stop':False,'forced_host_reset':False},indent=2)+'\n')
 reboot=run(['systemctl','reboot'],'request-normal-host-reboot',30)
 assert reboot.get('exit_code')==0,'Normal host reboot does not admit'
 (out/'reboot-requested.done').write_text('0\n')
except BaseException:
 (out/'process.failed').write_text('1\n');raise
