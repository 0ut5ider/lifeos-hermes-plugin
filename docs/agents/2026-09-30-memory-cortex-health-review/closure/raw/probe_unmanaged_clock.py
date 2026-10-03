# ABOUTME: Compares unchanged standalone exception behavior with the managed CLI wrapper.
# ABOUTME: Runs owned initial/current public sources against one private fixture.
from test_memory_cortex_health import MemoryCortexHealthTests
from dataclasses import asdict
from pathlib import Path
import json,os,subprocess
c=MemoryCortexHealthTests();c.setUp()
try:
 c.reviewer('Synthetic invalid-clock baseline')
 current=c.root/'LIFEOS/TOOLS/MemoryHealthCheck.ts'
 baseline=Path('/home/outsider/.cache/lifeos-plugin-memory/source-gate-20260930-cortex-health/lifeos/LifeOS/install/LIFEOS/TOOLS/MemoryHealthCheck.ts')
 connector=c.root/'LIFEOS/USER/CONFIG/memory-access.json';cfg=connector.read_bytes()
 env=dict(os.environ,HOME=str(c.fixture.fixture.home),BUN_CONFIG_NO_AUTO_INSTALL='1',CORTEX_HEALTH_NOW='synthetic-invalid-clock')
 for key in ('LIFEOS_MEMORY_INTERNAL','LIFEOS_MEMORY_CONTEXT','CORTEX_HEALTH_ROOT','CORTEX_INDEX_MANIFEST','CORTEX_HEALTH_NO_WRITE','CORTEX_HEALTH_REPORT_PATH'):env.pop(key,None)
 outcomes=[]
 connector.unlink()
 for name,script in [('initial-unmanaged',baseline),('current-unmanaged',current)]:
  result=subprocess.run(['bun','--no-install',str(script)],env=env,cwd=c.root,text=True,capture_output=True,timeout=5)
  outcomes.append({'case':name,'argv':['bun','--no-install',str(script)],'returncode':result.returncode,'stdout':result.stdout,'stderr':result.stderr,'published':(c.obs/'memory-health.jsonl').exists()})
 connector.write_bytes(cfg);connector.chmod(0o600);env['LIFEOS_MEMORY_CONTEXT']=json.dumps(asdict(c.fixture.context))
 result=subprocess.run(['bun','--no-install',str(current)],env=env,cwd=c.root,text=True,capture_output=True,timeout=5)
 outcomes.append({'case':'current-managed','returncode':result.returncode,'stdout':result.stdout,'stderr':result.stderr,'published':(c.obs/'memory-health.jsonl').exists()})
 print(json.dumps(outcomes))
finally:c.doCleanups()
