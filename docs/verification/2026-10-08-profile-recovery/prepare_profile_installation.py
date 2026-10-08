# ABOUTME: Installs identical deployed plugin bytes inside the selected development profile for backup coverage.
# ABOUTME: Drains bound services, preserves the original link, and records a private recovery receipt.
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import sys

sys.path.insert(0,'/home/lifeos-hermes/workspace/plugin-release')
from lifeos_hook_bridge.memory_service import MemoryConfiguration
from lifeos_hook_bridge.memory_transaction import publish
from lifeos_hook_bridge.profile_backup import create
from lifeos_hook_bridge.profile_services import ProfileServices


def identity(root):
    result={}
    for path in sorted(root.rglob('*')):
        info=path.lstat()
        if info.st_uid!=os.getuid() or stat.S_ISLNK(info.st_mode):
            raise RuntimeError('Plugin backup preparation requires regular owner program sources')
        if stat.S_ISREG(info.st_mode):
            result[path.relative_to(root).as_posix()]=hashlib.sha256(path.read_bytes()).hexdigest()
        elif not stat.S_ISDIR(info.st_mode):
            raise RuntimeError('Plugin backup preparation refuses a runtime program entry')
    return result


os.umask(0o077)
home=Path.home()
os.environ['PATH']=str(home/'.local/bin')+os.pathsep+os.environ.get('PATH','')
if shutil.which('bun')!=str(home/'.local/bin/bun'):
    raise RuntimeError('Profile backup preparation requires the reviewed installed Bun runtime')
profile=home/'.hermes'
configuration=MemoryConfiguration(profile/'lifeos-memory.json')
selected=configuration.load()
configuration.check_owner(selected,'dashboard:basic:release-owner')
if selected.get('ownership_enabled',False) or selected.get('sharing_enabled',False):
    raise RuntimeError('Plugin backup preparation requires the selected fresh store to remain disabled')
target=profile/'plugins/lifeos-hook-bridge'
source=home/'workspace/plugin-release/lifeos_hook_bridge'
if not target.is_symlink() or target.resolve()!=source or source.resolve()!=source:
    raise RuntimeError('Review the selected plugin link before installation preparation')
before=identity(source)
directory=home/'migration/2026-10-08'
journal=directory/'plugin-profile-layout.json'
saved=directory/'original-plugin-link'
stage=target.with_name('.lifeos-hook-bridge-backup-stage')
snapshot=home/'.local/state/lifeos-hook-bridge/profile-backups/2026-10-08-installed-layout'
if any(path.exists() or path.is_symlink() for path in (journal,saved,stage,snapshot)):
    raise RuntimeError('Recover the preceding installation preparation before another operation')
services=ProfileServices(profile,Path(selected['root']))
if services.status()['recovery_required']:
    raise RuntimeError('Recover the selected service operation before installation preparation')
review=services.preview()
receipt={'version':1,'state':'prepared','target':str(target),'original_link':os.readlink(target),
    'saved_link':str(saved),'source_files':before,'service_signature':review['signature'],
    'ownership_enabled':False,'sharing_enabled':False,'source_code_changed':False}


def record(state):
    receipt['state']=state
    publish(journal,(json.dumps(receipt,indent=2)+'\n').encode())


record('prepared')
try:
    services.drain(signature=review['signature'])
    services.verify_stopped()
    record('drained')
    before=identity(source)
    receipt['source_files']=before
    shutil.copytree(source,stage,symlinks=True)
    if identity(stage)!=before or identity(source)!=before:
        raise RuntimeError('The plugin program source changes during installation preparation')
    for path in [stage,*stage.rglob('*')]:
        mode=path.stat().st_mode
        path.chmod(0o700 if path.is_dir() or mode&0o111 else 0o600)
    record('publishing')
    os.rename(target,saved)
    os.rename(stage,target)
    descriptor=os.open(target.parent,os.O_RDONLY|os.O_DIRECTORY)
    try:os.fsync(descriptor)
    finally:os.close(descriptor)
    if identity(target)!=before:
        raise RuntimeError('The installed plugin differs from the reviewed deployed source')
    record('installed')
    receipt['backup']=create(configuration,snapshot,account='dashboard:basic:release-owner')
    record('backed_up')
finally:
    if services.status()['recovery_required']:services.resume()
receipt['services']=services.status()
record('complete')
print(json.dumps({'state':'complete','installed_files':len(before),
    'backup':receipt['backup'],'services':receipt['services'],
    'ownership_enabled':False,'source_code_changed':False}))
