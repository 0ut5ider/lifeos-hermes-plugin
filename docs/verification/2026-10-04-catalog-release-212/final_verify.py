# ABOUTME: Verifies current .212 services, plugin loading, model tools, and capture metadata.
# ABOUTME: Publishes only release facts and counts while retaining private payloads on the server.
from collections import Counter
from datetime import datetime
import gzip
import json
from pathlib import Path
import sys
import tomllib
import urllib.error
import urllib.request

from deploy_catalog import REVISION, check_sources, layout, run, save, sha, stable_services


def verify(target):
    ctx = layout(target)
    release = ctx['release']
    state = json.loads((release / 'preflight.json').read_text())
    status = json.loads((release / 'status.json').read_text())
    assert status['state'] == 'verified'
    check_sources(ctx, state)
    pids = stable_services(ctx)
    assert pids == status['services'], 'Service process changes after verification'
    interpreter = ctx['profile'] / 'tools/python-3.14.7+20260901-linux-x64/bin/python3'
    checker = release / 'plugin-source/docs/verification/2026-10-03-merged-release-212/check_runtime.py'
    runtime = json.loads(run(ctx, [interpreter, checker, ctx['host'], ctx['host'], ctx['plugin']]))
    assert (release / 'tool.done').is_file() and (release / 'tool.exit').read_text().strip() == '0'
    tool = json.loads((release / 'tool-result.json').read_text())
    http = {}
    for route in ['/chat', '/lifeos-bridge', '/api/plugins']:
        try:
            with urllib.request.urlopen(f'http://192.168.8.212:{ctx["port"]}{route}', timeout=10) as response:
                http[route] = response.status
        except urllib.error.HTTPError as error:
            http[route] = error.code
    assert http == {'/chat': 200, '/lifeos-bridge': 200, '/api/plugins': 401}
    config = json.loads(Path(state['recorder_path']).read_text())
    root = Path(config['root'])
    assert root.stat().st_mode & 0o077 == 0 and root.stat().st_uid == ctx['uid']
    assert Path(state['recorder_path']).stat().st_mode & 0o077 == 0
    rows = []
    for path in (root / 'runs' / config['run_id'] / 'events').glob('*/*.jsonl'):
        rows.extend(json.loads(line) for line in path.read_text().splitlines())
    service_initializations = {}
    tool_processes = set()
    for row in rows:
        if row['stage'] != 'process.initialized':
            continue
        if row['pid'] not in pids.values() and datetime.fromisoformat(row['time_utc']).timestamp() < tool['started']:
            continue
        artifact = json.loads(gzip.decompress((root / row['data_ref']['path']).read_bytes()))
        if row['pid'] in pids.values():
            assert artifact['config']['plugin_revision'] == REVISION
            assert artifact['capture_sources_actual'] == config['capture_sources']
            service_initializations[row['pid']] = True
        if str(release / 'tool-prompt.txt') in artifact.get('argv', []):
            assert artifact['config']['plugin_revision'] == REVISION
            assert artifact['capture_sources_actual'] == config['capture_sources']
            tool_processes.add(row['pid'])
    assert pids['hermes-gateway.service'] in service_initializations
    dashboard = 'hermes-dashboard.service' if target == 'discord' else 'lifeos-acceptance-dashboard.service'
    assert pids[dashboard] in service_initializations and tool_processes
    selected = [row for row in rows if row['pid'] in set(pids.values()) | tool_processes]
    gaps = [row for row in selected if row.get('status') == 'capture_gap' or row.get('prior_capture_failures')]
    assert not gaps, 'Capture reports a gap'
    turn_rows = [row for row in selected if row['pid'] in tool_processes]
    counts = Counter(row['stage'] for row in turn_rows)
    started = {row['invocation_id'] for row in turn_rows if row['stage'] == 'hook.started'}
    completed = {row['invocation_id'] for row in turn_rows if row['stage'] == 'hook.completed'}
    assert started and started == completed and not counts['hook.failed']
    pulse = tomllib.loads((ctx['native'] / 'LIFEOS/USER/CONFIG/PULSE.user.toml').read_text())
    result = {'target': target, 'revision': REVISION, 'plugin_version': '0.1.0',
              'plugin_files_verified': len(state['package_files']), 'runtime_files_changed': 2,
              'model_tools_sha256': sha(ctx['host'] / 'model_tools.py'),
              'services': pids, 'runtime': runtime, 'http': http, 'catalog': status['catalog'],
              'profile_preserved': status['profile_preserved'],
              'user_data_preserved_at_apply': status['user_data_preserved_at_apply'], 'tool': tool,
              'recorder': {'enabled': config['enabled'], 'plugin_revision': config['plugin_revision'],
                           'source_fingerprints_verified': len(config['fingerprints']),
                           'initialized_service_processes': sorted(service_initializations),
                           'tool_processes': sorted(tool_processes), 'tool_events': len(turn_rows),
                           'hook_starts': len(started), 'hook_completions': len(completed), 'capture_gaps': 0},
              'disabled_pulse_jobs': [job['name'] for job in pulse['job'] if not job.get('enabled', False)]}
    save(release / 'final-result.json', result)
    print(json.dumps(result))


if __name__ == '__main__':
    verify(sys.argv[1])
