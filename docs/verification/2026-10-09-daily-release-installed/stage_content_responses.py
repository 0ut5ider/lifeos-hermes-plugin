# ABOUTME: Selects the built Content action page in only the synthetic acceptance installation.
# ABOUTME: Guards prior files and exports and retains both export directories for reversal.
import hashlib
import importlib
import json
import os
from pathlib import Path
import sys
import tarfile

stage = Path('/home/lifeos-hermes/migration/2026-10-09/daily-text-581d76a7')
prepared = json.loads((stage / 'applications-prepared.json').read_text())
profile, root = Path(prepared['profile']), Path(prepared['installed'])
payload = stage / 'content-response-payload'
os.umask(0o077)
os.environ.update(HOME=str(root.parent), HERMES_HOME=str(profile),
    XDG_RUNTIME_DIR='/run/user/1008', DBUS_SESSION_BUS_ADDRESS='unix:path=/run/user/1008/bus')
sys.path[:0] = [str(profile / 'plugins'), str(stage / 'package/hermes')]
def module(name): return importlib.import_module('lifeos-hook-bridge.' + name)
sha = lambda content: hashlib.sha256(content).hexdigest()
def digest(directory):
    result = hashlib.sha256()
    for path in sorted(directory.rglob('*')):
        if path.is_file():
            assert not path.is_symlink()
            result.update(path.relative_to(directory).as_posix().encode() + b'\0'
                + sha(path.read_bytes()).encode() + b'\n')
    return result.hexdigest()
spec = json.loads((payload / 'selection.json').read_text())
selected = stage / 'pulse-daemon-types-source/lifeos'
manifest_path = stage / 'APPLICATION-CANDIDATE.json'
original = manifest_path.read_bytes()
manifest = json.loads(original)
relative = 'LIFEOS/PULSE/Observability'
exports = [root / relative / 'out', selected / 'LifeOS/install' / relative / 'out']
assert all(digest(path) == spec['before_export_sha256'] for path in exports)
targets = [(root / relative / 'src/app/content/page.tsx', 'content-page.tsx', spec['source_before_sha256']),
    (selected / 'LifeOS/install' / relative / 'src/app/content/page.tsx', 'content-page.tsx', spec['source_before_sha256']),
    (selected / 'lifeos-source-manifest.json', 'lifeos-source-manifest.json', manifest['native_source_manifest_sha256']),
    (profile / 'plugins/lifeos-hook-bridge/install_source.py', 'install_source.py', manifest['plugin_files']['lifeos_hook_bridge/install_source.py']),
    (profile / 'plugins/lifeos-hook-bridge/patches/lifeos-content-response-consumption.patch', 'lifeos-content-response-consumption.patch', None)]
changes = []
for target, name, expected in targets:
    before = target.read_bytes() if target.exists() else None
    assert (sha(before) if before is not None else None) == expected
    after = (payload / name).read_bytes()
    assert sha(after) == spec['files'][name]
    changes.append((target, before, after))
assert sha((payload / 'exports.tgz').read_bytes()) == spec['export_archive_sha256']
retained = stage / 'content-response-retained'
assert not retained.exists()
retained.mkdir(mode=0o700)
expanded = retained / 'expanded'
expanded.mkdir(mode=0o700)
with tarfile.open(payload / 'exports.tgz') as source: source.extractall(expanded, filter='data')
assert digest(expanded / 'out') == spec['after_export_sha256']
units = json.loads((stage / 'application-units.json').read_text())['units']
services = module('profile_services').ProfileServices(profile, root, units=units)
services.drain(signature=services.preview()['signature'])
services.verify_stopped()
switched = []
try:
    import shutil
    for index, target in enumerate(exports):
        assert digest(target) == spec['before_export_sha256']
        previous = retained / ('export-' + str(index) + '.before')
        incoming = target.with_name('out.content-responses-incoming')
        assert not previous.exists() and not incoming.exists()
        shutil.copytree(expanded / 'out', incoming)
        os.rename(target, previous)
        try: os.rename(incoming, target)
        except BaseException:
            os.rename(previous, target)
            raise
        switched.append((target, previous))
    for index, (target, before, after) in enumerate(changes):
        assert (target.read_bytes() if target.exists() else None) == before
        if before is not None: (retained / (str(index) + '.before')).write_bytes(before)
        module('memory_transaction').publish(target, after)
    (retained / 'APPLICATION-CANDIDATE.json').write_bytes(original)
    manifest['plugin_files']['lifeos_hook_bridge/install_source.py'] = spec['files']['install_source.py']
    manifest['plugin_files']['lifeos_hook_bridge/patches/lifeos-content-response-consumption.patch'] = spec['files']['lifeos-content-response-consumption.patch']
    manifest['native_source_manifest_sha256'] = spec['files']['lifeos-source-manifest.json']
    manifest['content_response_consumption'] = spec
    module('memory_transaction').publish(manifest_path, (json.dumps(manifest, indent=2) + '\n').encode())
    services.resume()
    report = {'status': 'PASS', 'exports': [str(path) for path in exports],
        'before_export_sha256': spec['before_export_sha256'], 'after_export_sha256': spec['after_export_sha256'],
        'native_patch_count': 25, 'services': services.status(), 'live_profile_changed': False,
        'model_routes_changed': False, 'media_runner_started': False}
    (stage / 'installed-content-response-selection.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
except BaseException:
    for target, previous in reversed(switched):
        os.rename(target, retained / ('export-' + str(exports.index(target)) + '.failed'))
        os.rename(previous, target)
    for target, before, _ in changes:
        if before is None: target.unlink(missing_ok=True)
        else: module('memory_transaction').publish(target, before)
    module('memory_transaction').publish(manifest_path, original)
    services.resume()
    raise
