# ABOUTME: Probes service grant snapshots and error outcomes using temporary native stores.
# ABOUTME: Uses real configuration files and native operations with controlled scheduling points.
import copy
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path.cwd()))
sys.path.insert(0,str(Path.cwd()/'tests'))
from test_memory_service import MemoryServiceTests
from test_memory_native import NativeMemoryTests,OWNER
from lifeos_hook_bridge.memory_service import MemoryConfiguration,MemoryService

def run(name,callback):
    test=MemoryServiceTests(); test.setUp()
    try: print(json.dumps({'case':name,'result':callback(test)},sort_keys=True))
    finally: test.doCleanups()

def mixed_configuration(test):
    other=NativeMemoryTests(); other.setUp()
    try:
        other.remember('Synthetic newly private root marker','private-root')
        test.configuration['sharing_enabled']=True
        MemoryConfiguration(test.config).save(test.configuration)
        replacement=copy.deepcopy(test.configuration)
        replacement['sharing_enabled']=False
        replacement['root']=str(other.root)
        class RotateAfterRead(MemoryConfiguration):
            loads=0
            def load(self):
                config=super().load()
                self.loads+=1
                if self.loads==1: MemoryConfiguration(self.path).save(replacement)
                return config
        service=MemoryService(RotateAfterRead(test.config))
        first=service.call_client('research','lifeos_memory_search',{'query':'private root'})
        second=service.call_client('research','lifeos_memory_search',{'query':'private root'})
        return {'first_call':first,'second_call':second}
    finally: other.doCleanups()

def corrupt_database(test):
    saved=test.fixture.remember()
    test.fixture.memory.database.write_bytes(b'synthetic invalid sqlite file')
    result={'status':test.service.call(OWNER,'lifeos_memory_status',{})}
    for name,arguments in [('lifeos_memory_search',{'query':'synthetic'}),('lifeos_memory_get',{'reference':saved['reference']})]:
        try: result[name]=test.service.call(OWNER,name,arguments)
        except Exception as error: result[name]={'raised':type(error).__name__,'message':str(error)}
    return result

run('mixed_configuration_revision',mixed_configuration)
run('database_unavailable_contract',corrupt_database)
