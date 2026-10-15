# ABOUTME: Creates one explicitly owned disposable guest for memory portability acceptance.
# ABOUTME: Preserves existing guests and records only safe network and creation metadata.
import ipaddress
import json
from pathlib import Path
import subprocess
import time

folder=Path('/root/lifeos-memory-portability-20261015')
folder.mkdir(mode=0o700,exist_ok=True)
guest=110
code=1


def run(arguments, label, timeout=180):
    with (folder/(label+'.stdout')).open('w') as output,(folder/(label+'.stderr')).open('w') as error:
        result=subprocess.run(arguments,stdout=output,stderr=error,timeout=timeout)
    if result.returncode:raise RuntimeError('The disposable guest operation fails at '+label)
    return (folder/(label+'.stdout')).read_text()


try:
    if Path('/etc/pve/lxc/110.conf').exists() or Path('/etc/pve/qemu-server/110.conf').exists():
        raise RuntimeError('Guest110 already exists; this operator does not adopt existing guests')
    before=json.loads(run(['pvesh','get','/cluster/resources','--type','vm','--output-format','json'],'before'))
    config=Path('/var/lib/vz/template/cache/ubuntu-24.04-standard_24.04-2_amd64.tar.zst')
    if not config.is_file():raise RuntimeError('The reviewed Ubuntu24.04 template is unavailable')
    run(['pct','create',str(guest),str(config),'--hostname','lifeos-portability-test',
        '--unprivileged','1','--rootfs','local-zfs:32','--memory','8192','--swap','0','--cores','4',
        '--features','nesting=1','--net0','name=eth0,bridge=vmbr0,ip=dhcp,ip6=manual,type=veth',
        '--onboot','0','--tags','disposable;lifeos-portability',
        '--ssh-public-keys','/root/.ssh/authorized_keys'],'create',timeout=600)
    run(['pct','start',str(guest)],'start')
    address=None
    for attempt in range(30):
        result=subprocess.run(['pct','exec',str(guest),'--','ip','-j','-4','addr','show','scope','global'],
            text=True,capture_output=True,timeout=20)
        if result.returncode==0:
            values=json.loads(result.stdout)
            addresses=[row['local'] for interface in values for row in interface.get('addr_info',[]) if row.get('family')=='inet']
            selected=[value for value in addresses if ipaddress.ip_address(value) in ipaddress.ip_network('192.168.8.0/24')]
            if len(selected)==1:address=selected[0];break
        time.sleep(2)
    if address is None:raise RuntimeError('The disposable guest has no reviewed LAN address')
    after=json.loads(run(['pvesh','get','/cluster/resources','--type','vm','--output-format','json'],'after'))
    preserved={row['vmid']:row['status'] for row in before}
    actual={row['vmid']:row['status'] for row in after if row['vmid']!=guest}
    if actual!=preserved:raise RuntimeError('An unrelated guest state changes during creation')
    receipt={'status':'CREATED','guest':guest,'address':address,'hostname':'lifeos-portability-test',
        'template':config.name,'rootfs_gib':32,'memory_mib':8192,'cores':4,'onboot':False,
        'unprivileged':True,'preserved_guest_states':preserved,'production_changed':False}
    (folder/'guest.json').write_text(json.dumps(receipt,indent=2)+'\n')
    code=0
finally:
    (folder/'provision.done').write_text(str(code)+'\n')
