# ABOUTME: Captures public source hashes and audit triage without reading user data.
# ABOUTME: Keeps inspected source snapshots and marks untraced inventory candidates explicitly.
import json,hashlib,shutil,csv,subprocess
from pathlib import Path
root=Path('/home/outsider/Projects/Hermes_agent/LifeOS_plugin')
source=Path('/home/outsider/.cache/lifeos-plugin-memory/source-gate-20260930-app-startup/lifeos/LifeOS/install')
out=root/'docs/agents/2026-09-30-memory-native-audit/raw'
traced={
 'hooks/MemoryTurnStart.hook.ts':'confirmed: composed delta bypass; delegated hot/retrieval siblings',
 'hooks/MemoryDeltaSurface.hook.ts':'confirmed: native retired additions exposed; cursor side effect',
 'hooks/LoadMemory.hook.ts':'existing behavioral tests: governed hot read',
 'hooks/LoadContext.hook.ts':'existing behavioral tests: retained dynamic source reads; static scope open',
 'hooks/lib/learning-readback.ts':'existing behavioral tests: five retained readers',
 'hooks/lib/advisory-readback.ts':'existing behavioral tests: attested path and findings',
 'hooks/MemoryReviewFire.hook.ts':'source traced: Stop cadence spawns reviewer with inherited context',
 'hooks/MemoryHealthGate.hook.ts':'source traced: health subprocess counts only emitted by gate',
 'LIFEOS/TOOLS/MemoryStatus.ts':'confirmed: whole raw diagnostic JSON row',
 'LIFEOS/TOOLS/MemoryInsights.ts':'confirmed: retained proposal edit sample',
 'LIFEOS/TOOLS/CortexHealth.ts':'confirmed: retained reviewer error; digest reads source traced',
 'LIFEOS/TOOLS/MemoryHealthCheck.ts':'source traced: embeds Cortex evidence and writes health log',
 'LIFEOS/TOOLS/Cortex.ts':'confirmed: unknown/retired corpus get; governed write sibling',
 'LIFEOS/TOOLS/MemoryRestore.ts':'confirmed: raw snapshot restore invalidates managed current reference',
 'LIFEOS/TOOLS/MemorySystem.ts':'source traced + existing tests: add/find governed; smoke raw restore remaining',
 'LIFEOS/TOOLS/MemoryWriter.ts':'existing behavioral tests: read/set delegation CAS; parser has no authorization',
 'LIFEOS/TOOLS/MemoryReviewer.ts':'source traced + existing tests: filtered input, delegated dispatch/auto decisions; whole detached lifecycle open',
 'LIFEOS/TOOLS/MemoryRetriever.ts':'existing behavioral tests: supplied authorized corpus; raw discovery is internal capability',
 'LIFEOS/TOOLS/lib/MemoryAccess.ts':'source traced + existing tests: strict connector; no-connector standalone',
 'LIFEOS/PULSE/lib/memory-proposals.ts':'existing behavioral tests: queue/decision delegation and raw writer refusal',
 'LIFEOS/PULSE/modules/memory.ts':'confirmed: request handler hot/proposal raw output',
 'LIFEOS/PULSE/lib/lifeos-context.ts':'confirmed: identity bypass; no-query cache retains authorized hot content',
 'LIFEOS/PULSE/edit/edit-handler.ts':'confirmed exported raw write; no production caller found',
 'LIFEOS/PULSE/modules/wiki.ts':'source traced raw index/body routes; execution blocked by missing minisearch',
 'LIFEOS/PULSE/Observability/observability.ts':'source traced graph cache to HTTP; behavior not tested',
 'LIFEOS/TOOLS/KnowledgeHarvester.ts':'confirmed: promote publishes forgotten unregistered text; other commands source partial',
 'LIFEOS/TOOLS/KnowledgeQuery.ts':'confirmed: forgotten native title returned; reads raw frontmatter',
 'LIFEOS/TOOLS/ProposalGC.ts':'source traced: scheduled raw target rewrite; registry/concurrency behavior untested',
 'LIFEOS/TOOLS/LearningPatternSynthesis.ts':'source partial: scheduled reader/derived writer/inference; boundary untested',
 'LIFEOS/TOOLS/SessionHarvester.ts':'source partial: scheduled transcript reader/queue writer; boundary untested',
 'LIFEOS/TOOLS/MemoryGraph.ts':'source partial: raw multi-silo graph builder; output consumer traced',
 'hooks/WorkCompletionLearning.hook.ts':'source partial: registered learning capture raw writer; downstream reads gated',
 'hooks/SatisfactionCapture.hook.ts':'source partial: registered feedback capture raw writer; downstream reads gated',
 'LIFEOS/PULSE/modules/hypotheses.ts':'source partial: raw frame decisions; further decision route probe needed',
 'LIFEOS/PULSE/modules/work.ts':'source partial: raw ISA title/cache; no behavior claim',
 'LIFEOS/PULSE/modules/upgrades.ts':'source partial: Upgrades/hypothesis API; needs own grant binding audit',
 'LIFEOS/TOOLS/Inference.ts':'source traced: external claude subprocess; managed adapter model-route gate evidence separate'
}
extras=['hooks/hooks.json','hooks/lib/subagent.ts','LIFEOS/PULSE/pulse.ts','LIFEOS/PULSE/modules/siri.ts','LIFEOS/PULSE/PULSE.toml','LIFEOS/TOOLS/CortexAdapter.ts','LIFEOS/DOCUMENTATION/Memory/MemorySystem.md','LIFEOS/DOCUMENTATION/Memory/CortexContract.md']
rows=json.loads((root/'docs/verification/2026-09-30-memory-native-inventory/candidate-paths.json').read_text())
paths=sorted({r['path'] for r in rows}|set(extras))
hashes={}
for rel in paths:
 p=source/rel
 hashes[rel]=hashlib.sha256(p.read_bytes()).hexdigest()
 if rel in traced or rel in extras:
  dest=out/'sources'/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,dest)
(out/'native-source-hashes.json').write_text(json.dumps(hashes,indent=2)+'\n')
with (out/'inventory-triage.csv').open('w') as f:
 w=csv.writer(f);w.writerow(['path','audit_status'])
 for row in rows:w.writerow([row['path'],traced.get(row['path'],'untraced candidate: no coverage conclusion')])
plugin=['patches/lifeos-memory-access.patch','lifeos_hook_bridge/patches/lifeos-memory-access.patch','lifeos_hook_bridge/memory_access.py','lifeos_hook_bridge/memory_sources.py','lifeos_hook_bridge/memory_service.py','tests/test_memory_native.py','tests/test_memory_delegation.py','tests/test_memory_sources.py','tests/test_memory_proposal_delegation.py']
ph={p:hashlib.sha256((root/p).read_bytes()).hexdigest() for p in plugin}
(out/'plugin-source-hashes.json').write_text(json.dumps(ph,indent=2)+'\n')
meta={'native_base':'5e2f2e8c0abde612da0e99c16c0d07d4ec21b88c','prepared_source':str(source),'plugin_head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(),'plugin_branch':subprocess.check_output(['git','branch','--show-current'],cwd=root,text=True).strip(),'inventory_candidates':len(rows),'candidates_with_partial_or_better_traces':len(traced),'extra_source_paths':extras,'untraced_count':len(rows)-len(traced),'paired_patch_equal':ph[plugin[0]]==ph[plugin[1]]}
(out/'source-metadata.json').write_text(json.dumps(meta,indent=2)+'\n');print(json.dumps(meta))
