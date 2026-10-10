# ABOUTME: Applies tested daemon type corrections to the isolated acceptance installation.
# ABOUTME: Returns ownership and drains only the three selected acceptance services.
import hashlib
import importlib
import json
import os
from pathlib import Path
import sys

stage = Path('/home/lifeos-hermes/migration/2026-10-09/daily-text-581d76a7')
prepared = json.loads((stage / 'applications-prepared.json').read_text())
profile = Path(prepared['profile'])
installed = Path(prepared['installed'])
os.umask(0o077)
os.environ.update(HOME=str(installed.parent), HERMES_HOME=str(profile),
    PATH=str(stage / 'bin') + ':/home/lifeos-hermes/.local/bin:/usr/bin:/bin',
    PYTHONPATH=str(stage / 'package/hermes'), TZ='America/Toronto',
    XDG_RUNTIME_DIR='/run/user/1008', DBUS_SESSION_BUS_ADDRESS='unix:path=/run/user/1008/bus')
sys.path[:0] = [str(profile / 'plugins'), str(stage / 'package/hermes')]
def module(name):
    return importlib.import_module('lifeos-hook-bridge.' + name)
configuration = module('memory_service').MemoryConfiguration(profile / 'lifeos-memory.json')
units = json.loads((stage / 'application-units.json').read_text())['units']
services = module('profile_services').ProfileServices(profile, installed, units=units)
setup = module('ownership_setup').OwnershipSetup(configuration, units=units)
receipt = setup.recover(account='dashboard:basic:acceptance-owner')
if receipt['state'] != 'returned' or configuration.load()['ownership_enabled']:
    raise RuntimeError('The isolated ownership operation does not return before source selection')
services.drain()
services.verify_stopped()
candidate = stage / 'pulse-daemon-types-source/lifeos'
previous = stage / 'pulse-shutdown-source/lifeos'
changes = []
for relative in ('LIFEOS/PULSE/pulse.ts', 'LIFEOS/HERMES/Health.ts'):
    original = (previous / 'LifeOS/install' / relative).read_bytes()
    corrected = (candidate / 'LifeOS/install' / relative).read_bytes()
    target = installed / relative
    if target.read_bytes() != original:
        raise RuntimeError('The isolated native bytes change before source correction')
    target.write_bytes(corrected)
    changes.append({'path': relative, 'before_sha256': hashlib.sha256(original).hexdigest(),
        'after_sha256': hashlib.sha256(corrected).hexdigest()})
manifest = json.loads((stage / 'APPLICATION-CANDIDATE.json').read_text())
patch_name = 'lifeos_hook_bridge/patches/lifeos-memory-access.patch'
target = profile / 'plugins/lifeos-hook-bridge/patches/lifeos-memory-access.patch'
if hashlib.sha256(target.read_bytes()).hexdigest() != manifest['plugin_files'][patch_name]:
    raise RuntimeError('The isolated patch changes before source correction')
patch = (stage / 'lifeos-memory-access-types.patch').read_bytes()
target.write_bytes(patch)
manifest['plugin_files'][patch_name] = hashlib.sha256(patch).hexdigest()
manifest['native_type_corrections'] = changes
manifest['native_source_manifest_sha256'] = hashlib.sha256(
    (candidate / 'lifeos-source-manifest.json').read_bytes()).hexdigest()
from ruamel.yaml import YAML
yaml = YAML()
config_path = profile / 'config.yaml'
settings = yaml.load(config_path.read_text())
settings['plugins']['entries']['lifeos-hook-bridge']['settings']['lifeos_source_dir'] = str(candidate / 'LifeOS/install')
with config_path.open('w') as stream:
    yaml.dump(settings, stream)
services.resume()
(stage / 'APPLICATION-CANDIDATE.json').write_text(json.dumps(manifest, indent=2) + '\n')
report = {'recovery': receipt, 'services': services.status(), 'native_type_corrections': changes,
    'ownership_enabled': configuration.load()['ownership_enabled'], 'live_profile_changed': False}
(stage / 'application-types-selection.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
