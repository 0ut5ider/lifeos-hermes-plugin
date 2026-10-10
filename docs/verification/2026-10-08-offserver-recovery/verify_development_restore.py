# ABOUTME: Verifies the restored development container and recovers its retained coherent profile snapshot.
# ABOUTME: Checks restored program hashes and SQLite integrity without activating the isolated recovery guest.
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys

os.umask(0o077)
home=Path.home()
profile=home/'.hermes'
os.environ['PATH']=str(home/'.local/bin')+os.pathsep+os.environ.get('PATH','')
if shutil.which('bun')!=str(home/'.local/bin/bun'):
    raise RuntimeError('Profile recovery requires the reviewed installed Bun runtime')
package=profile/'plugins/lifeos-hook-bridge'
spec=importlib.util.spec_from_file_location('lifeos_hook_bridge',package/'__init__.py',
    submodule_search_locations=[str(package)])
if spec is None or spec.loader is None:raise RuntimeError('The installed plugin package is unavailable')
module=importlib.util.module_from_spec(spec)
sys.modules['lifeos_hook_bridge']=module
spec.loader.exec_module(module)
from lifeos_hook_bridge.memory_access import NativeMemory
from lifeos_hook_bridge.memory_service import MemoryConfiguration
from lifeos_hook_bridge.profile_backup import inspect
from lifeos_hook_bridge.profile_backup_recovery import recover

configuration=MemoryConfiguration(profile/'lifeos-memory.json')
selected=configuration.load()
configuration.check_owner(selected,'dashboard:basic:release-owner')
if selected.get('ownership_enabled',False) or selected.get('sharing_enabled',False):
    raise RuntimeError('This recovery acceptance requires disabled fresh-store ownership and sharing')
receipt=json.loads((home/'migration/2026-10-08/plugin-profile-layout.json').read_text())
if receipt['state']!='complete':raise RuntimeError('Profile recovery requires the completed installed snapshot')
backup=Path(receipt['backup']['snapshot'])
signature=receipt['backup']['signature']
before=hashlib.sha256(configuration.path.read_bytes()).hexdigest()
programs={name:digest for name,digest in receipt['source_files'].items() if '__pycache__' not in Path(name).parts}
if any(hashlib.sha256((package/name).read_bytes()).hexdigest()!=digest for name,digest in programs.items()):
    raise RuntimeError('The PBS-restored installed program differs from its retained source receipt')
import sqlite3
with sqlite3.connect('file:'+str(profile/'state.db')+'?mode=ro',uri=True) as history:
    if history.execute('PRAGMA integrity_check').fetchall()!=[('ok',)]:
        raise RuntimeError('The PBS-restored Hermes history fails its integrity check')
    history_counts={table:history.execute('SELECT COUNT(*) FROM '+table).fetchone()[0] for table in ('sessions','messages')}
manifest=inspect(configuration,backup,signature,account='dashboard:basic:release-owner')
destination=home/'.local/state/lifeos-hook-bridge/profile-recovery/2026-10-08-offserver-restored'
result=recover(configuration,backup,signature,destination,account='dashboard:basic:release-owner')
candidate=Path(result['profile'])
verified=0
for item in manifest['files']:
    if item['path']==configuration.path.name:continue
    if hashlib.sha256((candidate/item['path']).read_bytes()).hexdigest()!=item['digest']:
        raise RuntimeError('A retained recovered profile file differs from its verified snapshot')
    verified+=1
rebound=MemoryConfiguration(candidate/configuration.path.name).load()
if rebound['root']!=result['root'] or rebound['ownership_enabled'] or rebound['sharing_enabled']:
    raise RuntimeError('The recovered profile has not retained disabled candidate authority')
if hashlib.sha256(configuration.path.read_bytes()).hexdigest()!=before:
    raise RuntimeError('The live memory configuration changes during separate recovery')
memory=NativeMemory(Path(result['root']))
with memory._transaction() as connection:
    facts=connection.execute('SELECT status,COUNT(*) FROM records GROUP BY status').fetchall()
summary={'status':result['status'],'profile_files':result['profile_files'],
    'verified_unchanged_profile_files':verified,'native_files':result['native_files'],
    'fact_counts':{row[0]:row[1] for row in facts},'ownership_enabled':False,'sharing_enabled':False,
    'live_configuration_unchanged':True,'snapshot_signature':signature,
    'verified_installed_program_files':len(programs),'history_integrity':'ok','history_counts':history_counts,
    'restored_container':103,'daily_server':False,'network_link_down':True}
(home/'migration/2026-10-08/offserver-recovery-result.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps(summary))
