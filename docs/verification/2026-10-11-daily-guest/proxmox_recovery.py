# ABOUTME: Backs up the daily container to PBS and restores each synthetic recovery case offline.
# ABOUTME: Keeps restored guests disconnected and application services masked during verification.
import json
import os
from pathlib import Path
import subprocess
import time

os.umask(0o077)
here = Path('/root/lifeos-daily-install/recovery')
here.mkdir(mode=0o700, exist_ok=True)
python = '/home/lifeos-hermes/.hermes/installs/995dd15ff6e15ed0/environments/65f4231f26e94a2d989e89eb96b98808/venv/bin/python'
guest_evidence = '/home/lifeos-hermes/deployment/2026-10-11'
progress = []

def run(args, label, *, input=None):
    started = time.monotonic()
    # Proxmox stages configuration for the mapped container root to read.
    result = subprocess.run(args, input=input, capture_output=True, text=True, timeout=1800,
        umask=0o022 if args[0] == 'vzdump' else -1)
    (here / (label + '.stdout')).write_text(result.stdout)
    (here / (label + '.stderr')).write_text(result.stderr)
    progress.append({'label': label, 'command': args, 'exit_code': result.returncode,
        'elapsed_seconds': time.monotonic() - started})
    (here / 'progress.json').write_text(json.dumps(progress, indent=2) + '\n')
    print(json.dumps(progress[-1]), flush=True)
    if result.returncode:
        raise RuntimeError(label + ': ' + result.stdout[-3000:] + result.stderr[-3000:])
    return result.stdout

def guest(vmid, script, args, label):
    return run(['pct', 'exec', str(vmid), '--', 'runuser', '-u', 'lifeos-hermes', '--',
        python, '-B', '/home/lifeos-hermes/install-input/' + script, *args], label)

status = 'FAIL'
receipts = []
try:
    run(['pct', 'config', '102'], 'daily-config')
    run(['pct', 'exec', '102', '--', 'runuser', '-u', 'lifeos-hermes', '--', 'env',
        'XDG_RUNTIME_DIR=/run/user/1000', 'DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus',
        'systemctl', '--user', 'stop', 'hermes-dashboard.service', 'com.lifeos.pulse.service',
        'hermes-gateway.service'], 'drain-daily-writers')
    for index, case in enumerate(('baseline', 'interrupted', 'later-edit')):
        vmid = 103 + index
        retained = subprocess.run(['pct', 'exec', '102', '--', 'test', '-f',
            guest_evidence + '/recovery-fixtures/' + case + '/prepared.json'], capture_output=True)
        if retained.returncode:
            guest(102, 'prepare_recovery.py', [case], case + '-prepare')
        guest(102, 'guest_coverage.py', [case, 'prepare'], case + '-coverage')
        run(['pct', 'shutdown', '102', '--timeout', '90'], case + '-shutdown')
        run(['vzdump', '102', '--storage', 'PBS-01', '--mode', 'stop', '--notes-template',
            'LifeOS daily synthetic whole-guest recovery ' + case], case + '-backup')
        content = json.loads(run(['pvesh', 'get', '/nodes/pve-tr1950x/storage/PBS-01/content',
            '--content', 'backup', '--vmid', '102', '--output-format', 'json'], case + '-archives'))
        archive = max(content, key=lambda row: row['ctime'])['volid']
        run(['pct', 'restore', str(vmid), archive, '--storage', 'local-zfs', '--unprivileged', '1',
            '--onboot', '0', '--hostname', 'lifeos-recovery-' + case], case + '-restore')
        run(['pct', 'set', str(vmid), '--delete', 'net0', '--onboot', '0',
            '--tags', 'disposable;lifeos-recovery'], case + '-disconnect')
        run(['pct', 'mount', str(vmid)], case + '-mount')
        rootfs = Path('/var/lib/lxc') / str(vmid) / 'rootfs'
        units = rootfs / 'home/lifeos-hermes/.config/systemd/user'
        for name in ('hermes-dashboard.service', 'hermes-gateway.service', 'com.lifeos.pulse.service'):
            path = units / name
            path.rename(units / (name + '.before-recovery'))
            path.symlink_to('/dev/null')
        config = json.loads((rootfs / 'home/lifeos-hermes/.hermes/lifeos-memory.json').read_text())
        assert not config['ownership_enabled'] and not config['sharing_enabled']
        run(['pct', 'unmount', str(vmid)], case + '-unmount')
        run(['pct', 'start', str(vmid)], case + '-start-isolated')
        run(['pct', 'exec', str(vmid), '--', 'ip', '-brief', 'address'], case + '-network')
        # Linger starts the user service manager. Give its bus a bounded opportunity to appear.
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            probe = subprocess.run(['pct', 'exec', str(vmid), '--', 'test', '-S', '/run/user/1000/bus'],
                capture_output=True, timeout=10)
            if probe.returncode == 0:
                break
            time.sleep(1)
        unit_check = run(['pct', 'exec', str(vmid), '--', 'runuser', '-u', 'lifeos-hermes', '--', 'env',
            'XDG_RUNTIME_DIR=/run/user/1000', 'DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus',
            'systemctl', '--user', 'show', '-p', 'ActiveState', 'hermes-dashboard.service',
            'hermes-gateway.service', 'com.lifeos.pulse.service'], case + '-services')
        assert all(line == 'ActiveState=inactive' for line in unit_check.splitlines() if line), unit_check
        guest(vmid, 'guest_coverage.py', [case, 'verify'], case + '-coverage-verify')
        guest(vmid, 'verify_recovery.py', [case], case + '-recovery-verify')
        for source, target in ((guest_evidence + '/coverage-' + case + '-restored.json',
                here / (case + '-coverage-restored.json')),
            (guest_evidence + '/recovery-fixtures/' + case + '/restored-verification.json',
                here / (case + '-restored-verification.json'))):
            run(['pct', 'pull', str(vmid), source, str(target)], case + '-pull-' + target.name)
        receipts.append({'case': case, 'archive': archive, 'restored_guest': vmid,
            'network_removed_before_start': True, 'application_services_masked_before_start': True,
            'restored_ownership_enabled': False, 'restored_sharing_enabled': False, 'status': 'PASS'})
        (here / 'receipts.json').write_text(json.dumps(receipts, indent=2) + '\n')
        run(['pct', 'shutdown', str(vmid), '--timeout', '30'], case + '-stop-restore')
        run(['pct', 'start', '102'], case + '-restart-daily')
    status = 'PASS'
except BaseException as error:
    (here / 'failure.txt').write_text(str(error) + '\n')
    raise
finally:
    subprocess.run(['pct', 'start', '102'], capture_output=True, timeout=90)
    (here / 'result.json').write_text(json.dumps({'status': status, 'cases': receipts,
        'operations': progress}, indent=2) + '\n')
    (here / '.done').write_text('0\n' if status == 'PASS' else '1\n')
