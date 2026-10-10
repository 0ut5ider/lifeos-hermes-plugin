# ABOUTME: Selects the verified owner-job output correction in the isolated installed acceptance bridge.
# ABOUTME: Guards exact prior bytes and drains acceptance services while leaving the live profile unchanged.
import hashlib
import importlib
import json
import os
from pathlib import Path
import sys

stage = Path('/home/lifeos-hermes/migration/2026-10-09/daily-text-581d76a7')
prepared = json.loads((stage / 'applications-prepared.json').read_text())
profile, root = Path(prepared['profile']), Path(prepared['installed'])
os.umask(0o077)
os.environ.update(HOME=str(root.parent), HERMES_HOME=str(profile),
    XDG_RUNTIME_DIR='/run/user/1008', DBUS_SESSION_BUS_ADDRESS='unix:path=/run/user/1008/bus')
sys.path[:0] = [str(profile / 'plugins'), str(stage / 'package/hermes')]
def module(name):
    return importlib.import_module('lifeos-hook-bridge.' + name)
manifest_path = stage / 'APPLICATION-CANDIDATE.json'
original = manifest_path.read_bytes()
manifest = json.loads(original)
changes = []
for name in ('memory_access.py', 'memory_service.py', 'memory_owner_jobs.py'):
    relative = 'lifeos_hook_bridge/' + name
    target = profile / 'plugins/lifeos-hook-bridge' / name
    before, after = target.read_bytes(), (stage / 'owner-output-fix-payload' / name).read_bytes()
    assert hashlib.sha256(before).hexdigest() == manifest['plugin_files'][relative]
    changes.append((relative, target, before, after))
units = json.loads((stage / 'application-units.json').read_text())['units']
services = module('profile_services').ProfileServices(profile, root, units=units)
services.drain(signature=services.preview()['signature'])
services.verify_stopped()
try:
    retained = stage / 'APPLICATION-CANDIDATE-before-owner-output-fix.json'
    assert not retained.exists()
    retained.write_bytes(original)
    observations = []
    for relative, target, before, after in changes:
        assert target.read_bytes() == before
        (stage / 'owner-output-fix-payload' / (target.name + '.before')).write_bytes(before)
        module('memory_transaction').publish(target, after)
        digest = hashlib.sha256(after).hexdigest()
        manifest['plugin_files'][relative] = digest
        observations.append({'path': relative, 'before_sha256': hashlib.sha256(before).hexdigest(),
            'after_sha256': digest})
    manifest['owner_job_output_correction'] = observations
    module('memory_transaction').publish(manifest_path, (json.dumps(manifest, indent=2) + '\n').encode())
    services.resume()
    report = {'status': 'PASS', 'selected_files': observations, 'reviewer_character_limit': 65536,
        'owner_job_byte_limit': 4194304, 'service_state': services.status(), 'live_profile_changed': False}
    (stage / 'installed-owner-output-selection.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
except BaseException:
    for _, target, before, _ in changes:
        module('memory_transaction').publish(target, before)
    module('memory_transaction').publish(manifest_path, original)
    services.resume()
    raise
