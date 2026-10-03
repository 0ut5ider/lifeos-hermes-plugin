# ABOUTME: Verifies running services and recorder manifests without exporting content.
# ABOUTME: Rebuilds the private index and reports capture health and source identity.

import gzip
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import urllib.error
import urllib.request

home = Path.home()
configuration = home / '.config/lifeos-development-capture/config.json'
config = json.loads(configuration.read_text())
root = Path(config['root'])
development = home / 'workspace/development-hook-capture/development'
environment = dict(os.environ, XDG_RUNTIME_DIR='/run/user/' + str(os.getuid()),
                   DBUS_SESSION_BUS_ADDRESS='unix:path=/run/user/' + str(os.getuid()) + '/bus')
units = ['hermes-gateway.service', 'hermes-dashboard.service']


def state():
    result = {}
    for unit in units:
        response = subprocess.run(['systemctl', '--user', 'show', unit, '-p', 'ActiveState', '-p', 'SubState',
                                   '-p', 'MainPID', '-p', 'NRestarts'], env=environment,
                                  capture_output=True, text=True, check=True)
        result[unit] = dict(line.split('=', 1) for line in response.stdout.splitlines())
    return result


first = state()
time.sleep(3)
second = state()
assert all(value['ActiveState'] == 'active' and value['SubState'] == 'running' and int(value['MainPID']) > 0
           and value == first[unit] for unit, value in second.items()), 'Service health is not stable'
current = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in (development / 'hook_capture').glob('*.py')}
assert current == config['capture_sources'], 'Recorder manifest differs from reviewed disk source'
assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest() == expected
           for p, expected in config['fingerprints'].items()), 'Native source fingerprints changed'
found = {}
pids = {int(value['MainPID']): unit for unit, value in second.items()}
for path in root.glob('runs/*/events/*/*.jsonl'):
    for line in path.read_bytes().splitlines():
        event = json.loads(line)
        if event.get('stage') == 'process.initialized' and event.get('pid') in pids:
            content = json.loads(gzip.decompress((root / event['data_ref']['path']).read_bytes()))
            actual = content.get('capture_sources_actual')
            found[pids[event['pid']]] = {'pid': event['pid'], 'manifest_matches': actual == current}
assert len(found) == len(units) and all(value['manifest_matches'] for value in found.values()), 'Running process manifest mismatch'
sys.path.insert(0, str(development))
from hook_capture.analysis import rebuild, summary
health = summary(rebuild(root))
with urllib.request.urlopen('http://192.168.8.212:9119/', timeout=5) as response:
    login = response.status
try:
    with urllib.request.urlopen('http://192.168.8.212:9119/api/config', timeout=5) as response:
        unauthorized = response.status
except urllib.error.HTTPError as error:
    unauthorized = error.code
assert login == 200 and unauthorized == 401, 'Dashboard authentication health changed'
print(json.dumps({'services_stable': second, 'running_recorder_manifests': found, 'capture_sources': current,
                  'native_fingerprints_unchanged': True, 'dashboard_login': login, 'unauthenticated_config_api': unauthorized,
                  'config_mode': oct(configuration.stat().st_mode & 0o777), 'root_mode': oct(root.stat().st_mode & 0o777),
                  'health': {key: health[key] for key in ('events', 'known_lost_events', 'capture_gaps', 'integrity_issues',
                                                        'incomplete_invocations', 'known_registrations')}}, indent=2))
