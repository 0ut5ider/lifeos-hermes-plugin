# ABOUTME: Verifies governed health denial, native severity parity, and Stop-hook publication.
# ABOUTME: Exercises synthetic fixtures and records raw commands and diagnostic outcomes.
import json,os,subprocess,time
from dataclasses import replace,asdict
from test_memory_cortex_health import MemoryCortexHealthTests
from lifeos_hook_bridge.memory_service import MemoryService

c=MemoryCortexHealthTests();c.setUp()
try:
 c.reviewer('Synthetic current control failure')
 original=c.fixture.context
 for label,context in [('unknown',replace(original,author='unknown')),('changed-route',replace(original,model_route='other'))]:
  c.fixture.context=context
  collector=c.call();result,report=c.health()
  assert collector=={'unavailable':True} and 'unavailable' in report
  assert not (c.obs/'memory-health.jsonl').exists()
  print(json.dumps({'case':label,'collector':collector,'health':report,'exit':result.returncode}),flush=True)
 c.fixture.context=original
 config=c.fixture.configuration.load();saved=json.loads(json.dumps(config));config['destinations']['chat-a:200']['read']=['project'];c.fixture.configuration.save(config)
 result,report=c.health();assert 'unavailable' in report and not (c.obs/'memory-health.jsonl').exists()
 print(json.dumps({'case':'restricted','health':report}),flush=True)
 c.fixture.configuration.save(saved)
 connector=c.root/'LIFEOS/USER/CONFIG/memory-access.json';cfg=connector.read_bytes();connector.unlink();connector.symlink_to(connector.parent/'missing-synthetic-connector')
 result,report=c.health();assert 'unavailable' in report and not (c.obs/'memory-health.jsonl').exists()
 print(json.dumps({'case':'broken-connector','health':report}),flush=True)
 connector.unlink();connector.write_bytes(cfg);connector.chmod(0o600)
 hot=c.root/'LIFEOS/USER/PRINCIPAL/PRINCIPAL_MEMORY.md'
 saved=c.fixture.fixture.remember('RULE: Synthetic current valid health fact','valid-hot','principal');assert saved['status']=='committed'
 hot.write_text(hot.read_text().replace('<!-- END ENTRIES -->','RULE: Synthetic invalid control '+'x'*300+'\n<!-- END ENTRIES -->'))
 service=MemoryService(c.fixture.configuration)
 diagnostic=service.native(original,'diagnose_hot',{'path':str(hot)})
 ordinary=service.native(original,'read',{'path':str(hot)})
 assert diagnostic['ok'] and len(diagnostic['dropped_invalid'])==1 and 'entries' not in diagnostic
 assert 'Synthetic current valid health fact' not in json.dumps(diagnostic)
 assert not ordinary.get('ok',False)
 print(json.dumps({'case':'invalid-hot-boundary','diagnostic':diagnostic,'ordinary':ordinary}),flush=True)
 managed_result,managed=c.health();(c.obs/'memory-health.jsonl').unlink()
 connector.unlink();unmanaged_result,unmanaged=c.health(context=False)
 assert managed['counts']==unmanaged['counts']
 assert [(x['id'],x['severity']) for x in managed['findings']]==[(x['id'],x['severity']) for x in unmanaged['findings']]
 print(json.dumps({'case':'native-severity-parity','managed_counts':managed['counts'],'unmanaged_counts':unmanaged['counts'],'managed_findings':managed['findings'],'unmanaged_findings':unmanaged['findings']}),flush=True)
 connector.write_bytes(cfg);connector.chmod(0o600);(c.obs/'memory-health.jsonl').unlink()
 env=dict(os.environ,HOME=str(c.fixture.fixture.home),BUN_CONFIG_NO_AUTO_INSTALL='1',LIFEOS_MEMORY_CONTEXT=json.dumps(asdict(original)))
 for key in ('LIFEOS_MEMORY_INTERNAL','CORTEX_HEALTH_ROOT','CORTEX_INDEX_MANIFEST','CORTEX_HEALTH_NOW','CORTEX_HEALTH_NO_WRITE','CORTEX_HEALTH_REPORT_PATH'):env.pop(key,None)
 start=time.monotonic();r=subprocess.run(['bun','--no-install',str(c.root/'hooks/MemoryHealthGate.hook.ts')],env=env,cwd=c.root,capture_output=True,text=True,timeout=6)
 elapsed=time.monotonic()-start
 assert r.returncode==0 and r.stdout=='' and 'Memory health: CRITICAL' in r.stderr
 assert (c.obs/'memory-health.jsonl').exists()
 print(json.dumps({'case':'actual-health-gate','seconds':elapsed,'returncode':r.returncode,'stdout':r.stdout,'stderr':r.stderr,'published':True}),flush=True)
finally:c.doCleanups()
