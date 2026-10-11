# ABOUTME: Checks the actual daily owner commands and two-minute Pulse capture schedule.
# ABOUTME: Retains command results on disk without changing the selected model or schedule.
import json
import os
from pathlib import Path
import subprocess
import time
import traceback


home = Path('/home/lifeos-hermes')
evidence = home / 'deployment/2026-10-11'
os.umask(0o077)
environment = json.loads((evidence / 'environment.json').read_text())
os.environ.update(environment, XDG_RUNTIME_DIR='/run/user/1000',
    DBUS_SESSION_BUS_ADDRESS='unix:path=/run/user/1000/bus')
profile = Path(environment['HERMES_HOME'])
root = Path(json.loads((profile / 'lifeos-memory.json').read_text())['root'])


def main():
    results = []
    for name in ('atlas-sync', 'conduit-capture', 'memory-consolidation', 'proposal-gc', 'life-morning-brief'):
        result = subprocess.run([str(home / '.local/bin/hermes'), 'lifeos-job', name],
            cwd=profile, capture_output=True, text=True, timeout=600)
        (evidence / ('daily-job-' + name + '.log')).write_text(result.stdout + result.stderr)
        assert result.returncode == 0 and not result.stderr, (name, result.returncode)
        body = json.loads(result.stdout)
        assert body['status'] == 'completed' and body['job'] == name
        results.append({'job': name, 'status': body['status']})
    state_path = root / 'LIFEOS/PULSE/state/state.json'
    deadline = time.monotonic() + 190
    while True:
        state = json.loads(state_path.read_text()) if state_path.exists() else {}
        capture = state.get('jobs', {}).get('conduit-capture', {})
        if capture.get('lastRun', 0) and capture.get('lastResult') == 'ok':
            break
        if time.monotonic() >= deadline:
            raise RuntimeError('The daily two-minute capture schedule has no successful execution')
        time.sleep(1)
    for path in (root / 'LIFEOS/USER/CONDUIT/events').glob('*.jsonl'):
        assert path.stat().st_mode & 0o777 == 0o600
    state = subprocess.check_output(['systemctl', '--user', 'show', 'com.lifeos.pulse.service',
        '--property=ActiveState,NRestarts,MainPID'], text=True)
    properties = dict(line.split('=', 1) for line in state.splitlines() if '=' in line)
    assert properties['ActiveState'] == 'active' and properties['NRestarts'] == '0'
    report = {'status': 'PASS', 'owner_jobs': results, 'scheduled_capture': capture,
        'pulse': properties, 'timezone': 'America/Toronto', 'model_routes_changed': False,
        'morning_brief_discord_delivery_verified': False}
    (evidence / 'daily-jobs-verification.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2), flush=True)


try:
    main()
except BaseException:
    traceback.print_exc()
    (evidence / 'daily-jobs-verification.done').write_text('1\n')
    raise
else:
    (evidence / 'daily-jobs-verification.done').write_text('0\n')
