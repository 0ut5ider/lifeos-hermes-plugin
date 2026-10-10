# ABOUTME: Selects the tested native Algorithm prompt transport in the synthetic acceptance installation.
# ABOUTME: Drains only acceptance services and retains exact prior source and plugin bytes for reversal.
import hashlib
import importlib
import json
import os
from pathlib import Path
import sys

stage = Path('/home/lifeos-hermes/migration/2026-10-09/daily-text-581d76a7')
prepared = json.loads((stage / 'applications-prepared.json').read_text())
profile, root = Path(prepared['profile']), Path(prepared['installed'])
payload = stage / 'algorithm-prompt-payload'
os.umask(0o077)
os.environ.update(HOME=str(root.parent), HERMES_HOME=str(profile),
    XDG_RUNTIME_DIR='/run/user/1008', DBUS_SESSION_BUS_ADDRESS='unix:path=/run/user/1008/bus')
sys.path[:0] = [str(profile / 'plugins'), str(stage / 'package/hermes')]
def module(name):
    return importlib.import_module('lifeos-hook-bridge.' + name)
sha = lambda value: hashlib.sha256(value).hexdigest()
manifest_path = stage / 'APPLICATION-CANDIDATE.json'
original = manifest_path.read_bytes()
manifest = json.loads(original)
spec = json.loads((payload / 'selection.json').read_text())
selected = stage / 'pulse-daemon-types-source/lifeos'
targets = [(root / 'LIFEOS/PULSE/modules/algorithm-tab.ts', 'algorithm-tab.ts', spec['native_before_sha256']),
    (selected / 'LifeOS/install/LIFEOS/PULSE/modules/algorithm-tab.ts', 'algorithm-tab.ts', spec['native_before_sha256']),
    (selected / 'lifeos-source-manifest.json', 'lifeos-source-manifest.json', manifest['native_source_manifest_sha256']),
    (profile / 'plugins/lifeos-hook-bridge/install_source.py', 'install_source.py', manifest['plugin_files']['lifeos_hook_bridge/install_source.py']),
    (profile / 'plugins/lifeos-hook-bridge/patches/lifeos-algorithm-prompt-transport.patch', 'lifeos-algorithm-prompt-transport.patch', None)]
changes = []
for target, name, expected in targets:
    before = target.read_bytes() if target.exists() else None
    assert (sha(before) if before is not None else None) == expected
    after = (payload / name).read_bytes()
    assert sha(after) == spec['files'][name]
    changes.append((target, name, before, after))
units = json.loads((stage / 'application-units.json').read_text())['units']
services = module('profile_services').ProfileServices(profile, root, units=units)
services.drain(signature=services.preview()['signature'])
services.verify_stopped()
retained = stage / 'algorithm-prompt-retained'
assert not retained.exists()
retained.mkdir(mode=0o700)
try:
    observations = []
    for index, (target, name, before, after) in enumerate(changes):
        assert (target.read_bytes() if target.exists() else None) == before
        if before is not None: (retained / (str(index) + '.before')).write_bytes(before)
        module('memory_transaction').publish(target, after)
        observations.append({'path': str(target), 'before_sha256': None if before is None else sha(before),
            'after_sha256': sha(after)})
    manifest['plugin_files']['lifeos_hook_bridge/install_source.py'] = spec['files']['install_source.py']
    manifest['plugin_files']['lifeos_hook_bridge/patches/lifeos-algorithm-prompt-transport.patch'] = spec['files']['lifeos-algorithm-prompt-transport.patch']
    manifest['native_source_manifest_sha256'] = spec['files']['lifeos-source-manifest.json']
    manifest['algorithm_prompt_transport'] = observations
    (retained / 'APPLICATION-CANDIDATE.json').write_bytes(original)
    module('memory_transaction').publish(manifest_path, (json.dumps(manifest, indent=2) + '\n').encode())
    services.resume()
    report = {'status': 'PASS', 'selected_files': observations, 'services': services.status(),
        'native_patch_count': 24, 'live_profile_changed': False, 'model_routes_changed': False}
    (stage / 'installed-algorithm-prompt-selection.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
except BaseException:
    for target, _, before, _ in changes:
        if before is None: target.unlink(missing_ok=True)
        else: module('memory_transaction').publish(target, before)
    module('memory_transaction').publish(manifest_path, original)
    services.resume()
    raise
