# ABOUTME: Measures preference root validation across a concurrent configuration change.
# ABOUTME: Uses real configuration publication and temporary SSH keys with a read barrier.
from pathlib import Path
import sys,json,threading,concurrent.futures
sys.path.insert(0,str(Path.cwd()));sys.path.insert(0,str(Path.cwd()/'tests'))
from test_memory_preferences import MemoryPreferencesTests
from test_memory_sharing import public_key
from lifeos_hook_bridge.memory_service import MemoryConfiguration
from lifeos_hook_bridge.memory_preferences import MemoryPreferences
for operation in ('enroll','revoke','sharing'):
 f=MemoryPreferencesTests();f.setUp()
 try:
  pref=f.preferences;config=MemoryConfiguration(f.fixture.fixture.config)
  if operation=='revoke':pref.enroll(dict(client='race',public_key=public_key(90),projects=['lab'],model_route='unknown'))
  checked=threading.Event();proceed=threading.Event()
  class ObservedPreferences(MemoryPreferences):
   def _configuration(self):
    value=super()._configuration();checked.set()
    if not proceed.wait(10):raise RuntimeError('probe barrier timeout')
    return value
  watched=ObservedPreferences(config.path,pref.root,f.fixture.keys,Path(sys.executable),Path.cwd()/'lifeos_hook_bridge/memory_mcp.py')
  def act():
   if operation=='enroll':return watched.enroll(dict(client='race',public_key=public_key(90),projects=['lab'],model_route='unknown'))
   if operation=='revoke':return watched.revoke('race')
   return watched.sharing(True)
  with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
   task=pool.submit(act)
   assert checked.wait(10)
   other=str(pref.root.parent/'other-synthetic-installation')
   config.update(lambda value:value.update(root=other))
   before=config.load();key_before=f.fixture.keys.read_text();proceed.set()
   try: result=task.result(timeout=10)
   except Exception as error: result={'error':type(error).__name__,'message':str(error)}
   after=config.load()
  print(json.dumps({'operation':operation,'result':result,'other_root':other,'root_after':after['root'],'configuration_changed':before!=after,'keys_changed':key_before!=f.fixture.keys.read_text(),'client':after['clients'].get('race')}),flush=True)
 finally:f.doCleanups()
