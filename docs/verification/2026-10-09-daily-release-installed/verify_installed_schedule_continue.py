# ABOUTME: Verifies the installed native capture schedule consumes actual Hermes hook activity.
# ABOUTME: Records fixed owner jobs and service restart without changing daily schedules or model routes.
import importlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

stage = Path('/home/lifeos-hermes/migration/2026-10-09/daily-text-581d76a7')
prepared = json.loads((stage / 'applications-prepared.json').read_text())
profile, root = Path(prepared['profile']), Path(prepared['installed'])
os.umask(0o077)
sys.path[:0] = [str(profile / 'plugins'), str(stage / 'package/hermes')]
def module(name):
    return importlib.import_module('lifeos-hook-bridge.' + name)
environment = {'HOME': str(root.parent), 'HERMES_HOME': str(profile),
    'PATH': str(stage / 'bin') + ':/home/lifeos-hermes/.local/bin:/usr/bin:/bin',
    'PYTHONPATH': str(stage / 'package/hermes'), 'LANG': 'C.UTF-8', 'TZ': 'America/Toronto',
    'LIFEOS_DIR': str(root / 'LIFEOS'), 'LIFEOS_HOOK_SETTINGS': str(root / 'settings.json'),
    'LIFEOS_NOTIFICATION_CHANNEL': 'headless', 'BUN_CONFIG_NO_AUTO_INSTALL': '1',
    'PYTHONDONTWRITEBYTECODE': '1', 'TERMINAL_CWD': str(root.parent),
    'HERMES_WRITE_SAFE_ROOT': str(root.parent)}
from ruamel.yaml import YAML
configured = YAML(typ='safe').load((profile / 'config.yaml').read_text())
model = configured['model']
route = {'provider': 'custom', 'model': model['default'], 'base_url': model['base_url'],
    'api_mode': model.get('api_mode', 'chat_completions')}
configuration_before = (profile / 'config.yaml').read_bytes()
state_path = root / 'LIFEOS/PULSE/state/state.json'
state_before = json.loads(state_path.read_text())
work = json.loads((stage / 'installed-schedule-hermes-work-second.txt').read_text())
isa_events = [item for item in work['events'] if item['src'] == 'ISASync.hook.ts']
assert any(item['slug'] == 'synthetic-conduit-hermes' and item['op'] == 'upsert' for item in isa_events)
assert work['registry']['sessions']['synthetic-conduit-hermes']['sessionUUID'] == 'synthetic-conduit-hermes-work'
assert len(work['approvals']) == 1 and work['approvals'][0]['choice'] == 'once'
events_dir = root / 'LIFEOS/USER/CONDUIT/events'
deadline = time.monotonic() + 190
captured = None
while time.monotonic() < deadline:
    state_after = json.loads(state_path.read_text())
    rows = [json.loads(line) for path in events_dir.glob('*.jsonl')
        for line in path.read_text().splitlines() if line.strip()]
    candidates = [item for item in rows if item.get('detail', {}).get('lastSlug') == 'synthetic-conduit-hermes'
        and item['ts'] >= max(event['ts'] for event in isa_events)]
    if candidates:
        captured = candidates[0]
        break
    time.sleep(1)
assert captured is not None, 'The actual unchanged daemon schedule does not capture the actual Hermes work'
assert captured['detail']['events'] >= len(isa_events)
assert state_after['jobs']['conduit-capture']['lastResult'] == 'ok'
assert all(path.stat().st_mode & 0o777 == 0o600 for path in events_dir.glob('*.jsonl'))
commands = []
for name in ('conduit-capture', 'memory-consolidation', 'proposal-gc', 'life-morning-brief'):
    started = time.monotonic()
    result = subprocess.run([str(stage / 'bin/hermes'), 'lifeos-job', name],
        env=environment, cwd=profile, capture_output=True, text=True, timeout=180)
    (stage / ('installed-owner-job-' + name + '.txt')).write_text(result.stdout + result.stderr)
    assert result.returncode == 0 and not result.stderr, result.stdout + result.stderr
    body = json.loads(result.stdout)
    assert body['status'] == 'completed' and body['job'] == name, body
    if name == 'conduit-capture':
        assert body['output'] == 'captured 0 event(s)\n'
    commands.append({'job': name, 'elapsed_seconds': round(time.monotonic() - started, 3), 'result': body})

os.environ.update(environment, XDG_RUNTIME_DIR='/run/user/1008',
    DBUS_SESSION_BUS_ADDRESS='unix:path=/run/user/1008/bus')
units = json.loads((stage / 'application-units.json').read_text())['units']
services = module('profile_services').ProfileServices(profile, root, units=units)
preview = services.preview()
started = time.monotonic()
services.drain(signature=preview['signature'])
services.verify_stopped()
drain_seconds = round(time.monotonic() - started, 3)
retained_capture = json.loads(state_path.read_text())['jobs']['conduit-capture']
assert retained_capture['lastRun'] >= state_after['jobs']['conduit-capture']['lastRun']
services.resume()
assert services.status()['state'] == 'active'
assert (profile / 'config.yaml').read_bytes() == configuration_before
report = {'status': 'PASS', 'actual_hermes_hook_events': work['events'], 'exact_synthetic_write_approval': work['approvals'],
    'native_scheduled_capture': captured, 'capture_state': retained_capture,
    'actual_owner_jobs': commands, 'restart_service_state': services.status(),
    'drain_seconds': drain_seconds, 'source_probe': 'installed-schedule-hermes-work-second.txt', 'schedules_changed': False,
    'model_routes_changed': False, 'synthetic_data_only': True, 'live_profile_changed': False,
    'discord_delivery_verified': False, 'active_long_job_shutdown_verified': False}
(stage / 'installed-schedule-verification.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
