# ABOUTME: Installs the pinned candidate in a new isolated home and prepares Adrian and Cerebo identity.
# ABOUTME: Keeps the live profile, transport credentials, and running services outside this acceptance fixture.
import json
import os
from pathlib import Path
import sys
import time

sys.dont_write_bytecode = True
stage = Path('/home/lifeos-hermes/migration/2026-10-09/daily-text-581d76a7')
package = stage / 'package'
site = Path('/home/lifeos-hermes/.hermes/installs/995dd15ff6e15ed0/environments/65f4231f26e94a2d989e89eb96b98808/venv/lib/python3.14/site-packages')
sys.path[:0] = [str(package), str(site)]
from lifeos_hook_bridge.install_source import install_prepared_lifeos
from lifeos_hook_bridge.memory_service import MemoryConfiguration
from lifeos_hook_bridge.fresh_store import FreshStore

os.umask(0o077)
profile = stage / 'profile'
profile.mkdir(mode=0o700)
os.environ['HERMES_HOME'] = str(profile)
os.environ['LIFEOS_NOTIFICATION_CHANNEL'] = 'headless'
bootstrap = stage / 'bootstrap/home/.claude'
started = time.monotonic()
receipt = install_prepared_lifeos(package / 'lifeos', bootstrap, stage / 'failed-bootstrap')
configuration = MemoryConfiguration(profile / 'lifeos-memory.json')
configuration.save({'version': 1, 'root': str(bootstrap), 'principal': 'acceptance-owner',
    'ownership_enabled': False, 'sharing_enabled': False,
    'accounts': {'dashboard:acceptance-owner': 'acceptance-owner'}, 'destinations': {}, 'clients': {}})
(profile / 'config.yaml').write_text('memory:\n  memory_enabled: false\n  user_profile_enabled: false\nplugins:\n  enabled: []\n')
review = FreshStore(configuration).prepare(package / 'lifeos', principal_name='Adrian',
    assistant_name='Cerebo', account='dashboard:acceptance-owner')
if (review['state'] != 'review' or review['active_facts'] != 0 or review['ownership_enabled']
        or review['sharing_enabled'] or review['services_started']):
    raise RuntimeError('The installed fresh store changes its isolated acceptance contract')
report = {'bootstrap_receipt': receipt, 'fresh_store_review': review,
    'elapsed_seconds': round(time.monotonic() - started, 3),
    'live_services_changed': False, 'transport_credentials_loaded': False}
(stage / 'fresh-store-installed.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
