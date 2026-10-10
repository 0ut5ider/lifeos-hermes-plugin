# ABOUTME: Corrects the isolated application's authenticated Pulse relay configuration.
# ABOUTME: Returns ownership before changing settings and preserves the original failed evidence.
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
account = 'dashboard:basic:acceptance-owner'
before = {'ownership_enabled': configuration.load()['ownership_enabled'],
    'relay_configured': 'pulse_http' in configuration.load()}
receipt = setup.recover(account=account)
if receipt['state'] != 'returned' or configuration.load()['ownership_enabled']:
    raise RuntimeError('Ownership does not return before the relay setup correction')
services.drain()
services.verify_stopped()
configuration.update(lambda value: value.update(pulse_http={
    'dashboard_base_url': 'http://127.0.0.1:18819',
    'dashboard_browser_url': 'http://localhost:18819'}))
from ruamel.yaml import YAML
yaml = YAML()
config_path = profile / 'config.yaml'
settings = yaml.load(config_path.read_text())
settings['plugins']['entries']['lifeos-hook-bridge']['settings']['lifeos_source_dir'] = str(
    stage / 'pulse-shutdown-source/lifeos/LifeOS/install')
with config_path.open('w') as stream:
    yaml.dump(settings, stream)
services.resume()
report = {'before': before, 'recovery': receipt, 'services': services.status(),
    'ownership_enabled': configuration.load()['ownership_enabled'],
    'relay': configuration.load()['pulse_http'], 'live_profile_changed': False}
(stage / 'application-relay-configuration.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
