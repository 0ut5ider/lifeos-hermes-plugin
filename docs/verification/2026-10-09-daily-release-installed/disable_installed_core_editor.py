# ABOUTME: Selects the tested daily profile without the ungoverned native Hermes core-file editor.
# ABOUTME: Verifies absent routes and retains exact previous configuration bytes for the isolated profile.
import hashlib
import importlib
import json
import os
from pathlib import Path
import sys
import time
import urllib.error
import urllib.request

stage = Path('/home/lifeos-hermes/migration/2026-10-09/daily-text-581d76a7')
prepared = json.loads((stage / 'applications-prepared.json').read_text())
profile, root = Path(prepared['profile']), Path(prepared['installed'])
os.umask(0o077)
os.environ.update(HOME=str(root.parent), HERMES_HOME=str(profile),
    PATH=str(stage / 'bin') + ':/home/lifeos-hermes/.local/bin:/usr/bin:/bin',
    PYTHONPATH=str(stage / 'package/hermes'), TZ='America/Toronto',
    XDG_RUNTIME_DIR='/run/user/1008', DBUS_SESSION_BUS_ADDRESS='unix:path=/run/user/1008/bus')
sys.path[:0] = [str(profile / 'plugins'), str(stage / 'package/hermes')]
def module(name):
    return importlib.import_module('lifeos-hook-bridge.' + name)
units = json.loads((stage / 'application-units.json').read_text())['units']
services = module('profile_services').ProfileServices(profile, root, units=units)
manifest = json.loads((stage / 'APPLICATION-CANDIDATE.json').read_text())
name = 'docs/deployment/daily-text/PULSE.user.toml'
target = root / 'LIFEOS/USER/CONFIG/PULSE.user.toml'
original = target.read_bytes()
assert hashlib.sha256(original).hexdigest() == manifest['daily_configuration_files'][name]
selected = (stage / 'daily-PULSE.user-core-disabled.toml').read_bytes()
assert selected == original.replace(b'bunker = false\n', b'bunker = false\nhermes = false\n')
retained = stage / 'daily-PULSE.user-before-core-disable.toml'
assert not retained.exists()
retained.write_bytes(original)
configuration_before = (profile / 'config.yaml').read_bytes()
services.drain(signature=services.preview()['signature'])
services.verify_stopped()
module('memory_transaction').publish(target, selected)
services.resume()
client = urllib.request.build_opener(urllib.request.ProxyHandler({}))
observations = []
for method, path, content in [('GET', '/api/hermes', None), ('GET', '/api/hermes/', None),
    ('GET', '/api/hermes/log-analysis', None), ('GET', '/api/hermes/file/principal-memory', None),
    ('PUT', '/api/hermes/file/config', {'content': 'Synthetic refused editor write'}),
    ('POST', '/api/hermes/remount', None)]:
    request = urllib.request.Request('http://127.0.0.1:18837' + path, method=method,
        data=None if content is None else json.dumps(content).encode(),
        headers={} if content is None else {'Content-Type': 'application/json'})
    for attempt in range(30):
        try:
            try:
                response = client.open(request, timeout=10)
            except urllib.error.HTTPError as error:
                response = error
            break
        except (OSError, urllib.error.URLError):
            time.sleep(1)
    else:
        raise RuntimeError('The actual Pulse daemon does not restart')
    with response:
        body = response.read(1024 * 1024).decode()
        observations.append({'method': method, 'path': path, 'status': response.status, 'body': body})
        assert response.status == 404, observations[-1]
assert (profile / 'config.yaml').read_bytes() == configuration_before
assert target.read_bytes() == selected and target.stat().st_mode & 0o777 == 0o600
manifest['daily_configuration_files'][name] = hashlib.sha256(selected).hexdigest()
manifest['daily_core_editor_selection'] = {'path': name,
    'before_sha256': hashlib.sha256(original).hexdigest(), 'after_sha256': hashlib.sha256(selected).hexdigest(),
    'launch_assumption': 'Use the actual Hermes dashboard for administration'}
(stage / 'APPLICATION-CANDIDATE.json').write_text(json.dumps(manifest, indent=2) + '\n')
report = {'status': 'PASS', 'observations': observations, 'native_core_editor_enabled': False,
    'actual_hermes_dashboard_configuration_unchanged': True, 'retained_previous_configuration': str(retained),
    'service_state': services.status(), 'live_profile_changed': False,
    'selection': manifest['daily_core_editor_selection']}
(stage / 'installed-core-editor-selection.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
