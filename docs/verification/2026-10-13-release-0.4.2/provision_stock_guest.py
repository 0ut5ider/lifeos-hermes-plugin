# ABOUTME: Creates a manager-free disposable Hermes test guest after checking the Proxmox inventory.
# ABOUTME: Records provisioning outcomes without changing existing guests.
import os,json,subprocess,time
from pathlib import Path
os.umask(0o077)
out=Path('/root/lifeos-release-0.4.2/provision')
out.mkdir(parents=True,exist_ok=True)
commands=[['pvesh','get','/cluster/resources','--type','vm','--output-format','json'],['pct','create','107','local:vztmpl/ubuntu-24.04-standard_24.04-2_amd64.tar.zst','--hostname','lifeos-042-stock-test','--rootfs','local-zfs:120','--unprivileged','1','--memory','8192','--cores','4','--features','nesting=1','--net0','name=eth0,bridge=vmbr0,ip=dhcp,firewall=1','--onboot','0','--tags','lifeos-test','--ssh-public-keys','/root/lifeos-release-0.4.2/test-public-key.pub','--start','1']]
rows=[]
try:
 for number,command in enumerate(commands):
  start=time.monotonic()
  result=subprocess.run(command,capture_output=True,text=True,timeout=600)
  (out/(str(number)+'.stdout')).write_text(result.stdout)
  (out/(str(number)+'.stderr')).write_text(result.stderr)
  rows.append({'command':command,'exit_code':result.returncode,'elapsed_seconds':time.monotonic()-start})
  (out/'operations.json').write_text(json.dumps(rows,indent=2)+'\n')
  assert result.returncode==0,'Read saved provisioning output'
  if number==0:assert all(row['vmid']!=107 for row in json.loads(result.stdout))
 (out/'process.done').write_text('0\n')
except BaseException:
 (out/'process.done').write_text('1\n');raise
