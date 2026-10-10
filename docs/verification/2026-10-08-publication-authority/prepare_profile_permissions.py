# ABOUTME: Records and normalizes measured backup directory permissions on the development profile.
# ABOUTME: Restarts the selected services through their recovery journal with a private creation mask.
import json
import os
from pathlib import Path
import stat
import subprocess
import sys

sys.path.insert(0, '/home/lifeos-hermes/workspace/plugin-release')
from lifeos_hook_bridge.memory_service import MemoryConfiguration
from lifeos_hook_bridge.memory_transaction import publish
from lifeos_hook_bridge.profile_services import ProfileServices


os.umask(0o077)
home = Path.home()
profile = home / '.hermes'
configuration = MemoryConfiguration(profile / 'lifeos-memory.json')
selected = configuration.load()
if selected.get('ownership_enabled', False) or selected.get('sharing_enabled', False):
    raise RuntimeError('This preparation requires the selected fresh store to remain disabled')
services = ProfileServices(profile, Path(selected['root']))
if services.status()['recovery_required']:
    raise RuntimeError('Recover the selected service operation before permission preparation')
names = ('source-checks', 'platforms', 'platforms/pairing', 'kanban', 'state',
         'plugin-update-checks', 'sandboxes', 'sandboxes/singularity', 'gateway', 'runtime')
review = []
for name in names:
    path = profile / name
    info = path.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or path.resolve() != path:
        raise RuntimeError('A reviewed profile directory changes its physical owner path')
    review.append({'path': name, 'mode': info.st_mode & 0o777})
dropins = [home / '.config/systemd/user' / (unit + '.d') / 'backup-privacy.conf'
           for unit in services.units.values()]
if any(path.exists() or path.is_symlink() for path in dropins):
    raise RuntimeError('A permission drop-in already exists; review the previous operation')
journal = home / 'migration/2026-10-08/profile-permissions.json'
if journal.exists():
    raise RuntimeError('Review the saved permission preparation before another operation')
receipt = {'version': 1, 'directories': review, 'dropins': [str(path) for path in dropins],
           'state': 'prepared', 'ownership_enabled': False}
publish(journal, (json.dumps(receipt, indent=2) + '\n').encode())
for path in dropins:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    publish(path, b'[Service]\nUMask=0077\n')
subprocess.run(['systemctl', '--user', 'daemon-reload'], check=True, capture_output=True)
signature = services.preview()['signature']
receipt['service_signature'] = signature
receipt['state'] = 'draining'
publish(journal, (json.dumps(receipt, indent=2) + '\n').encode())
try:
    services.drain(signature=signature)
    services.verify_stopped()
    for item in review:
        (profile / item['path']).chmod(0o700)
    receipt['state'] = 'restarting'
    publish(journal, (json.dumps(receipt, indent=2) + '\n').encode())
    resumed = services.resume()
except BaseException:
    if services.status()['recovery_required']:
        services.resume()
    raise
if resumed['state'] != 'active':
    raise RuntimeError('The selected services do not resume')
for unit in services.units.values():
    current = subprocess.run(['systemctl', '--user', 'show', unit, '--property=UMask', '--value'],
                             check=True, capture_output=True, text=True).stdout.strip()
    if current != '0077':
        raise RuntimeError('A selected service does not use the private creation mask')
receipt['state'] = 'complete'
publish(journal, (json.dumps(receipt, indent=2) + '\n').encode())
print(json.dumps({'state': receipt['state'], 'private_directories': len(review),
                  'services': len(dropins), 'ownership_enabled': False}))
