# ABOUTME: Checks installation binding when enrollment publication fails after grant commit.
# ABOUTME: Uses a real filesystem failure and concurrent configuration update in temporary fixtures.
from pathlib import Path
import sys,threading,concurrent.futures,json
sys.path.insert(0,str(Path.cwd()));sys.path.insert(0,str(Path.cwd()/'tests'))
from test_memory_preferences import MemoryPreferencesTests
from test_memory_sharing import public_key
from lifeos_hook_bridge.memory_service import MemoryConfiguration
f=MemoryPreferencesTests();f.setUp()
try:
 pref=f.preferences;path=f.fixture.fixture.config;committed=threading.Event();proceed=threading.Event()
 class ObservedConfiguration(MemoryConfiguration):
  calls=0
  def update(self,change):
   result=super().update(change);self.calls+=1
   if self.calls==1:
    committed.set()
    if not proceed.wait(10):raise RuntimeError('probe timeout')
   return result
 pref.connections.configuration=ObservedConfiguration(path)
 def enroll():return pref.enroll({'client':'race','public_key':public_key(91),'projects':['lab'],'model_route':'unknown'})
 with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
  pending=pool.submit(enroll);assert committed.wait(10)
  config=MemoryConfiguration(path)
  def switch(value):
   value['clients']['race']={'enabled':True,'read':['project'],'write':[],'projects':['other'],'model_route':'unknown','credential_fingerprint':'SHA256:unrelated-synthetic-key'}
  config.update(switch);before=config.load();keys=f.fixture.keys.read_text()
  f.fixture.keys.parent.chmod(0o500);proceed.set()
  try:result=pending.result(timeout=10)
  except Exception as error:result={'error':type(error).__name__,'message':str(error)}
  after=config.load()
 print(json.dumps({'result':result,'before':before['clients']['race'],'after':after['clients']['race'],'root':after['root'],'configuration_changed':before!=after,'keys_changed':keys!=f.fixture.keys.read_text()}),flush=True)
finally:
 f.fixture.keys.parent.chmod(0o700);f.doCleanups()
