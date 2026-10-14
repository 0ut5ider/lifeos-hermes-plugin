# ABOUTME: Restores the exact protected daily checkpoint into an isolated disposable guest.
# ABOUTME: Masks application services before boot and exports safe verification receipts without changing daily.
import json
import os
from pathlib import Path
import shutil
import subprocess
import time

os.umask(0o077)
folder = Path('/root/lifeos-daily-checkpoint-restore-20261014')
out = folder / 'observation'
assert not out.exists(), 'This observation already has evidence'
out.mkdir(mode=0o700)
archive = 'PBS-01:backup/ct/102/2026-10-14T16:15:12Z'
storage = 'lifeos-daily-restore'
storage_path = Path('/var/lib/vz/lifeos-daily-restore')
vmid = 110
python = '/home/lifeos-hermes/.hermes/.lifeos-releases/52af3122ef614ac49ef55b692e392f0c/python-environment/bin/python'
operations = []
created = False
storage_created = False
success = False


def run(command, label, *, timeout=3600):
    started = time.monotonic()
    result = subprocess.run(command, capture_output=True, text=True, timeout=timeout,
        umask=0o022 if command[:2] == ['pct', 'restore'] else -1)
    (out / (label + '.stdout')).write_text(result.stdout)
    (out / (label + '.stderr')).write_text(result.stderr)
    operations.append({'action': label, 'command': command, 'exit_code': result.returncode,
        'elapsed_seconds': round(time.monotonic() - started, 3)})
    (out / 'operations.json').write_text(json.dumps(operations, indent=2) + '\n')
    assert result.returncode == 0, label + ' fails; inspect private host evidence'
    print(json.dumps({'action': label, 'exit_code': result.returncode}), flush=True)
    return result.stdout


try:
    guests = json.loads(run(['pvesh', 'get', '/cluster/resources', '--type', 'vm', '--output-format', 'json'], 'inventory'))
    assert all(row['vmid'] != vmid for row in guests)
    originals = {str(row['vmid']): row['status'] for row in guests}
    details = json.loads(run(['pvesh', 'get', '/nodes/pve-tr1950x/storage/PBS-01/content/' + archive,
        '--output-format', 'json'], 'protected-archive'))
    assert details['protected'] is True and details['size'] == 24360759650
    assert details['format'] == 'pbs-ct' and details['path'].endswith('/ct/102/2026-10-14T16:15:12Z')
    stores = json.loads(run(['pvesh', 'get', '/storage', '--output-format', 'json'], 'storage-inventory'))
    assert all(row['storage'] != storage for row in stores) and not storage_path.exists()
    storage_path.mkdir(mode=0o700)
    run(['pvesm', 'add', 'dir', storage, '--path', str(storage_path), '--content', 'rootdir'], 'create-test-storage')
    storage_created = True
    run(['pct', 'restore', str(vmid), archive, '--storage', storage, '--rootfs', storage + ':80',
        '--unprivileged', '1', '--onboot', '0', '--hostname', 'lifeos-daily-checkpoint-recovery'], 'restore-exact-checkpoint', timeout=7200)
    created = True
    run(['pct', 'set', str(vmid), '--delete', 'net0', '--onboot', '0', '--memory', '4096',
        '--cores', '4', '--tags', 'disposable;lifeos-daily-checkpoint-recovery'], 'disconnect-before-boot')
    run(['pct', 'mount', str(vmid)], 'mount-restored-filesystem')
    rootfs = Path('/var/lib/lxc') / str(vmid) / 'rootfs'
    units = rootfs / 'home/lifeos-hermes/.config/systemd/user'
    for name in ('hermes-dashboard.service', 'hermes-gateway.service', 'com.lifeos.pulse.service'):
        path = units / name
        assert path.is_file() and not path.is_symlink()
        path.rename(units / (name + '.before-checkpoint-test'))
        path.symlink_to('/dev/null')
    stage = rootfs / 'home/lifeos-hermes/checkpoint-verification-20261014'
    assert not stage.exists()
    stage.mkdir(mode=0o700)
    owner = (rootfs / 'home/lifeos-hermes').stat()
    os.chown(stage, owner.st_uid, owner.st_gid)
    for name in ('verify_daily_checkpoint.py', 'history_guest_recovery.py', 'daily-promotion-baseline.json'):
        target = stage / name
        shutil.copyfile(folder / name, target)
        os.chown(target, owner.st_uid, owner.st_gid)
        target.chmod(0o600)
    run(['pct', 'unmount', str(vmid)], 'unmount-restored-filesystem')
    run(['pct', 'start', str(vmid)], 'boot-disconnected')
    config = run(['pct', 'config', str(vmid)], 'isolated-config')
    assert 'net0:' not in config and 'onboot: 0' in config and 'unprivileged: 1' in config
    run(['pct', 'exec', str(vmid), '--', 'ip', '-brief', 'address'], 'isolated-network')
    receipt = json.loads(run(['pct', 'exec', str(vmid), '--', 'runuser', '-u', 'lifeos-hermes', '--',
        python, '-B', '/home/lifeos-hermes/checkpoint-verification-20261014/verify_daily_checkpoint.py'], 'verify-current-daily', timeout=1800))
    assert receipt['status'] == 'PASS' and receipt['version'] == '0.4.3'
    run(['pct', 'shutdown', str(vmid), '--timeout', '90'], 'shutdown-test-guest')
    cleanup_config = run(['pct', 'config', str(vmid)], 'cleanup-guard')
    assert 'hostname: lifeos-daily-checkpoint-recovery' in cleanup_config and 'net0:' not in cleanup_config
    assert 'tags: disposable;lifeos-daily-checkpoint-recovery' in cleanup_config
    run(['pct', 'destroy', str(vmid), '--purge', '1'], 'remove-owned-test-guest')
    created = False
    volumes = json.loads(run(['pvesh', 'get', '/nodes/pve-tr1950x/storage/' + storage + '/content', '--output-format', 'json'], 'empty-storage'))
    assert not volumes
    run(['pvesm', 'remove', storage], 'remove-owned-storage')
    storage_created = False
    for directory in sorted(storage_path.rglob('*'), key=lambda path: len(path.parts), reverse=True):
        assert directory.is_dir() and not directory.is_symlink()
        directory.rmdir()
    storage_path.rmdir()
    after = json.loads(run(['pvesh', 'get', '/cluster/resources', '--type', 'vm', '--output-format', 'json'], 'final-inventory'))
    assert {str(row['vmid']): row['status'] for row in after} == originals
    protected = json.loads(run(['pvesh', 'get', '/nodes/pve-tr1950x/storage/PBS-01/content/' + archive,
        '--output-format', 'json'], 'final-protected-archive'))
    assert protected['protected'] is True
    receipt.update(backup_archive=archive, source_guest=102, restored_guest=vmid,
        network_disconnected=True, application_services_masked_before_boot=True,
        original_guest_states_preserved=True, source_guest_changed=False,
        disposable_guest_removed=True, owned_storage_removed=True, checkpoint_still_protected=True)
    (out / 'verification.json').write_text(json.dumps(receipt, indent=2) + '\n')
    success = True
finally:
    (out / 'process.done').write_text('0\n' if success else '1\n')
