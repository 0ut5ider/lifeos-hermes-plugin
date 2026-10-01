# ABOUTME: Captures native diagnostic output from a governed synthetic LifeOS profile.
# ABOUTME: Checks whether raw observability fields reintroduce an excluded exact claim.
from dataclasses import asdict
import json,os,subprocess,sys
from pathlib import Path
repository=Path('/home/outsider/Projects/Hermes_agent/LifeOS_plugin')
sys.path[:0]=[str(repository),str(repository/'tests')]
from test_memory_runtime import MemoryRuntimeTests
from test_memory_native import OWNER
case=MemoryRuntimeTests();case.setUp()
try:
 native=case.fixture
 marker='Synthetic forgotten native diagnostic claim'
 saved=native.remember(marker,'diagnostic-original')
 native.memory.forget(OWNER,saved['reference'],'diagnostic-forget')
 case.admit()
 connector=native.root/'LIFEOS/USER/CONFIG/memory-access.json'
 connector.parent.mkdir(exist_ok=True)
 connector.write_text(json.dumps({'version':1,'command':[sys.executable,str(repository/'lifeos_hook_bridge/memory_rpc.py'),'--configuration',str(case.path)]}))
 connector.chmod(0o600)
 observations=native.root/'LIFEOS/MEMORY/OBSERVABILITY'
 observations.mkdir(exist_ok=True)
 (observations/'reviewer-runs.jsonl').write_text(json.dumps({'ts':'2026-09-30T12:00:00Z','ok':True,'content':marker})+'\n')
 environment={key:os.environ[key] for key in ('PATH','LANG','TZ') if key in os.environ}
 environment.update(HOME=str(native.home),BUN_CONFIG_NO_AUTO_INSTALL='1')
 case.runtime.bind_environment(environment,session_id='session')
 result=subprocess.run(['bun','--no-install',str(native.root/'LIFEOS/TOOLS/MemoryStatus.ts'),'--json'],env=environment,capture_output=True,text=True,timeout=30)
 print(json.dumps({'returncode':result.returncode,'stdout':result.stdout,'stderr':result.stderr,'marker_in_stdout':marker in result.stdout,'ordinary_recall':native.memory.recall(OWNER,'diagnostic claim')},indent=2))
 assert result.returncode==0 and result.stderr=='',result
finally:case.doCleanups()
