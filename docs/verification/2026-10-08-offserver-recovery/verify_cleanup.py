# ABOUTME: Verifies completed recovery-fixture removal from the retained external cleanup receipt.
# ABOUTME: Records completion only after source guests, schedules, volumes, and PBS archives match.
import hashlib
import json
from pathlib import Path
import subprocess

BASE=Path('/root/lifeos-release-acceptance/2026-10-08')
expected=json.loads((BASE/'fixture-cleanup.json').read_text())
warnings=[]


def command(*arguments):
    result=subprocess.run(arguments,capture_output=True,text=True,timeout=120)
    if result.stderr:warnings.append(result.stderr.strip())
    if result.returncode:raise RuntimeError(f'{arguments[0]} fails with status {result.returncode}')
    return result.stdout


def api(path):return json.loads(command('pvesh','get',path,'--output-format','json'))


def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True).encode()).hexdigest()


assert command('hostname','-s').strip()=='pve-tr1950x'
assert expected['status']=='removed_completed_recovery_fixtures'
assert set(expected['fixtures'])=={'102','103'}
for identifier,receipt in expected['fixtures'].items():
    assert not Path(f'/etc/pve/lxc/{identifier}.conf').exists()
    assert receipt['volume'] not in command('pvesm','list','local-zfs','--vmid',identifier)
    source='100' if identifier=='102' else '101'
    listing=command('pvesm','list','PBS-01','--content','backup','--vmid',source)
    assert any(line.split()[0]==receipt['archive'] for line in listing.splitlines() if line.split())
for reference,receipt in expected['protected_after'].items():
    kind,identifier=reference.split(':')
    assert digest(api(f'/nodes/pve-tr1950x/{kind}/{identifier}/config'))==receipt['configuration']
    assert api(f'/nodes/pve-tr1950x/{kind}/{identifier}/status/current')['status']==receipt['status']
assert digest(api('/cluster/backup'))==expected['backup_schedule_digest']
print(json.dumps({'status':'verified_cleanup','fixtures':[102,103],'volumes_absent':True,
    'archives_retained':True,'source_guests_unchanged':True,'vm_801_unchanged':True,
    'backup_schedules_unchanged':True,'warnings':sorted(set(warnings))},indent=2),flush=True)
(BASE/'fixture-cleanup-verified.done').write_text('0\n')
