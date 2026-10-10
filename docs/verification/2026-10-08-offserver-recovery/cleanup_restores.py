# ABOUTME: Removes completed isolated recovery containers after verifying their retained PBS archives.
# ABOUTME: Preserves source guests, VM 801, backup schedules, and unrelated storage volumes.
import atexit
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

NODE='pve-tr1950x'
FIXTURES={102:('lifeos-recovery-probe',{'disposable','lifeos-recovery'},100,
    'PBS-01:backup/ct/100/2026-10-08T16:10:54Z'),
    103:('lifeos-dev-recovery',{'lifeos-recovery-disposable'},101,
    'PBS-01:backup/ct/101/2026-10-08T16:23:42Z')}
warnings=[]
completion={'succeeded':False}


def record_completion(path=Path(sys.argv[0]).with_name('fixture-cleanup.done'),state=completion):
    path.write_text('0\n' if state['succeeded'] else '1\n')


atexit.register(record_completion)


def command(*arguments):
    result=subprocess.run(arguments,capture_output=True,text=True,timeout=180)
    if result.stderr:warnings.append(result.stderr.strip())
    if result.returncode:raise RuntimeError(f'{arguments[0]} fails with status {result.returncode}: {result.stderr.strip()}')
    return result.stdout


def api(path):return json.loads(command('pvesh','get',path,'--output-format','json'))


def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True).encode()).hexdigest()


def protected():
    return {f'{kind}:{identifier}':{'configuration':digest(api(f'/nodes/{NODE}/{kind}/{identifier}/config')),
        'status':api(f'/nodes/{NODE}/{kind}/{identifier}/status/current')['status']}
        for kind,identifier in (('lxc',100),('lxc',101),('qemu',801))}


assert command('hostname','-s').strip()==NODE
before=protected()
schedule=digest(api('/cluster/backup'))
checked={}
for identifier,(name,tags,source,archive) in FIXTURES.items():
    config=api(f'/nodes/{NODE}/lxc/{identifier}/config')
    assert config['hostname']==name and set(config['tags'].split(';'))==tags
    assert config.get('onboot',0)==0 and config['unprivileged']==1 and 'lock' not in config
    assert api(f'/nodes/{NODE}/lxc/{identifier}/status/current')['status']=='stopped'
    assert all(part in config['net0'].split(',') for part in ('ip=manual','ip6=manual','link_down=1'))
    assert re.fullmatch(f'local-zfs:subvol-{identifier}-disk-0(?:,[^\n]+)?',config['rootfs'])
    assert not any(re.fullmatch(r'mp\d+',key) for key in config)
    listing=command('pvesm','list','PBS-01','--content','backup','--vmid',str(source))
    assert any(line.split()[0]==archive for line in listing.splitlines() if line.split())
    checked[identifier]={'hostname':name,'configuration_digest':digest(config),
        'archive':archive,'volume':config['rootfs'].split(',')[0]}

for identifier,receipt in checked.items():
    assert digest(api(f'/nodes/{NODE}/lxc/{identifier}/config'))==receipt['configuration_digest']
    assert api(f'/nodes/{NODE}/lxc/{identifier}/status/current')['status']=='stopped'
    command('pct','destroy',str(identifier))
    assert not Path(f'/etc/pve/lxc/{identifier}.conf').exists()
    assert receipt['volume'] not in command('pvesm','list','local-zfs','--vmid',str(identifier))

after=protected()
assert after==before and digest(api('/cluster/backup'))==schedule
for identifier,(_,_,source,archive) in FIXTURES.items():
    listing=command('pvesm','list','PBS-01','--content','backup','--vmid',str(source))
    assert any(line.split()[0]==archive for line in listing.splitlines() if line.split())

print(json.dumps({'status':'removed_completed_recovery_fixtures','fixtures':checked,
    'protected_before':before,'protected_after':after,'backup_schedule_digest':schedule,
    'archives_retained':True,'source_guests_unchanged':True,'backup_schedules_unchanged':True,
    'warnings':sorted(set(warnings))},indent=2),flush=True)
completion['succeeded']=True
