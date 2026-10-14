# ABOUTME: Repeats verification in the exact retained disconnected checkpoint guest after correcting its test launcher.
# ABOUTME: Preserves the failed observation, exports only safe receipts, and removes only the owned test resources.
import json
import os
from pathlib import Path
import subprocess
import time

os.umask(0o077)
folder = Path('/root/lifeos-daily-checkpoint-restore-20261014')
prior = folder / 'observation'
out = folder / 'verification-retry-1'
assert not out.exists()
out.mkdir(mode=0o700)
archive = 'PBS-01:backup/ct/102/2026-10-14T16:15:12Z'
storage = 'lifeos-daily-restore'
storage_path = Path('/var/lib/vz/lifeos-daily-restore')
python = '/home/lifeos-hermes/.hermes/.lifeos-releases/52af3122ef614ac49ef55b692e392f0c/python-environment/bin/python'
operations = []
success = False


def run(command, label, timeout=1800):
    started = time.monotonic()
    result = subprocess.run(command, capture_output=True, text=True, timeout=timeout)
    (out / (label + '.stdout')).write_text(result.stdout)
    (out / (label + '.stderr')).write_text(result.stderr)
    operations.append({'action': label, 'command': command, 'exit_code': result.returncode,
        'elapsed_seconds': round(time.monotonic() - started, 3)})
    (out / 'operations.json').write_text(json.dumps(operations, indent=2) + '\n')
    assert result.returncode == 0, label + ' fails; inspect private host evidence'
    print(json.dumps({'action': label, 'exit_code': result.returncode}), flush=True)
    return result.stdout


try:
    assert (prior / 'process.done').read_text().strip() == '1'
    before = json.loads((prior / 'inventory.stdout').read_bytes())
    original_states = {str(row['vmid']): row['status'] for row in before}
    restored = next(row for row in json.loads((prior / 'operations.json').read_bytes()) if row['action'] == 'restore-exact-checkpoint')
    assert restored['exit_code'] == 0 and restored['command'] == ['pct', 'restore', '110', archive,
        '--storage', storage, '--rootfs', storage + ':80', '--unprivileged', '1', '--onboot', '0',
        '--hostname', 'lifeos-daily-checkpoint-recovery']
    config = run(['pct', 'config', '110'], 'retained-guest-guard')
    assert 'hostname: lifeos-daily-checkpoint-recovery' in config and 'tags: disposable;lifeos-daily-checkpoint-recovery' in config
    assert not any(line.startswith('net') and ':' in line for line in config.splitlines()) and 'onboot: 0' in config
    assert 'rootfs: ' + storage + ':' in config
    run(['pct', 'push', '110', str(folder / 'verify_daily_checkpoint.py'),
        '/home/lifeos-hermes/checkpoint-verification-20261014/verify_daily_checkpoint.py', '--user', '1000', '--group', '1000', '--perms', '0600'], 'replace-owned-test-verifier')
    receipt = json.loads(run(['pct', 'exec', '110', '--', 'runuser', '-u', 'lifeos-hermes', '--',
        python, '-B', '/home/lifeos-hermes/checkpoint-verification-20261014/verify_daily_checkpoint.py'], 'verify-current-daily'))
    assert receipt['status'] == 'PASS' and receipt['version'] == '0.4.3' and receipt['sealed_program_targets'] == 9
    run(['pct', 'shutdown', '110', '--timeout', '90'], 'shutdown-test-guest')
    cleanup = run(['pct', 'config', '110'], 'cleanup-guard')
    assert cleanup == config
    run(['pct', 'destroy', '110', '--purge', '1'], 'remove-owned-test-guest')
    assert not json.loads(run(['pvesh', 'get', '/nodes/pve-tr1950x/storage/' + storage + '/content', '--output-format', 'json'], 'empty-storage'))
    run(['pvesm', 'remove', storage], 'remove-owned-storage')
    for directory in sorted(storage_path.rglob('*'), key=lambda path: len(path.parts), reverse=True):
        assert directory.is_dir() and not directory.is_symlink()
        directory.rmdir()
    storage_path.rmdir()
    after = json.loads(run(['pvesh', 'get', '/cluster/resources', '--type', 'vm', '--output-format', 'json'], 'final-inventory'))
    assert {str(row['vmid']): row['status'] for row in after} == original_states
    protected = json.loads(run(['pvesh', 'get', '/nodes/pve-tr1950x/storage/PBS-01/content/' + archive,
        '--output-format', 'json'], 'final-protected-archive'))
    assert protected['protected'] is True
    receipt.update(backup_archive=archive, source_guest=102, restored_guest=110,
        network_disconnected=True, application_services_masked_before_boot=True,
        original_guest_states_preserved=True, source_guest_changed=False, disposable_guest_removed=True,
        owned_storage_removed=True, checkpoint_still_protected=True,
        historical_failed_probe_preserved=True, restoration_repeated=False)
    (out / 'verification.json').write_text(json.dumps(receipt, indent=2) + '\n')
    success = True
finally:
    (out / 'process.done').write_text('0\n' if success else '1\n')
