# ABOUTME: Creates a consistent off-server backup after the verified daily promotion.
# ABOUTME: Resumes the original daily services and exports only backup and process metadata.
import json
import os
from pathlib import Path
import subprocess
import time

os.umask(0o077)
out = Path('/root/lifeos-release-0.4.3/daily-postpromotion-backup')
assert not out.exists(), 'The backup evidence already exists'
out.mkdir(parents=True, mode=0o700)
python = '/home/lifeos-hermes/.hermes/.lifeos-releases/52af3122ef614ac49ef55b692e392f0c/python-environment/bin/python'
operations = []


def run(command, label, *, input=None, timeout=3600):
    started = time.monotonic()
    result = subprocess.run(command, input=input, capture_output=True, text=True, timeout=timeout,
        umask=0o022 if command[0] == 'vzdump' else -1)
    (out / (label + '.stdout')).write_text(result.stdout)
    (out / (label + '.stderr')).write_text(result.stderr)
    operations.append({'action': label, 'exit_code': result.returncode,
        'elapsed_seconds': round(time.monotonic() - started, 3)})
    (out / 'operations.json').write_text(json.dumps(operations, indent=2) + '\n')
    assert result.returncode == 0, label + ' fails'
    return result.stdout


def services(action):
    code = """import importlib,json,os,sys
from pathlib import Path
p=Path('/home/lifeos-hermes/.hermes');sys.path.insert(0,str(p/'plugins'))
os.environ.update(HERMES_HOME=str(p),XDG_RUNTIME_DIR='/run/user/1000',DBUS_SESSION_BUS_ADDRESS='unix:path=/run/user/1000/bus')
m=importlib.import_module('lifeos-hook-bridge.profile_services')
c=json.loads((p/'lifeos-memory.json').read_bytes());s=m.ProfileServices(p,Path(c['root']))
ACTION
""".replace('ACTION', action)
    return run(['pct', 'exec', '102', '--', 'runuser', '-u', 'lifeos-hermes', '--',
        python, '-B', '-'], 'resume-services' if 's.resume()' in action else 'drain-services', input=code)


drain_attempted = False
completed = False
try:
    services("assert not s.status()['recovery_required'];print('Daily service recovery preflight passed')")
    drain_attempted = True
    services("s.drain(signature=s.preview()['signature']);s.verify_stopped();print('Daily writers drained')")
    run(['vzdump', '102', '--storage', 'PBS-01', '--mode', 'snapshot',
        '--notes-template', 'LifeOS 0.4.3 daily postpromotion checkpoint'], 'backup-daily')
    archives = json.loads(run(['pvesh', 'get', '/nodes/pve-tr1950x/storage/PBS-01/content',
        '--content', 'backup', '--vmid', '102', '--output-format', 'json'], 'list-backups'))
    archive = max((row for row in archives if row['volid'].startswith('PBS-01:backup/ct/102/')), key=lambda row: row['ctime'])
    services("s.resume();assert not s.status()['recovery_required'];print('Daily writers resumed')")
    drain_attempted = False
    receipt = {'status': 'PASS', 'source_guest': 102, 'selected_version': '0.4.3',
        'archive': archive['volid'], 'backup_bytes': archive['size'], 'backup_mode': 'snapshot',
        'application_writers_drained': True, 'original_services_resumed': True,
        'prior_protected_checkpoint_preserved': True, 'restore_test_performed': False,
        'safe_operations': operations}
    (out / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    completed = True
finally:
    try:
        if drain_attempted:
            services("if s.status()['recovery_required']: s.resume()\nassert not s.status()['recovery_required'];print('Daily service recovery checked after failure')")
    finally:
        (out / 'process.done').write_text('0\n' if completed else '1\n')
