# ABOUTME: Checks the RPC byte ceiling with full native curation log rows.
# ABOUTME: Uses real native row generation and a disposable approved owner fixture.
import json,os,subprocess,time
from dataclasses import asdict
from test_memory_delegation import MemoryDelegationTests
from test_memory_native import OWNER,SOURCE
f=MemoryDelegationTests();f.setUp()
try:
 entries=[f'RULE: Synthetic capacity record {i:02} '+('archive detail '*14).strip() for i in range(40)]
 snapshot=f.fixture.memory.read_hot(OWNER,'principal')
 saved=f.fixture.memory.native_set(OWNER,'principal',entries,'capacity',snapshot['revision'])
 assert saved['ok'],saved
 log=f.root/'LIFEOS/MEMORY/OBSERVABILITY/memory-writes.jsonl';native_row=log.read_text().splitlines()[-1]
 current=f.fixture.remember('RULE: Synthetic current byte control','byte-control','principal');assert current['status']=='committed',current
 control=log.read_text().splitlines()[-1]
 log.write_text((native_row+'\n')*499+control+'\n')
 env=dict(os.environ,HOME=str(f.fixture.home),BUN_CONFIG_NO_AUTO_INSTALL='1',LIFEOS_MEMORY_CONTEXT=json.dumps(asdict(f.context)))
 for name in ['LIFEOS_MEMORY_INTERNAL','CLAUDE_AGENT_TYPE','CLAUDE_CODE_SUBAGENT_NAME','CLAUDE_CODE_SUBAGENT_TYPE','CLAUDE_CODE_FORK_SUBAGENT','CLAUDE_AGENT_SDK','CLAUDE_PROJECT_DIR']:env.pop(name,None)
 t=time.monotonic()
 p=subprocess.run([f.fixture.memory.bun,'--no-install',str(SOURCE/'hooks/MemoryDeltaSurface.hook.ts')],text=True,capture_output=True,cwd=f.root,env=env,timeout=45)
 print(json.dumps({'row_count':500,'row_bytes':len(native_row.encode()),'entries_per_row':len(entries),'entry_chars':len(entries[0]),'log_bytes':log.stat().st_size,'seconds':time.monotonic()-t,'code':p.returncode,'stdout':p.stdout,'stderr':p.stderr,'native_curation_committed':saved['receipt']['status'],'current_committed':current['status']}))
 from lifeos_hook_bridge.memory_service import MemoryService
 direct=MemoryService(f.configuration).native(f.context,'read_source',{'path':str(log)})
 print(json.dumps({'case':'direct_service_response','ok':direct.get('ok'),'content_bytes':len(direct.get('content','').encode()),'rpc_serialized_bytes':len((json.dumps(direct)+'\n').encode()),'contains_current': 'Synthetic current byte control' in direct.get('content',''),'rpc_max_buffer':4*1024*1024}))
finally:f.doCleanups()
