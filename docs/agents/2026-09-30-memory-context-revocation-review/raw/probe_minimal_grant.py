# ABOUTME: Captures the server response for a valid minimal client grant.
# ABOUTME: Uses only a disposable native fixture and private configuration.
from pathlib import Path
import sys,json
sys.path.insert(0,str(Path.cwd()));sys.path.insert(0,str(Path.cwd()/'tests'))
from test_memory_preferences import MemoryPreferencesTests
from lifeos_hook_bridge.memory_service import MemoryConfiguration
f=MemoryPreferencesTests();f.setUp()
try:
 config=MemoryConfiguration(f.fixture.fixture.config)
 config.update(lambda value:value.update(clients={'minimal':{'enabled':False}}))
 print(json.dumps({'validated_configuration':config.load(),'status':f.preferences.status()},indent=2))
finally:f.doCleanups()
