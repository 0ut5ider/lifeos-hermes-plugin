# ABOUTME: Creates a protected whole-guest checkpoint before an authorized complete release update.
# ABOUTME: Drains application writers and preserves every original guest power state.
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time

parser = argparse.ArgumentParser()
parser.add_argument('server', choices=('development', 'daily'))
args = parser.parse_args()
if sys.flags.optimize:
    raise RuntimeError('Checkpoint verification requires assertions')
os.umask(0o077)
guest, hostname, operation = {
    'development': (101, 'lifeos-dev', '4eac8d1b398e47138d80f8b67b6df596'),
    'daily': (102, 'lifeos-daily', 'b9e873b251604202a58442b502a3c2b2'),
}[args.server]
out = Path('/root/lifeos-promotion-060-20261015') / ('checkpoint-' + args.server)
out.mkdir(parents=True, mode=0o700)
operations = []
drained = False
receipt = {'status': 'FAIL', 'server': args.server, 'guest': guest}

def run(command, label, *, source=None, timeout=180):
    started = time.monotonic()
    result = subprocess.run(command, input=source, capture_output=True, text=True,
        timeout=timeout, umask=0o022 if command[0] == 'vzdump' else -1)
    (out / (label + '.stdout')).write_text(result.stdout)
    (out / (label + '.stderr')).write_text(result.stderr)
    operations.append({'label': label, 'command': command, 'exit_code': result.returncode,
        'elapsed_seconds': time.monotonic() - started})
    (out / 'operations.json').write_text(json.dumps(operations, indent=2) + '\n')
    if result.returncode:
        raise RuntimeError('Checkpoint fails at ' + label)
    return result.stdout

def inventory(label):
    values = json.loads(run(['pvesh', 'get', '/cluster/resources', '--type', 'vm',
        '--output-format', 'json'], label))
    return {str(row['vmid']): row['status'] for row in values}

def archives(label):
    return json.loads(run(['pvesh', 'get', '/nodes/pve-tr1950x/storage/PBS-01/content',
        '--content', 'backup', '--vmid', str(guest), '--output-format', 'json'], label))

def services(action):
    code = """import importlib,json,os,sys
from pathlib import Path
p=Path('/home/lifeos-hermes/.hermes');sys.path.insert(0,str(p/'plugins'))
os.environ.update(HERMES_HOME=str(p),XDG_RUNTIME_DIR='/run/user/1000',DBUS_SESSION_BUS_ADDRESS='unix:path=/run/user/1000/bus')
m=importlib.import_module('lifeos-hook-bridge.profile_services')
c=json.loads((p/'lifeos-memory.json').read_bytes());s=m.ProfileServices(p,Path(c['root']))
""" + action
    python = '/home/lifeos-hermes/.hermes/.lifeos-releases/' + operation + '/python-environment/bin/python'
    return run(['pct', 'exec', str(guest), '--', 'runuser', '-u', 'lifeos-hermes', '--',
        python, '-B', '-'], 'resume-writers' if 's.resume()' in action else 'drain-writers', source=code)

try:
    before = inventory('guests-before')
    config = run(['pct', 'config', str(guest)], 'source-config')
    assert 'hostname: ' + hostname + '\n' in config and before[str(guest)] == 'running'
    previous = archives('archives-before')
    services("assert not s.status()['recovery_required'];s.drain(signature=s.preview()['signature']);s.verify_stopped();print('Writers drained')")
    drained = True
    run(['vzdump', str(guest), '--storage', 'PBS-01', '--mode', 'snapshot', '--remove', '0',
        '--protected', '1', '--notification-mode', 'legacy-sendmail', '--mailto', '',
        '--notes-template', 'LifeOS 0.6.0 ' + args.server + ' prepromotion checkpoint'], 'backup', timeout=7200)
    current = archives('archives-after')
    added = {row['volid'] for row in current} - {row['volid'] for row in previous}
    assert len(added) == 1
    archive = added.pop()
    selected = next(row for row in current if row['volid'] == archive)
    assert archive.startswith('PBS-01:backup/ct/' + str(guest) + '/') and selected['protected'] == 1
    assert {row['volid'] for row in previous}.issubset({row['volid'] for row in current})
    services("s.resume();assert not s.status()['recovery_required'];print('Writers resumed')")
    drained = False
    assert inventory('guests-after') == before
    receipt.update(status='PASS', prior_version='0.5.0', protected_archive=archive,
        backup_bytes=selected['size'], writers_drained=True, services_resumed=True,
        all_original_guest_states_preserved=True, previous_archives_preserved=True,
        restore_test_performed=False, personal_records_exported=False)
except Exception as error:
    receipt['error_type'] = type(error).__name__
finally:
    if drained:
        services("s.resume();print('Writers resumed after failure')")
    (out / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    (out / 'process.done').write_text('0\n' if receipt['status'] == 'PASS' else '1\n')
raise SystemExit(0 if receipt['status'] == 'PASS' else 1)
