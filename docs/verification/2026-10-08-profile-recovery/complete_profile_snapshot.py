# ABOUTME: Completes the recorded development profile backup after the deployed plugin layout is covered.
# ABOUTME: Verifies disabled ownership and resumed services without replacing a prior snapshot.
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import stat
import sys

os.umask(0o077)
home=Path.home()
profile=home/'.hermes'
os.environ['PATH']=str(home/'.local/bin')+os.pathsep+os.environ.get('PATH','')
if shutil.which('bun')!=str(home/'.local/bin/bun'):
    raise RuntimeError('Profile snapshot requires the reviewed installed Bun runtime')
package=profile/'plugins/lifeos-hook-bridge'
spec=importlib.util.spec_from_file_location('lifeos_hook_bridge',package/'__init__.py',
    submodule_search_locations=[str(package)])
if spec is None or spec.loader is None:
    raise RuntimeError('The installed plugin package is unavailable')
module=importlib.util.module_from_spec(spec)
sys.modules['lifeos_hook_bridge']=module
spec.loader.exec_module(module)
from lifeos_hook_bridge.memory_service import MemoryConfiguration
from lifeos_hook_bridge.memory_transaction import publish
from lifeos_hook_bridge.profile_backup import create, inspect
from lifeos_hook_bridge.profile_services import ProfileServices

configuration=MemoryConfiguration(profile/'lifeos-memory.json')
selected=configuration.load()
configuration.check_owner(selected,'dashboard:basic:release-owner')
if selected.get('ownership_enabled',False) or selected.get('sharing_enabled',False):
    raise RuntimeError('This recovery acceptance requires disabled fresh-store ownership and sharing')
directory=home/'migration/2026-10-08'
journal=directory/'plugin-profile-layout.json'
receipt=json.loads(journal.read_text())
target=Path(receipt['target'])
if receipt['state']!='installed' or target.is_symlink() or target.resolve()!=target:
    raise RuntimeError('Review the recorded installed plugin layout before snapshot completion')
programs={name:digest for name,digest in receipt['source_files'].items() if '__pycache__' not in Path(name).parts}
if any(hashlib.sha256((target/name).read_bytes()).hexdigest()!=digest for name,digest in programs.items()):
    raise RuntimeError('The installed plugin code differs from the recorded source')
services=ProfileServices(profile,Path(selected['root']))
if services.status()['recovery_required']:
    raise RuntimeError('Recover the preceding service drain before snapshot completion')
snapshot=home/'.local/state/lifeos-hook-bridge/profile-backups/2026-10-08-installed-layout'
permissions=directory/'native-backup-permissions.json'
user=Path(selected['root']).parent/'.config/LIFEOS/USER'
names=('CACHE','CUSTOMIZATIONS/SKILLS/LocalIntelligence','CUSTOMIZATIONS/SKILLS/LocalIntelligence/runs')
changes=[]
for name in names:
    path=user/name
    info=path.lstat()
    if path.resolve()!=path or info.st_uid!=os.getuid() or not stat.S_ISDIR(info.st_mode):
        raise RuntimeError('A measured native directory changes its physical owner path')
    changes.append({'path':str(path),'mode':stat.S_IMODE(info.st_mode)})
if permissions.exists():
    if any((user/name).stat().st_mode&0o077 for name in names):
        raise RuntimeError('Review the preceding native directory normalization before another change')
else:
    publish(permissions,(json.dumps({'version':1,'directories':changes},indent=2)+'\n').encode())
review=services.preview()
try:
    services.drain(signature=review['signature'])
    services.verify_stopped()
    for name in names:(user/name).chmod(0o700)
    receipt['backup']=create(configuration,snapshot,account='dashboard:basic:release-owner')
    inspect(configuration,snapshot,receipt['backup']['signature'],account='dashboard:basic:release-owner')
    receipt['state']='backed_up'
    publish(journal,(json.dumps(receipt,indent=2)+'\n').encode())
finally:
    if services.status()['recovery_required']:services.resume()
receipt['services']=services.status()
receipt['state']='complete'
publish(journal,(json.dumps(receipt,indent=2)+'\n').encode())
print(json.dumps({'state':'complete','verified_program_files':len(programs),'backup':receipt['backup'],
    'services':receipt['services'],'ownership_enabled':False,'source_code_changed':False}))
