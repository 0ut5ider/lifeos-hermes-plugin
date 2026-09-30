# ABOUTME: Tests malformed arguments over an actual installed-copy MCP stdio connection.
# ABOUTME: Uses a synthetic writable project grant and records mutation and protocol outcomes.
import asyncio
import json
from pathlib import Path
import shutil
import sys
import tempfile
sys.path.insert(0,str(Path.cwd()))
sys.path.insert(0,str(Path.cwd()/'tests'))
from mcp import Client
from mcp.client.stdio import StdioServerParameters,stdio_client
from test_memory_service import MemoryServiceTests
from test_memory_native import OWNER
from lifeos_hook_bridge.memory_service import MemoryConfiguration

test=MemoryServiceTests(); test.setUp()
try:
    saved=test.fixture.remember()
    test.configuration['sharing_enabled']=True
    test.configuration['clients']['research']['write']=['project']
    MemoryConfiguration(test.config).save(test.configuration)
    installed=test.fixture.home/'plugins/lifeos-hook-bridge'
    shutil.copytree(Path.cwd()/'lifeos_hook_bridge',installed,ignore=shutil.ignore_patterns('__pycache__'))
    params=StdioServerParameters(command=sys.executable,args=[str(installed/'memory_mcp.py'),'--configuration',str(test.config),'--client','research'])
    arguments={'reference':saved['reference'],'request_id':'malformed-forget','dry_run':True}
    direct=test.service.call_client('research','lifeos_memory_forget',arguments)
    async def exercise():
        with tempfile.TemporaryFile(mode='w+') as errors:
            async with Client(stdio_client(params,errlog=errors),cache=None) as client:
                schemas=await client.list_tools()
                forget=next(tool for tool in schemas.tools if tool.name=='lifeos_memory_forget')
                output={'direct_forget':direct,'forget_schema':forget.model_dump(mode='json')}
                for key,name,args in [('boolean_limit','lifeos_memory_search',{'query':'synthetic','limit':True}),
                                      ('extra_write_argument','lifeos_memory_forget',arguments)]:
                    try:
                        result=await client.call_tool(name,args)
                        output[key]=result.model_dump(mode='json')
                    except Exception as error:
                        output[key]={'raised':type(error).__name__,'message':str(error)}
                output['native_record_after']=test.fixture.memory.get(OWNER,saved['reference'])
                # Exercise a genuine database failure over the same open connection.
                test.fixture.memory.database.write_bytes(b'synthetic invalid sqlite file')
                try:
                    result=await client.call_tool('lifeos_memory_search',{'query':'synthetic'})
                    output['database_failure']=result.model_dump(mode='json')
                except Exception as error:
                    output['database_failure']={'raised':type(error).__name__,'message':str(error)}
            errors.seek(0)
            output['server_stderr']=errors.read()
            print(json.dumps(output,sort_keys=True))
    asyncio.run(exercise())
finally:
    test.doCleanups()
