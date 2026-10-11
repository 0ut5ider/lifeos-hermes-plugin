# ABOUTME: Verifies actual morning-brief delivery and refusal of a stale owner policy.
# ABOUTME: Reads only synthetic acceptance messages and retains credential-free results.
import json
import os
from pathlib import Path
import subprocess
import sys
import urllib.request

from dotenv import dotenv_values

home = Path('/home/lifeos-hermes')
evidence = home / 'deployment/2026-10-11'
profile = home / '.hermes'
os.umask(0o077)
environment = dict(os.environ, **json.loads((evidence / 'environment.json').read_text()))
token = dotenv_values(profile / '.env')['DISCORD_BOT_TOKEN']
program = evidence / 'deliver_morning.py'
assert program.is_file(), 'The staged morning delivery program is missing'


def messages():
    request = urllib.request.Request(
        'https://discord.com/api/v10/channels/1558870196784205927/messages?limit=100',
        headers={'Authorization': 'Bot ' + token, 'User-Agent': 'LifeOS-Deployment/1.0'})
    with urllib.request.urlopen(request, timeout=15) as response:
        return json.load(response)


before = {row['id'] for row in messages()}
refused = subprocess.run([sys.executable, '-B', str(program)],
    env=dict(environment, LIFEOS_MEMORY_CONFIGURATION_REVISION='0' * 64),
    capture_output=True, text=True, timeout=120)
assert refused.returncode != 0, 'A stale owner configuration must refuse delivery'
assert {row['id'] for row in messages()} == before, 'Refused generation sends no message'
accepted = subprocess.run([sys.executable, '-B', str(program)], env=environment,
    capture_output=True, text=True, timeout=660)
(evidence / 'morning-delivery-process.log').write_text(accepted.stdout + accepted.stderr)
assert accepted.returncode == 0 and not accepted.stderr
receipt = json.loads(accepted.stdout)
assert receipt['status'] == 'delivered'
delivered = [row for row in messages() if row['id'] not in before
    and row['author']['id'] == '1558867947152347198'
    and row['content'].startswith('LifeOS morning brief\n\nGood morning.')]
assert len(delivered) == 1, 'The actual synthetic morning brief must arrive exactly once'
report = {'status': 'PASS', 'stale_configuration_refused': True, 'refused_delivery_count': 0,
    'message_id': delivered[0]['id'], 'channel_id': delivered[0]['channel_id'],
    'actual_morning_brief_delivered': True, 'active_schedule_changed': False}
(evidence / 'morning-delivery-verification.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
