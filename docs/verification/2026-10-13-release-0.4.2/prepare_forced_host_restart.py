# ABOUTME: Stops each admitted guest gracefully and commits the ZFS pool before a forced restart.
# ABOUTME: Saves admission evidence without issuing the restart or using the blocked global sync.
import json
import os
from pathlib import Path
import subprocess
import time

os.umask(0o077)
output = Path('/root/lifeos-release-0.4.2/forced-host-restart')
output.mkdir(mode=0o700, parents=True, exist_ok=True)
rows = []


def run(command, timeout=30):
    started = time.monotonic()
    result = subprocess.run(command, capture_output=True, text=True, timeout=timeout)
    row = {'command': command, 'exit_code': result.returncode,
        'stdout': result.stdout, 'stderr': result.stderr,
        'elapsed_seconds': round(time.monotonic() - started, 3)}
    rows.append(row)
    (output / 'operations.json').write_text(json.dumps(rows, indent=2) + '\n')
    assert result.returncode == 0, 'The guest shutdown or pool commit does not complete'
    return result.stdout.strip()


try:
    boot_id = Path('/proc/sys/kernel/random/boot_id').read_text().strip()
    (output / 'original-boot-id').write_text(boot_id + '\n')
    for guest, command in [(801, 'qm'), (100, 'pct'), (101, 'pct'), (102, 'pct'), (108, 'pct')]:
        state = run([command, 'status', str(guest)])
        if state != 'status: stopped':
            run([command, 'shutdown', str(guest), '--timeout', '180' if command == 'qm' else '90'], 210)
        assert run([command, 'status', str(guest)]) == 'status: stopped'
    run(['zpool', 'sync', 'rpool'], 60)
    assert run(['zpool', 'status', '-x', 'rpool']) == "pool 'rpool' is healthy"
    receipt = {'forced_host_restart_explicitly_approved': True,
        'original_boot_id': boot_id, 'original_running_guests': [100, 101, 102, 801],
        'additional_disposable_guest': 108, 'all_admitted_guests_stopped_gracefully': True,
        'forced_guest_stop': False, 'zpool_sync_rpool_complete': True,
        'global_sync_bypassed_due_to_observed_kernel_wait': True,
        'pool_healthy': True, 'forced_restart_issued': False}
    (output / 'admission.json').write_text(json.dumps(receipt, indent=2) + '\n')
    (output / 'process.done').write_text('0\n')
except BaseException:
    (output / 'process.done').write_text('1\n')
    raise
