# ABOUTME: Removes disposable restore guests after their recorded verification passes.
# ABOUTME: Restarts the daily dashboard and checks the installed release after a guest reboot.
import atexit
import json
import os
from pathlib import Path
import subprocess
import sys
import time

os.umask(0o077)
here = Path('/root/lifeos-daily-install/recovery')
exit_state = {'code': '1\n'}
atexit.register(lambda: (here / '.final.done').write_text(exit_state['code']))
result = json.loads((here / 'result.json').read_text())
assert result['status'] == 'PASS'
assert [item['case'] for item in result['cases']] == ['baseline', 'interrupted', 'later-edit']
operations = []


def run(args, label, timeout=300):
    completed = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
    (here / (label + '.stdout')).write_text(completed.stdout)
    (here / (label + '.stderr')).write_text(completed.stderr)
    operations.append({'label': label, 'exit_code': completed.returncode})
    assert completed.returncode == 0, (label, completed.stdout[-2000:], completed.stderr[-2000:])
    return completed.stdout


def user(args, label):
    return run(['pct', 'exec', '102', '--', 'runuser', '-u', 'lifeos-hermes', '--', 'env',
        'XDG_RUNTIME_DIR=/run/user/1000', 'DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus',
        *args], label)


assert sys.argv[1:] in ([], ['--after-cleanup'])
for receipt in result['cases']:
    vmid = str(receipt['restored_guest'])
    assert vmid in ('103', '104', '105') and receipt['status'] == 'PASS'
    if sys.argv[1:]:
        assert (here / ('cleanup-destroy-' + vmid + '.stdout')).exists()
        assert not (Path('/etc/pve/lxc') / (vmid + '.conf')).exists()
        continue
    config = run(['pct', 'config', vmid], 'cleanup-config-' + vmid)
    assert 'hostname: lifeos-recovery-' + receipt['case'] in config
    assert 'net0:' not in config and 'onboot: 0' in config
    assert 'disposable' in config and 'lifeos-recovery' in config
    assert 'status: stopped' in run(['pct', 'status', vmid], 'cleanup-state-' + vmid)
    run(['pct', 'destroy', vmid, '--purge', '1'], 'cleanup-destroy-' + vmid)

user(['systemctl', '--user', 'enable', '--now', 'hermes-dashboard.service'], 'enable-dashboard')
run(['pct', 'shutdown', '102', '--timeout', '90'], 'final-daily-shutdown')
run(['pct', 'start', '102'], 'final-daily-start')
deadline = time.monotonic() + 30
while time.monotonic() < deadline:
    probe = subprocess.run(['pct', 'exec', '102', '--', 'test', '-S', '/run/user/1000/bus'],
        capture_output=True, timeout=10)
    if probe.returncode == 0:
        break
    time.sleep(1)
services = {}
for name in ('hermes-dashboard.service', 'hermes-gateway.service', 'com.lifeos.pulse.service'):
    output = user(['systemctl', '--user', 'show', '-p', 'ActiveState', '-p', 'UnitFileState', name],
        'final-' + name)
    services[name] = dict(line.split('=', 1) for line in output.splitlines() if '=' in line)
assert services['hermes-dashboard.service'] == {'ActiveState': 'active', 'UnitFileState': 'enabled'}
for name in ('hermes-gateway.service', 'com.lifeos.pulse.service'):
    assert services[name] == {'ActiveState': 'inactive', 'UnitFileState': 'disabled'}
addresses = json.loads(run(['pct', 'exec', '102', '--', 'ip', '-json', 'address'], 'final-addresses'))
assert any(item.get('local') == '192.168.8.253' for row in addresses for item in row['addr_info'])
python = '/home/lifeos-hermes/.hermes/installs/995dd15ff6e15ed0/environments/65f4231f26e94a2d989e89eb96b98808/venv/bin/python'
# A running systemd process can precede the native dashboard HTTP listener.
deadline = time.monotonic() + 60
while time.monotonic() < deadline:
    probe = subprocess.run(['pct', 'exec', '102', '--', 'curl', '--silent', '--output', '/dev/null',
        '--write-out', '%{http_code}', 'http://127.0.0.1:18819/api/plugins/lifeos-hook-bridge/memory'],
        capture_output=True, text=True, timeout=10)
    if probe.returncode == 0 and probe.stdout == '401':
        break
    time.sleep(1)
else:
    raise RuntimeError('Dashboard does not reach the expected anonymous HTTP 401 state')
user([python, '-B', '/home/lifeos-hermes/install-input/verify_installation.py'], 'final-installation-check')
job = json.loads(run(['pvesh', 'get', '/cluster/backup/lifeos-daily-offserver',
    '--output-format', 'json'], 'final-backup-job'))
assert job['enabled'] == 1 and job['vmid'] == '102' and job['storage'] == 'PBS-01'
assert job['mode'] == 'stop' and job['schedule'] == '01:00'
assert job['prune-backups'] == {'keep-daily': '7', 'keep-weekly': '4', 'keep-monthly': '3'}
report = {'status': 'PASS', 'address': '192.168.8.253', 'guest': 102,
    'guest_reboot_verified': True, 'services': services, 'backup_job': job,
    'disposable_restore_guests_removed': [103, 104, 105],
    'development_guest_preserved': 101, 'discord_cutover_pending': True,
    'ownership_enabled': False, 'sharing_enabled': False, 'active_facts': 0,
    'operations': operations}
(here / 'final-state.json').write_text(json.dumps(report, indent=2) + '\n')
exit_state['code'] = '0\n'
print(json.dumps(report, indent=2))
