# ABOUTME: Rechecks the recorded automatic evening run without starting or delivering any job.
# ABOUTME: Uses an isolated staged timestamp validator and exports only safe aggregate evidence.
from datetime import datetime
import hashlib
import importlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tomllib
import types
from zoneinfo import ZoneInfo

from dotenv import dotenv_values

profile = Path('/home/lifeos-hermes/.hermes')
folder = profile / 'operations/evening-acceptance-20261014'
initial = json.loads((folder / 'automatic-evening-verification.json').read_bytes())
assert initial['status'] == 'FAIL'
assert initial['error'] == 'The current Pulse state and cron delivery receipt must agree'
request = json.loads((folder / 'request.json').read_bytes())
configuration = json.loads((profile / 'lifeos-memory.json').read_bytes())
root = Path(configuration['root'])
assert str(root) == request['root']
user = root / 'LIFEOS/USER/CONFIG/PULSE.user.toml'
assert hashlib.sha256(user.read_bytes()).hexdigest() == request['before_sha256']
selected = [row for row in tomllib.loads(user.read_text())['job'] if row['name'] == 'life-morning-brief']
assert len(selected) == 1 and selected[0]['schedule'] == '0 7 * * *' and selected[0]['enabled']
start = datetime(2026, 10, 14, 18, 2, tzinfo=ZoneInfo('America/Toronto'))
end = datetime(2026, 10, 14, 18, 17, tzinfo=start.tzinfo)
assert datetime.now(start.tzinfo) >= end
assert request['window_start'] == start.isoformat() and request['window_end'] == end.isoformat()
assert request['evening_schedule'] == '2 18 14 10 *'
package = types.ModuleType('installed_evidence_only')
package.__path__ = [str(profile / 'plugins/lifeos-hook-bridge')]
sys.modules[package.__name__] = package
installed = importlib.import_module(package.__name__ + '.morning_observation')
api = importlib.import_module(package.__name__ + '.discord_audience')
staged_path = folder / 'staged-morning-observer.py'
spec = importlib.util.spec_from_file_location('staged_clock_validation', staged_path)
staged = importlib.util.module_from_spec(spec)
spec.loader.exec_module(staged)
environment = dict(os.environ, XDG_RUNTIME_DIR='/run/user/' + str(os.getuid()),
    DBUS_SESSION_BUS_ADDRESS='unix:path=/run/user/' + str(os.getuid()) + '/bus')


def run(arguments):
    return subprocess.run(arguments, capture_output=True, text=True, env=environment,
        timeout=30, check=True).stdout


version = json.loads(run([str(profile.parent / '.local/bin/hermes'), 'lifeos-version']))['active']
assert version['version'] == '0.4.3' and version['verification'] == 'verified' and not version['modified_files']
assert version['commit'] == 'a1abb579558edcf29f7cd04ecfd998995d48db54'
assert version['package_sha256'] == '1c7de7abc4014bfee83bc9bdcd4bfdb6c169526844d44491741d56645f400177'
journal = run(['journalctl', '--user', '-u', 'com.lifeos.pulse.service', '--since', start.isoformat(),
    '--until', end.isoformat(), '--output=json', '--no-pager',
    '--grep="msg"[[:space:]]*:[[:space:]]*"(Running: life-morning-brief|life-morning-brief completed)'])
state_path = root / 'LIFEOS/PULSE/state/state.json'
state = json.loads(state_path.read_bytes())['jobs']['life-morning-brief']
channel = '1558870196784205927'
bot = configuration['discord_channels'][channel]['bot']
assert bot == '1558867947152347198'
try:
    installed.morning_execution(journal, state, start, end, channel)
except ValueError as error:
    assert str(error) == initial['error']
else:
    raise AssertionError('The original observer failure must remain reproducible')
execution = staged.morning_execution(journal, state, start, end, channel)
delivery = installed.morning_delivery(api.DiscordAPI(dotenv_values(profile / '.env')['DISCORD_BOT_TOKEN']),
    channel, bot, start, end)
assert datetime.fromisoformat(execution['started_at']) <= datetime.fromisoformat(delivery['message_timestamp']) <= datetime.fromisoformat(execution['completed_at'])
services = {}
for name in ('com.lifeos.pulse.service', 'hermes-gateway.service', 'hermes-dashboard.service'):
    properties = dict(line.split('=', 1) for line in run(['systemctl', '--user', 'show', name,
        '--property=ActiveState,MainPID']).splitlines() if '=' in line)
    assert properties['ActiveState'] == 'active'
    services[name] = properties['ActiveState']
assert state == json.loads(state_path.read_bytes())['jobs']['life-morning-brief']
assert hashlib.sha256(user.read_bytes()).hexdigest() == request['before_sha256']
receipt = {'format': 3, 'status': 'PASS', 'observation_kind': 'owner-rescheduled-automatic-run',
    'version': version['version'], 'commit': version['commit'], 'package_sha256': version['package_sha256'],
    'window_start': start.isoformat(), 'window_end': end.isoformat(), 'automatic_execution_verified': True,
    'discord_delivery_verified': True, 'original_0700_wall_clock_observed': False,
    'scheduler': {key: value for key, value in request.items() if key != 'root'},
    'execution': execution, 'discord': {**delivery, 'bot_id': bot},
    'initial_installed_observer': initial, 'verification_method': 'isolated-staged-validator-replay',
    'validator_sha256': hashlib.sha256(staged_path.read_bytes()).hexdigest(),
    'qualified_installed_program_changed': False, 'job_manually_run': False,
    'services': services, 'normal_schedule_restored': True,
    'all_original_configuration_bytes_restored': True}
(folder / 'automatic-rescheduled-verification.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps(receipt, indent=2))
