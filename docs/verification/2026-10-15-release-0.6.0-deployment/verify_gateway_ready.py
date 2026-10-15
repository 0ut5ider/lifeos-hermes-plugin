# ABOUTME: Verifies the updated gateway through its actual process, fresh heartbeat, and Discord connection.
# ABOUTME: Reports PID-file validation separately and exports no conversation content or credentials.
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time

parser = argparse.ArgumentParser()
parser.add_argument('server', choices=('development', 'daily'))
parser.add_argument('operation')
args = parser.parse_args()
if sys.flags.optimize or re.fullmatch('[0-9a-f]{32}', args.operation) is None:
    raise RuntimeError('Use assertions and the exact applied operation')
home = Path('/home/lifeos-hermes')
profile = home / '.hermes'
assert Path.home() == home and os.getuid() == (1008 if args.server == 'development' else 1000)
os.umask(0o077)
os.environ.update(HERMES_HOME=str(profile), XDG_RUNTIME_DIR='/run/user/' + str(os.getuid()),
    DBUS_SESSION_BUS_ADDRESS='unix:path=/run/user/' + str(os.getuid()) + '/bus')
sys.path.insert(0, str(profile / '.lifeos-releases' / args.operation / 'hermes'))
from gateway.status import read_runtime_status, runtime_status_heartbeat_age_s, runtime_status_pid_is_live, get_running_pid

receipt = {'status': 'FAIL', 'server': args.server, 'operation': args.operation,
    'conversation_content_exported': False, 'discord_message_sent': False}
try:
    identity = json.loads((profile / 'integration-release.json').read_bytes())
    assert identity['version'] == '0.6.0' and identity['commit'] == 'c86b5887b899ca779afbb217c33843e1ee12c381'
    assert identity['package_sha256'] == '9e2a1939efbaccc94abaa879b265f1af447f9bdfe0b82aecc76f872f15fa9fb7'
    for attempt in range(60):
        state = read_runtime_status() or {}
        observed = subprocess.run(['systemctl', '--user', 'show', 'hermes-gateway.service',
            '--property=MainPID,ActiveState,SubState', '--no-pager'], capture_output=True, text=True, check=True)
        assert not observed.stderr
        unit = dict(line.split('=', 1) for line in observed.stdout.splitlines())
        age = runtime_status_heartbeat_age_s(state)
        discord = state.get('platforms', {}).get('discord', {}).get('state')
        ready = (state.get('gateway_state') == 'running' and runtime_status_pid_is_live(state)
            and type(age) is int and age <= 120 and discord == 'connected'
            and unit['ActiveState'] == 'active' and unit['SubState'] == 'running'
            and int(unit['MainPID']) == state.get('pid'))
        if ready:
            break
        time.sleep(2)
    assert ready
    request = json.loads((profile / '.lifeos-releases' / args.operation / 'request.json').read_bytes())
    assert (Path('/proc') / str(state['pid']) / 'exe').resolve() == Path(request['runtime']['python']).resolve()
    assert args.operation.encode() in (Path('/proc') / str(state['pid']) / 'cmdline').read_bytes()
    receipt.update(status='PASS', version=identity['version'], program_commit=identity['commit'],
        gateway_state=state['gateway_state'], runtime_pid=state['pid'],
        systemd_main_pid_matches=True, native_runtime_pid_live=True, selected_runtime_process_verified=True,
        heartbeat_age_seconds=age, discord_state=discord,
        strict_pidfile_running_pid=get_running_pid(cleanup_stale=False))
except Exception as error:
    receipt['error_type'] = type(error).__name__
folder = home / 'releases/qualification-0.6.0'
with (folder / ('gateway-' + args.server + '.json')).open('x') as handle:
    json.dump(receipt, handle, indent=2)
    handle.write('\n')
print(json.dumps(receipt))
raise SystemExit(0 if receipt['status'] == 'PASS' else 1)
