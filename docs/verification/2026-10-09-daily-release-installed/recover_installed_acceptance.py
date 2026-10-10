# ABOUTME: Recovers the interrupted isolated ownership operation with corrected native shutdown.
# ABOUTME: Preserves live services and records source identity before repeating admission.
import importlib
import hashlib
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
account = 'dashboard:basic:acceptance-owner'
if configuration.load()['ownership_enabled']:
    raise RuntimeError('The interrupted isolated activation unexpectedly enables ownership')
services.quiesce()
services.verify_stopped()
candidate = stage / 'pulse-shutdown-source/lifeos'
relative = 'LIFEOS/PULSE/pulse.ts'
original = (stage / 'mount-plugin-source/lifeos/LifeOS/install' / relative).read_bytes()
corrected = (candidate / 'LifeOS/install' / relative).read_bytes()
target = installed / relative
if target.read_bytes() != original:
    raise RuntimeError('The isolated daemon bytes differ before the selected correction')
target.write_bytes(corrected)
manifest = json.loads((stage / 'APPLICATION-CANDIDATE.json').read_text())
patch_name = 'lifeos_hook_bridge/patches/lifeos-memory-access.patch'
patch = (stage / 'lifeos-memory-access.patch').read_bytes()
target = profile / 'plugins/lifeos-hook-bridge/patches/lifeos-memory-access.patch'
if hashlib.sha256(target.read_bytes()).hexdigest() != manifest['plugin_files'][patch_name]:
    raise RuntimeError('The isolated memory patch differs before correction')
target.write_bytes(patch)
manifest['plugin_files'][patch_name] = hashlib.sha256(patch).hexdigest()
manifest['native_pulse_correction'] = {'path': relative,
    'before_sha256': hashlib.sha256(original).hexdigest(),
    'after_sha256': hashlib.sha256(corrected).hexdigest()}
manifest['native_source_manifest_sha256'] = hashlib.sha256(
    (candidate / 'lifeos-source-manifest.json').read_bytes()).hexdigest()
receipt = setup.recover(account=account)
if receipt['state'] != 'returned' or configuration.load()['ownership_enabled']:
    raise RuntimeError('The interrupted activation does not return to disabled ownership')
services.drain()
services.verify_stopped()
from ruamel.yaml import YAML
yaml = YAML()
config_path = profile / 'config.yaml'
settings = yaml.load(config_path.read_text())
settings['plugins']['entries']['lifeos-hook-bridge']['settings']['lifeos_source_dir'] = str(candidate / 'LifeOS/install')
with config_path.open('w') as stream:
    yaml.dump(settings, stream)
services.resume()
(stage / 'APPLICATION-CANDIDATE.json').write_text(json.dumps(manifest, indent=2) + '\n')
report = {'recovery': receipt, 'services': services.status(),
    'native_pulse_correction': manifest['native_pulse_correction'],
    'ownership_enabled': configuration.load()['ownership_enabled'],
    'live_profile_changed': False, 'transport_credentials_loaded': False}
(stage / 'application-shutdown-recovery.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
