# ABOUTME: Checks native canonical reads in a disposable managed profile without caller context.
# ABOUTME: Records the alternative reader behavior without reading installed user data.
import json
import os
import subprocess
from pathlib import Path

from test_memory_delegation import MemoryDelegationTests

fixture=MemoryDelegationTests();fixture.setUp()
try:
    fixture.fixture.remember('SyntheticCanonicalReaderScopeMarker','canonical-reader-probe','project')
    module=fixture.root/'LIFEOS/TOOLS/Cortex.ts'
    program='import {loadCanonicalRecords,runCortex} from '+json.dumps(str(module))+';\n' \
        +'const root='+json.dumps(str(fixture.root/'LIFEOS/MEMORY'))+';\n' \
        +'const records=loadCanonicalRecords(root); const result=await runCortex(["get",records[0].id,"--memory-root",root]);\n' \
        +'console.log(JSON.stringify(result));'
    environment=dict(os.environ,HOME=str(fixture.fixture.home),BUN_CONFIG_NO_AUTO_INSTALL='1')
    environment.pop('LIFEOS_MEMORY_CONTEXT',None)
    environment.pop('LIFEOS_MEMORY_INTERNAL',None)
    process=subprocess.run(['bun','--no-install','-e',program],env=environment,capture_output=True,text=True,timeout=30)
    assert process.returncode==0,process.stderr
    assert process.stderr=='',process.stderr
    result=json.loads(process.stdout)
    print(json.dumps({'managed_connector_exists':(fixture.root/'LIFEOS/USER/CONFIG/memory-access.json').exists(),
        'caller_context_present':'LIFEOS_MEMORY_CONTEXT' in environment,'exit_code':result['exitCode'],
        'marker_exposed':'SyntheticCanonicalReaderScopeMarker' in process.stdout,'result':result},indent=2))
finally:fixture.doCleanups()
