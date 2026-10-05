from pathlib import Path
import subprocess,json,traceback
p=Path(__file__).parent
commands=[
 ['pveam','download','local','ubuntu-24.04-standard_24.04-2_amd64.tar.zst'],
 ['pct','create','100','local:vztmpl/ubuntu-24.04-standard_24.04-2_amd64.tar.zst',
  '--hostname','lifeos-install-probe','--unprivileged','1','--cores','2','--cpulimit','2',
  '--cpuunits','50','--memory','4096','--swap','0','--rootfs','local-zfs:24',
  '--net0','name=eth0,bridge=vmbr0,ip=dhcp,ip6=manual,firewall=1','--features','nesting=1',
  '--onboot','0','--tags','disposable;lifeos-test',
  '--description','Disposable LifeOS and Hermes installation acceptance fixture created 2026-10-05.'],
 ['pct','start','100'],['pct','config','100'],['qm','config','801']]
status=1
try:
 with (p/'output.txt').open('w') as out:
  for command in commands:
   out.write(json.dumps({'command':command})+'\n');out.flush()
   subprocess.run(command,stdout=out,stderr=subprocess.STDOUT,check=True)
 status=0
except Exception:
 (p/'error.txt').write_text(traceback.format_exc())
finally:
 (p/'run.done').write_text(str(status)+'\n')
