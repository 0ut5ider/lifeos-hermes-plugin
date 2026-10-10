# ABOUTME: Selects tested plugin files and native Atlas code in the isolated acceptance profile.
# ABOUTME: Drains acceptance services, retains prior bytes, and verifies both canonical source trees.
import argparse
import hashlib
import importlib
import json
import os
from pathlib import Path
import stat
import sys


parser = argparse.ArgumentParser()
parser.add_argument('candidate', type=Path)
candidate = parser.parse_args().candidate
stage = Path('/home/lifeos-hermes/migration/2026-10-09/daily-text-581d76a7')
assert candidate.parent == stage.parent and candidate.name.startswith('daily-text-0.2.0-')
package = candidate/'package'
prepared = json.loads((stage/'applications-prepared.json').read_text())
profile, root = Path(prepared['profile']), Path(prepared['installed'])
selected = stage/'pulse-daemon-types-source/lifeos'
os.umask(0o077)
os.environ.update(HOME=str(root.parent), HERMES_HOME=str(profile),
    XDG_RUNTIME_DIR='/run/user/1008', DBUS_SESSION_BUS_ADDRESS='unix:path=/run/user/1008/bus')
sys.path[:0] = [str(profile/'plugins'), str(stage/'package/hermes'), str(package)]
installed = lambda name: importlib.import_module('lifeos-hook-bridge.'+name)
incoming = importlib.import_module('lifeos_hook_bridge.install_source')
sha = lambda content: hashlib.sha256(content).hexdigest()
manifest_path = stage/'APPLICATION-CANDIDATE.json'
original = manifest_path.read_bytes()
manifest = json.loads(original)
release = json.loads((package/'DAILY-CANDIDATE.json').read_text())
assert set(manifest['plugin_files']) <= set(release['plugin_files'])
incoming.validate_prepared_lifeos(package/'lifeos')
incoming.validate_supported_hermes(package/'hermes')
installed('install_source').validate_prepared_lifeos(selected)
configuration = (profile/'config.yaml').read_bytes()
memory_configuration = (profile/'lifeos-memory.json').read_bytes()
changes = []
for relative, expected in release['plugin_files'].items():
    target = profile/'plugins/lifeos-hook-bridge'/Path(relative).relative_to('lifeos_hook_bridge')
    before = target.read_bytes() if target.exists() else None
    assert (None if before is None else sha(before)) == manifest['plugin_files'].get(relative), relative
    source = package/relative
    after = source.read_bytes()
    assert sha(after) == expected
    if before != after:
        changes.append((target, before, after, stat.S_IMODE(target.stat().st_mode) if before is not None
            else stat.S_IMODE(source.stat().st_mode)))
for relative in map(Path, ('LIFEOS/ATLAS/Store.ts', 'LIFEOS/ATLAS/Atlas.ts', 'LIFEOS/PULSE/modules/atlas.ts')):
    canonical = selected/'LifeOS/install'/relative
    target = root/relative
    before = canonical.read_bytes()
    assert target.read_bytes() == before
    after = (package/'lifeos/LifeOS/install'/relative).read_bytes()
    if before != after:
        for path in (canonical, target):
            changes.append((path, before, after, stat.S_IMODE(path.stat().st_mode)))
schedule = root/'LIFEOS/USER/CONFIG/PULSE.user.toml'
before = schedule.read_bytes()
after = (package/'docs/deployment/daily-text/PULSE.user.toml').read_bytes()
changes.append((schedule, before, after, stat.S_IMODE(schedule.stat().st_mode)))
source_manifest = selected/'lifeos-source-manifest.json'
before = source_manifest.read_bytes()
assert sha(before) == manifest['native_source_manifest_sha256']
after = (package/'lifeos/lifeos-source-manifest.json').read_bytes()
changes.append((source_manifest, before, after, stat.S_IMODE(source_manifest.stat().st_mode)))
units = json.loads((stage/'application-units.json').read_text())['units']
services = installed('profile_services').ProfileServices(profile, root, units=units)
retained = stage/('atlas-selection-retained-'+release['head'][:8])
assert not retained.exists()
services.drain(signature=services.preview()['signature'])
services.verify_stopped()
retained.mkdir(mode=0o700)
publish = installed('memory_transaction').publish
observations = []
try:
    for index, (target, before, after, mode) in enumerate(changes):
        assert (target.read_bytes() if target.exists() else None) == before
        if before is not None:
            (retained/(str(index)+'.before')).write_bytes(before)
        observations.append({'path': str(target), 'before_sha256': None if before is None else sha(before),
            'after_sha256': sha(after), 'mode': mode, 'retained': None if before is None else str(index)+'.before'})
        publish(target, after, mode=mode)
    incoming.validate_prepared_lifeos(selected)
    assert (profile/'config.yaml').read_bytes() == configuration
    assert (profile/'lifeos-memory.json').read_bytes() == memory_configuration
    for relative, digest in release['plugin_files'].items():
        target = profile/'plugins/lifeos-hook-bridge'/Path(relative).relative_to('lifeos_hook_bridge')
        assert sha(target.read_bytes()) == digest
    (retained/'APPLICATION-CANDIDATE.json').write_bytes(original)
    (retained/'files.json').write_text(json.dumps(observations, indent=2)+'\n')
    manifest.update(head=release['head'], plugin_files=release['plugin_files'],
        native_source_manifest_sha256=sha((package/'lifeos/lifeos-source-manifest.json').read_bytes()),
        atlas_initialization_candidate=str(candidate), daily_schedule_sha256=sha(schedule.read_bytes()))
    publish(manifest_path, (json.dumps(manifest,indent=2)+'\n').encode())
    services.resume()
    report = {'status':'PASS', 'head':release['head'], 'files':observations,
        'plugin_file_count':len(release['plugin_files']), 'services':services.status(),
        'native_source_manifests_verified':True, 'model_routes_changed':False,
        'live_profile_changed':False, 'isolated_acceptance_profile_only':True}
    (stage/('installed-atlas-candidate-selection-'+release['head'][:8]+'.json')).write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
except BaseException:
    for target, before, _, mode in reversed(changes):
        if before is None:
            target.unlink(missing_ok=True)
        else:
            publish(target,before,mode=mode)
    publish(manifest_path,original)
    services.resume()
    raise
