# ABOUTME: Injects one measured process exit into a disposable installed software removal.
# ABOUTME: Signals only the exact reviewed workflow MainPID after all active LifeOS plugins disappear.
import argparse
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import time

parser = argparse.ArgumentParser()
parser.add_argument('identifier')
parser.add_argument('--label', required=True)
args = parser.parse_args()
assert os.getuid() == 0
assert re.fullmatch('[0-9a-f]{32}', args.identifier)
assert re.fullmatch('[a-z0-9-]+', args.label)
os.umask(0o077)
home = Path('/home/lifeos-hermes')
profile = home / '.hermes'
job = profile / '.lifeos-portability' / args.identifier
assert (job / 'review.json').is_file()
review = json.loads((job / 'review.json').read_bytes())
assert review['state'] == 'ready'
output = home / 'install-input/fault-injection' / args.label
output.mkdir(parents=True, mode=0o700)
environment = dict(os.environ, HOME=str(home), XDG_RUNTIME_DIR='/run/user/1000',
    DBUS_SESSION_BUS_ADDRESS='unix:path=/run/user/1000/bus')
receipt = {'status': 'FAIL', 'workflow': args.identifier, 'daily_changed': False,
    'signal_sent': False, 'fault_injection_only': True}
started = time.monotonic()
try:
    while time.monotonic() - started < 600:
        state = json.loads((job / 'status.json').read_bytes())['state']
        publication = job / 'removal/operation.json'
        phase = json.loads(publication.read_bytes())['state'] if publication.is_file() else None
        absent = all(not os.path.lexists(profile / 'plugins' / name)
            for name in ('lifeos', 'lifeos-hook-bridge', 'lifeos-release-manager'))
        if state == 'applying' and absent and phase in ('publishing', 'restarting', 'verification_required'):
            unit = json.loads((job / 'launch.json').read_bytes())['unit']
            assert re.fullmatch('lifeos-memory-' + args.identifier + '-[0-9a-f]{8}', unit)
            command = ['runuser', '-u', 'lifeos-hermes', '--', 'systemctl', '--user', 'show', unit,
                '--property=MainPID', '--property=ControlGroup', '--property=FragmentPath', '--property=ActiveState']
            result = subprocess.run(command, env=environment, capture_output=True, text=True, timeout=15, check=True)
            metadata = dict(line.split('=', 1) for line in result.stdout.splitlines() if '=' in line)
            pid = int(metadata['MainPID'])
            assert pid > 1 and metadata['ActiveState'] == 'active'
            assert metadata['FragmentPath'] == '/run/user/1000/systemd/transient/' + unit + '.service'
            process = Path('/proc') / str(pid)
            assert process.stat().st_uid == 1000
            descriptor = os.pidfd_open(pid)
            try:
                arguments = (process / 'cmdline').read_bytes().split(b'\0')
                assert str(job).encode() in arguments and b'apply' in arguments
                groups = {line.removeprefix('0::') for line in (process / 'cgroup').read_text().splitlines() if line.startswith('0::')}
                assert groups == {metadata['ControlGroup']}
                assert json.loads((job / 'launch.json').read_bytes())['unit'] == unit
                assert json.loads((job / 'status.json').read_bytes())['state'] == 'applying'
                receipt.update(unit=unit, pid=pid, publication_phase=phase, all_active_plugins_absent=True,
                    exact_main_pid_bound=True, pidfd_used=True)
                (output / 'signal-intent.json').write_text(json.dumps(receipt, indent=2) + '\n')
                signal.pidfd_send_signal(descriptor, signal.SIGKILL)
                receipt.update(status='PASS', signal_sent=True, signal='SIGKILL')
                break
            finally:
                os.close(descriptor)
        if state in ('verified', 'rolled_back', 'cancelled', 'interrupted'):
            raise RuntimeError('The workflow reaches a terminal state before the selected fault boundary')
        time.sleep(0.05)
    if not receipt['signal_sent']:
        raise TimeoutError('The selected installed removal boundary does not occur')
except Exception as error:
    receipt.update(error_type=type(error).__name__, reason=str(error))
finally:
    receipt['elapsed_seconds'] = time.monotonic() - started
    (output / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    (output / 'observation.done').write_text('0\n' if receipt['status'] == 'PASS' else '1\n')
print(json.dumps(receipt))
raise SystemExit(0 if receipt['status'] == 'PASS' else 1)
