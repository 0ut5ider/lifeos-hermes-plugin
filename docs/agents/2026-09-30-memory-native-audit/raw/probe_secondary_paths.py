# ABOUTME: Checks real native diagnostic, staged publication, and wiki consumers.
# ABOUTME: Uses synthetic retained records and never invokes a model or external server.
import os,json,subprocess
from datetime import datetime,timezone
from test_memory_delegation import MemoryDelegationTests
from test_memory_native import SOURCE,OWNER
f=MemoryDelegationTests();f.setUp()
try:
 marker='RULE: synthetic audit forgotten albatross marker'
 r=f.fixture.remember(marker,'audit-retired','principal');f.fixture.memory.forget(OWNER,r['reference'],'forget')
 env=dict(os.environ,HOME=str(f.fixture.home),LIFEOS_DIR=str(f.root/'LIFEOS'),BUN_CONFIG_NO_AUTO_INSTALL='1')
 env.pop('LIFEOS_MEMORY_CONTEXT',None);env.pop('LIFEOS_MEMORY_INTERNAL',None)
 def run(label,args):
  p=subprocess.run([f.fixture.memory.bun,'--no-install',*args],text=True,capture_output=True,env=env,cwd=f.root,timeout=45)
  print(json.dumps({'case':label,'argv':args,'code':p.returncode,'stdout':p.stdout,'stderr':p.stderr}))
 obs=f.root/'LIFEOS/MEMORY/OBSERVABILITY'
 (obs/'reviewer-runs.jsonl').write_text(json.dumps({'ts':datetime.now(timezone.utc).isoformat(),'ok':False,'error':marker})+'\n')
 run('cortex_health_retained_error',['-e',f'const m=await import({json.dumps(str(SOURCE/"LIFEOS/TOOLS/CortexHealth.ts"))}); console.log(JSON.stringify(m.collectCortexEvidence({{root:{json.dumps(str(f.root))}}})));'])
 staged=f.root/'LIFEOS/MEMORY/KNOWLEDGE/_harvest-queue/Research/audit-retained.md';staged.parent.mkdir(parents=True)
 staged.write_text('---\ntype: research\ntitle: '+marker+'\ncreated: 2026-01-01\nstatus: pending-review\n---\n'+marker+'\n')
 run('harvester_promote_without_context',[str(SOURCE/'LIFEOS/TOOLS/KnowledgeHarvester.ts'),'promote','Research/audit-retained'])
 target=f.root/'LIFEOS/MEMORY/KNOWLEDGE/Research/audit-retained.md'
 print(json.dumps({'case':'promoted_bytes','published':target.exists(),'retired_quote_published':target.exists() and marker in target.read_text(),'staged_removed':not staged.exists(),'governed_recall':f.fixture.memory.recall(OWNER,'albatross')}))
 run('knowledge_query_without_context',[str(SOURCE/'LIFEOS/TOOLS/KnowledgeQuery.ts'),'--json'])
 source=json.dumps(str(SOURCE/'LIFEOS/PULSE/modules/wiki.ts'))
 run('wiki_without_context',['-e',f'const m=await import({source}); await m.handleWikiRequest(new Request("http://localhost/api/wiki/reindex"),"/api/wiki/reindex"); const r=await m.handleWikiRequest(new Request("http://localhost/api/wiki/knowledge/Research/audit-retained"),"/api/wiki/knowledge/Research/audit-retained"); console.log(await r.text());'])
finally:f.doCleanups()
