# ABOUTME: Verifies one actual private-model reply after the complete integration update.
# ABOUTME: Keeps conversation output private and exports only the expected marker and process proof.
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time

parser = argparse.ArgumentParser()
parser.add_argument('server', choices=('development', 'daily'))
args = parser.parse_args()
if sys.flags.optimize:
    raise RuntimeError('Model verification requires assertions')
home = Path('/home/lifeos-hermes')
assert Path.home() == home
assert os.getuid() == (1008 if args.server == 'development' else 1000)
os.umask(0o077)
profile = home / '.hermes'
stage = home / 'releases/qualification-0.6.0' / ('model-' + args.server)
stage.mkdir(mode=0o700)
configuration = json.loads((profile / 'lifeos-memory.json').read_bytes())
installed = Path(configuration['root'])
environment = {'HOME': str(installed.parent), 'HERMES_HOME': str(profile),
    'PATH': str(home / '.local/bin') + ':/usr/local/bin:/usr/bin:/bin',
    'LANG': 'C.UTF-8', 'TZ': 'America/Toronto',
    'LIFEOS_DIR': str(installed / 'LIFEOS'), 'LIFEOS_HOOK_SETTINGS': str(installed / 'settings.json'),
    'LIFEOS_NOTIFICATION_CHANNEL': 'headless', 'BUN_CONFIG_NO_AUTO_INSTALL': '1',
    'PYTHONDONTWRITEBYTECODE': '1'}
marker = 'D' + ('252' if args.server == 'development' else '253') + '-060-UPDATE-PASS'
query = stage / 'query.txt'
query.write_text('Reply exactly ' + marker + '. Do not call any tool.\n')
receipt = {'status': 'FAIL', 'server': args.server, 'personal_data_imported_or_reset': False,
    'new_memory_fact_requested': False, 'discord_message_requested': False}
started = time.monotonic()
try:
    with (stage / 'stdout.jsonl').open('wb') as stdout, (stage / 'stderr.txt').open('wb') as stderr:
        result = subprocess.run([str(home / '.local/bin/hermes'), 'chat', '--query-file', str(query),
            '--oneshot', '--format', 'stream-json', '--max-turns', '3', '--run-budget', '120'],
            cwd=profile, env=environment, stdout=stdout, stderr=stderr, timeout=180)
    events = []
    for line in (stage / 'stdout.jsonl').read_text().splitlines():
        try:
            value = json.loads(line)
        except ValueError:
            continue
        if isinstance(value, dict):
            events.append(value)
    final = next((row for row in reversed(events) if row.get('type') == 'result'), {})
    tools = [row.get('name') for row in events if row.get('type') == 'tool_use']
    assert result.returncode == 0 and final.get('exit_code') == 0
    assert not tools and final.get('tokens', {}).get('output', 0) > 0
    assert marker in final.get('text', '') and final.get('session_id')
    receipt.update(status='PASS', actual_model_reply=True, expected_marker_verified=True,
        session=final['session_id'], tool_names=tools, process_exit_code=result.returncode)
except Exception as error:
    receipt['error_type'] = type(error).__name__
finally:
    receipt['elapsed_seconds'] = time.monotonic() - started
    (stage / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    (stage / 'process.done').write_text('0\n' if receipt['status'] == 'PASS' else '1\n')
print(json.dumps(receipt))
raise SystemExit(0 if receipt['status'] == 'PASS' else 1)
