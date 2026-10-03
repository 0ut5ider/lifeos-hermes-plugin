# ABOUTME: Measures native delta filtering cost against real append-only write logs.
# ABOUTME: Runs an authorized native composer in private fixtures with controlled row counts.
import json,os,subprocess,time
from dataclasses import asdict
from test_memory_delegation import MemoryDelegationTests
from test_memory_native import SOURCE
f=MemoryDelegationTests();f.setUp()
try:
 f.fixture.remember('RULE: synthetic audit current volume marker','volume','principal')
 obs=f.root/'LIFEOS/MEMORY/OBSERVABILITY';log=obs/'memory-writes.jsonl';row=json.loads(log.read_text().splitlines()[-1])
 env=dict(os.environ,HOME=str(f.fixture.home),BUN_CONFIG_NO_AUTO_INSTALL='1',LIFEOS_MEMORY_CONTEXT=json.dumps(asdict(f.context)))
 for name in ['LIFEOS_MEMORY_INTERNAL','CLAUDE_AGENT_TYPE','CLAUDE_CODE_SUBAGENT_NAME','CLAUDE_CODE_SUBAGENT_TYPE','CLAUDE_CODE_FORK_SUBAGENT','CLAUDE_AGENT_SDK','CLAUDE_PROJECT_DIR']:env.pop(name,None)
 for count in [1,100,500]:
  log.write_text(''.join(json.dumps(dict(row,ts=f'2026-09-{1+i//24:02}T{i%24:02}:00:00Z'))+'\n' for i in range(count)))
  cursor=obs/'memory-delta-cursor.json'
  if cursor.exists():cursor.unlink()
  t=time.monotonic()
  p=subprocess.run([f.fixture.memory.bun,'--no-install',str(SOURCE/'hooks/MemoryTurnStart.hook.ts')],input=json.dumps({'session_id':f'volume-{count}','prompt':''}),text=True,capture_output=True,cwd=f.root,env=env,timeout=50)
  print(json.dumps({'rows':count,'bytes':log.stat().st_size,'seconds':time.monotonic()-t,'configured_hook_timeout_seconds':8,'code':p.returncode,'stdout':p.stdout,'stderr':p.stderr}),flush=True)
finally:f.doCleanups()
