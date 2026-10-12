# ABOUTME: Verifies the actual scheduled morning execution and its fixed-channel Discord delivery.
# ABOUTME: Exports scheduler timestamps and message identifiers without retaining personal narration.
import argparse
from datetime import datetime, timedelta
import json
import os
from pathlib import Path
import subprocess
import urllib.request
from zoneinfo import ZoneInfo
from dotenv import dotenv_values

parser = argparse.ArgumentParser()
parser.add_argument('--date', required=True)
args = parser.parse_args()
os.umask(0o077)
home = Path('/home/lifeos-hermes')
profile = home / '.hermes'
os.environ.update(XDG_RUNTIME_DIR='/run/user/' + str(os.getuid()),
    DBUS_SESSION_BUS_ADDRESS='unix:path=/run/user/' + str(os.getuid()) + '/bus')
start = datetime.fromisoformat(args.date + 'T07:00:00').replace(tzinfo=ZoneInfo('America/Toronto'))
end = start + timedelta(minutes=15)
assert datetime.now(start.tzinfo) >= end, 'The automatic observation window has not finished'
config = json.loads((profile / 'lifeos-memory.json').read_text())
root = Path(config['root'])
state = json.loads((root / 'LIFEOS/PULSE/state/state.json').read_text())['jobs'].get('life-morning-brief')
assert state and state['lastResult'] == 'ok', 'The scheduler has no successful morning execution'
completed = datetime.fromtimestamp(state['lastRun'] / 1000, start.tzinfo)
assert start <= completed <= end, 'The last execution is outside the automatic observation window'
journal = subprocess.check_output(['journalctl', '--user', '-u', 'com.lifeos.pulse.service',
    '--since', start.isoformat(), '--until', end.isoformat(), '--output=json', '--no-pager'], text=True)
events = []
for line in journal.splitlines():
    try:
        event = json.loads(json.loads(line)['MESSAGE'])
    except (ValueError, KeyError):
        continue
    if event.get('subsystem') == 'cron' and event.get('msg', '').startswith('life-morning-brief completed'):
        events.append(event)
assert len(events) == 1, 'The scheduler must complete the morning job exactly once'
receipt = json.loads(events[0]['outputPreview'])
assert receipt['status'] == 'delivered' and receipt['channel_id'] == '1558870196784205927'
token = dotenv_values(profile / '.env')['DISCORD_BOT_TOKEN']
request = urllib.request.Request('https://discord.com/api/v10/channels/1558870196784205927/messages?limit=100',
    headers={'Authorization': 'Bot ' + token, 'User-Agent': 'LifeOS-Release-Verification/1.0'})
with urllib.request.urlopen(request, timeout=20) as response:
    messages = json.load(response)
matches = [row for row in messages if row['author']['id'] == '1558867947152347198'
    and row['content'].startswith('LifeOS morning brief\n\n')
    and start <= datetime.fromisoformat(row['timestamp']) <= end]
assert len(matches) == 1, 'Discord must contain exactly one morning brief in the observation window'
release = json.loads((profile / 'integration-release.json').read_text())
report = {'status': 'PASS', 'schedule': '0 7 * * *', 'timezone': 'America/Toronto',
    'automatic_execution_verified': True, 'completed_at': completed.isoformat(),
    'discord_delivery_verified': True, 'channel_id': matches[0]['channel_id'],
    'message_id': matches[0]['id'], 'message_timestamp': matches[0]['timestamp'],
    'version': release['version'], 'commit': release['commit'], 'manual_trigger_used': False}
directory = home / 'deployment' / ('release-' + release['version'] + '-' + release['commit'][:8])
(directory / 'automatic-morning-verification.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
