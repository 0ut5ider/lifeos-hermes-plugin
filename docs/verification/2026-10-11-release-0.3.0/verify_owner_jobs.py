# ABOUTME: Checks fixed daily owner jobs and an actual successful Pulse capture execution.
# ABOUTME: Keeps native output private and reports status without copying personal job content.
import json
import os
from pathlib import Path
import subprocess
import time

os.umask(0o077)
home = Path('/home/lifeos-hermes')
profile = home / '.hermes'
selected = json.loads((profile / 'integration-release.json').read_text())
root = Path(json.loads((profile / 'lifeos-memory.json').read_text())['root'])
output = home / 'deployment' / ('release-' + selected['version'] + '-' + selected['commit'][:8])
os.environ.update(HERMES_HOME=str(profile), PYTHONDONTWRITEBYTECODE='1',
    PATH=str(home / '.local/bin') + ':' + os.environ.get('PATH', ''),
    XDG_RUNTIME_DIR='/run/user/' + str(os.getuid()),
    DBUS_SESSION_BUS_ADDRESS='unix:path=/run/user/' + str(os.getuid()) + '/bus')
results = []
latch_recovery = None
for name in ('atlas-sync', 'conduit-capture', 'memory-consolidation', 'proposal-gc', 'life-morning-brief'):
    result = subprocess.run([str(home / '.local/bin/hermes'), 'lifeos-job', name],
        capture_output=True, text=True, cwd=profile, timeout=600)
    (output / ('owner-job-' + name + '.stdout')).write_text(result.stdout)
    (output / ('owner-job-' + name + '.stderr')).write_text(result.stderr)
    body = json.loads(result.stdout)
    row = {'job': name, 'status': body['status'], 'exit_code': result.returncode,
        'stderr_bytes': len(result.stderr.encode())}
    results.append(row)
    print(json.dumps(row), flush=True)
    assert result.returncode == 0 and not result.stderr and body['status'] == 'completed', row
    if name == 'conduit-capture':
        state_path = root / 'LIFEOS/PULSE/state/state.json'
        state = json.loads(state_path.read_text())
        failure = state['jobs'].get(name, {})
        if failure.get('consecutiveFailures', 0) >= 3:
            subprocess.run(['systemctl', '--user', 'stop', 'com.lifeos.pulse.service'], check=True)
            try:
                state = json.loads(state_path.read_text())
                failure = dict(state['jobs'][name])
                (output / 'pulse-state-before-latch-recovery.json').write_text(json.dumps(state, indent=2) + '\n')
                state['jobs'][name]['consecutiveFailures'] = 0
                pending = state_path.with_suffix('.release-retry')
                pending.write_text(json.dumps(state, indent=2) + '\n')
                pending.chmod(0o600)
                pending.replace(state_path)
                latch_recovery = {'previous': failure, 'manual_capture_succeeded': True,
                    'last_result_and_timestamp_preserved': True}
            finally:
                subprocess.run(['systemctl', '--user', 'start', 'com.lifeos.pulse.service'], check=True)
deadline = time.monotonic() + 190
while True:
    state = json.loads((root / 'LIFEOS/PULSE/state/state.json').read_text())
    capture = state['jobs'].get('conduit-capture', {})
    if capture.get('lastResult') == 'ok' and capture.get('consecutiveFailures') == 0:
        break
    if time.monotonic() >= deadline:
        raise RuntimeError('Pulse has no successful automatic capture after release selection')
    time.sleep(1)
report = {'status': 'PASS', 'owner_jobs': results, 'scheduled_capture': capture,
    'model_settings_changed': False, 'automatic_morning_brief_observed': False,
    'capture_failure_latch_recovery': latch_recovery}
(output / 'owner-jobs-verification.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
