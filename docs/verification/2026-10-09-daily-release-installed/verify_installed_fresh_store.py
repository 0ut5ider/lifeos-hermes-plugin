# ABOUTME: Revalidates the signed isolated fresh-store result after installed preparation.
# ABOUTME: Preserves the malformed launcher marker and reports only verified completion facts.
import hashlib
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
stage = Path('/home/lifeos-hermes/migration/2026-10-09/daily-text-581d76a7')
package = stage / 'package'
sys.path[:0] = [str(package), '/home/lifeos-hermes/.hermes/installs/995dd15ff6e15ed0/environments/65f4231f26e94a2d989e89eb96b98808/venv/lib/python3.14/site-packages']
from lifeos_hook_bridge.fresh_store import FreshStore
from lifeos_hook_bridge.memory_service import MemoryConfiguration

result = json.loads((stage / 'fresh-store-installed.json').read_text())
previous = result['fresh_store_review']
home = Path(previous['installed']).parent
identifier = home.parent.name
configuration = MemoryConfiguration(stage / 'profile/lifeos-memory.json')
current_home, current = FreshStore(configuration).review_home(identifier, account='dashboard:acceptance-owner')
if current_home != home or current['state'] != 'review' or current['names'] != {'principal': 'Adrian', 'assistant': 'Cerebo'}:
    raise RuntimeError('The isolated signed fresh-store review does not validate')
if configuration.load()['ownership_enabled'] or configuration.load()['sharing_enabled']:
    raise RuntimeError('The isolated profile changes owner activation')
record = {'identifier': identifier, 'home': str(home), 'review_state': current['state'],
    'names': current['names'], 'signature': previous['signature'], 'signed_review_valid': True,
    'active_facts': previous['active_facts'], 'ownership_enabled': False, 'sharing_enabled': False,
    'services_started': previous['services_started'], 'live_services_changed': False,
    'original_launcher_marker': (stage / 'fresh-store-installed.done').read_text(),
    'original_exit_status_marker_valid': False}
(stage / 'fresh-store-revalidation.json').write_text(json.dumps(record, indent=2) + '\n')
print(json.dumps(record, indent=2))
