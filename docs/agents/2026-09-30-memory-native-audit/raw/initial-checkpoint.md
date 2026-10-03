# Native memory source audit

Date: 2026-09-30
Role: Independent source and synthetic fixture reviewer
Question: Which reachable native memory paths remain outside authorization, retained-claim filtering, or governed publication?
Model: GPT-6. The exact model variant is not exposed in this agent context.

## Incomplete checkpoint

This checkpoint is source evidence, not completed behavioral verification or activation approval. Public LifeOS base: 5e2f2e8c0abde612da0e99c16c0d07d4ec21b88c with distributed patches in source-gate-20260930-app-startup. Plugin review began at 2f0a84e.

Prioritized reachable candidates:

1. hooks/hooks.json registers MemoryTurnStart on UserPromptSubmit. MemoryTurnStart calls MemoryDeltaSurface.run, which reads memory-writes.jsonl directly, renders additions and evictions, and advances its cursor without connector authorization or retired-claim filtering. LoadMemory and MemoryRetriever siblings are delegated. Verify a real write then forget against the complete composer, both owner and missing context.
2. LIFEOS/PULSE/pulse.ts imports modules/memory.ts and forwards /api/memory requests. The module reads raw hot files via parseMemoryContent (which is a parser, not authorized read), pending proposals, health rows, and reviewer run paths. Proposal decision delegation in lib/memory-proposals.ts does not govern these sibling reads. Verify real handler output with managed connector and missing context. Server authentication and external reachability require separate tracing.
3. LIFEOS/TOOLS/MemoryInsights.ts prints recent proposal edit samples from raw JSONL. MemoryStatus.ts --json returns whole latest reviewer/retrieval rows despite narrow TypeScript interfaces. Verify retired native proposal/log claims and malformed connector outcomes.
4. LIFEOS/TOOLS/Cortex.ts runCortex enumerates raw canonical corpus for search/get/export/timeline/status/rebuild. Write commands use governed MemorySystem.add. CortexHealth imports the same raw enumeration for index digest. Verify actual canonical fixture reads, then distinguish hashes/counts from claim output.

No conclusion covers all 132 inventory candidates. Native tests are reference evidence; plugin behavioral coverage for these exact diagnostic and PULSE paths has not yet been found.
