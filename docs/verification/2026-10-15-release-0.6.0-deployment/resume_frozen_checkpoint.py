# ABOUTME: Resumes only the admitted daily writers after Proxmox mounts their frozen backup snapshot.
# ABOUTME: Keeps transfer completion separate from source service availability and preserves safe evidence.
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

parser = argparse.ArgumentParser()
parser.add_argument('phase', choices=('daily-preupdate', 'daily-postupdate'))
args = parser.parse_args()
if sys.flags.optimize:
    raise RuntimeError('Snapshot admission requires assertions')
name, operation, drain, resumed = {
    'daily-preupdate': ('checkpoint-daily', 'b9e873b251604202a58442b502a3c2b2', 'drain-writers', 'resume-writers'),
    'daily-postupdate': ('daily-whole-guest-restore', 'f25cd605ccef45db829b69dfbf5f8a66', 'drain-source', 'resume-source'),
}[args.phase]
folder = Path('/root/lifeos-promotion-060-20261015') / name
receipt = {'status': 'FAIL', 'source_guest': 102, 'phase': args.phase}
snapshot = 'rpool/data/subvol-102-disk-0@vzdump'
if (folder / 'frozen-snapshot-resume.json').exists():
    raise RuntimeError('This one-time snapshot admission already has a receipt')
try:
    for attempt in range(180):
        operations = json.loads((folder / 'operations.json').read_bytes()) if (folder / 'operations.json').is_file() else []
        assert all(row['exit_code'] == 0 for row in operations)
        if any(row['label'] == resumed for row in operations):
            receipt.update(status='PASS', already_resumed_by_checkpoint=True,
                services_resumed_before_transfer_completion=False)
            break
        admitted = any(row['label'] == drain for row in operations)
        result = subprocess.run(['zfs', 'get', '-Hp', '-o', 'property,value',
            'creation,guid', snapshot], capture_output=True, text=True)
        if admitted and result.returncode == 0:
            metadata = dict(line.split('\t', 1) for line in result.stdout.splitlines())
            if int(metadata['creation']) >= int(folder.stat().st_mtime):
                break
        time.sleep(1)
    else:
        raise RuntimeError('No current frozen snapshot is admitted')
    if receipt['status'] != 'PASS':
        tasks = json.loads(subprocess.check_output(['pvesh', 'get', '/nodes/pve-tr1950x/tasks',
            '--source', 'active', '--output-format', 'json'], text=True))
        assert any(row.get('type') == 'vzdump' and row.get('id') == '102' for row in tasks)
        backup = Path('/usr/share/perl5/PVE/VZDump/LXC.pm').read_bytes()
        assert hashlib.sha256(backup).hexdigest() == '52b4280502e2a64dd896b5091367430b371552e4c5a94795d916294bc413559f'
        source = """import importlib,json,os,sys,subprocess
from pathlib import Path
p=Path('/home/lifeos-hermes/.hermes');sys.path.insert(0,str(p/'plugins'));uid=str(os.getuid())
os.environ.update(HERMES_HOME=str(p),XDG_RUNTIME_DIR='/run/user/'+uid,DBUS_SESSION_BUS_ADDRESS='unix:path=/run/user/'+uid+'/bus')
m=importlib.import_module('lifeos-hook-bridge.profile_services');c=json.loads((p/'lifeos-memory.json').read_bytes());s=m.ProfileServices(p,Path(c['root']))
before=s.status()['state'];assert before in ('stopped','active')
if before=='stopped':s.verify_stopped();s.resume()
assert s.status()['state']=='active'
for name in ('hermes-dashboard.service','hermes-gateway.service','com.lifeos.pulse.service'):
 r=subprocess.run(['systemctl','--user','show',name,'--property=ActiveState,SubState,MainPID','--no-pager'],capture_output=True,text=True,check=True)
 values=dict(line.split('=',1) for line in r.stdout.splitlines());assert not r.stderr
 assert values['ActiveState']=='active' and values['SubState']=='running' and int(values['MainPID'])>0
print(json.dumps({'state':'active','uid':int(uid),'resumed':before=='stopped'}))
"""
        python = '/home/lifeos-hermes/.hermes/.lifeos-releases/' + operation + '/python-environment/bin/python'
        result = subprocess.run(['pct', 'exec', '102', '--', 'runuser', '-u', 'lifeos-hermes', '--',
            python, '-B', '-'], input=source, text=True, capture_output=True, check=True)
        assert all('PVE::Storage::Custom::TrueNASPlugin' in line and 'older storage API' in line for line in result.stderr.splitlines())
        observed = json.loads(result.stdout)
        assert observed['uid'] == 1000 and observed['state'] == 'active'
        receipt.update(status='PASS', snapshot=snapshot, snapshot_guid=metadata['guid'],
            snapshot_creation=int(metadata['creation']), native_backup_source_sha256=hashlib.sha256(backup).hexdigest(),
            services_resumed_before_transfer_completion=observed['resumed'],
            source_service_state=observed['state'])
except Exception as error:
    receipt['error_type'] = type(error).__name__
finally:
    folder.mkdir(parents=True, exist_ok=True, mode=0o700)
    (folder / 'frozen-snapshot-resume.json').write_text(json.dumps(receipt, indent=2) + '\n')
    (folder / 'frozen-snapshot-resume.done').write_text('0\n' if receipt['status'] == 'PASS' else '1\n')
raise SystemExit(0 if receipt['status'] == 'PASS' else 1)
