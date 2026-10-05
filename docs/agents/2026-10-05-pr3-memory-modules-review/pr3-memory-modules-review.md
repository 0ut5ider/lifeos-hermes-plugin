2026-10-05 | Role: independent reviewer of unreviewed memory modules | Question: What real defects remain in the requested lasting-memory runtime modules at c083037 versus origin/main? | Model: GPT-6 (Codex)

## Findings

| Severity | File:line at c083037 | One-sentence defect | Concrete failure scenario | Confidence |
|---|---|---|---|---|
| High | `lifeos_hook_bridge/memory_service.py:570` | A client grant is checked only at call entry, so an in-flight read or write can finish after revocation. | A remote client starts a slow `lifeos_memory_search` or `lifeos_memory_remember`; the owner disables that client in the configuration while native ranking or validation runs; `_call` returns the fact or publishes the write under the old scope. | confirmed by reading |
| High | `patches/lifeos-memory-access.patch:6698` | Managed HTTP mode is remembered only in process memory, so a restart with both connector markers absent serves the original direct file routes. | After a managed install loses `memory-http.json` and `memory-access.json` during configuration drift, PULSE restarts while its HTTP port remains reachable; `hasManagedMemoryHTTP()` returns false, and `/api/memory` or `/api/wiki` falls through to unauthenticated native readers. | confirmed by reading |
| High | `lifeos_hook_bridge/memory_transaction.py:148` | Generic recovery restores journal copies without checking whether an owner edited a destination after the interrupted operation. | A write crashes after its journal is prepared, the owner edits the affected fact file, then any memory transaction runs recovery; because most operations omit `after_digest`, recovery replaces the owner's newer bytes with the old copy, and no backup of that newer edit is made. | confirmed by reading |
| Medium | `lifeos_hook_bridge/memory_freshness_migration.py:119` | A repeat context migration writes to the same fixed-name backup and can destroy the earlier pre-migration copy. | An owner changes a context file back to a form that needs migration and reruns the command; upstream `writeBackup` emits the same `*-2026-05-03-23-00-00.md` path, and `publish()` replaces its earlier contents. | confirmed by reading |
| Medium | `lifeos_hook_bridge/memory_service.py:82` | Proposal argument validation leaves every nested string and numeric field unbounded before passing the payload to the native worker. | A client with proposal creation permission submits a very large `edit` or `rationale`; the service accepts the nested object, serializes it for the Bun subprocess, and can exhaust memory or block its worker before native validation rejects it. | confirmed by reading |

## Coverage

- `lifeos_hook_bridge/memory_native.ts`: read fully.
- `lifeos_hook_bridge/memory_publication.ts`: read fully.
- `lifeos_hook_bridge/memory_runtime.py`: read fully.
- `lifeos_hook_bridge/memory_http.py`: read fully.
- `lifeos_hook_bridge/memory_mcp.py`: read fully.
- `lifeos_hook_bridge/memory_rpc.py`: read fully.
- `lifeos_hook_bridge/memory_service.py`: read fully.
- `lifeos_hook_bridge/memory_policy.py`: read fully.
- `lifeos_hook_bridge/memory_access.py`: read fully.
- `lifeos_hook_bridge/memory_transaction.py`: read fully.
- `lifeos_hook_bridge/memory_sources.py`: read fully.
- `lifeos_hook_bridge/memory_source_review.py`: read fully.
- `lifeos_hook_bridge/memory_prompt.py`: read fully.
- `lifeos_hook_bridge/memory_history.py`: read fully.
- `lifeos_hook_bridge/memory_lineage.py`: read fully.
- `lifeos_hook_bridge/memory_context_audit.py`: read fully.
- `lifeos_hook_bridge/memory_counts.py`: read fully.
- `lifeos_hook_bridge/memory_pulse_adapters.py`: read fully.
- `lifeos_hook_bridge/memory_pulse.py`: read fully.
- `lifeos_hook_bridge/memory_freshness.py`: read fully.
- `lifeos_hook_bridge/memory_freshness_cache.py`: read fully.
- `lifeos_hook_bridge/memory_freshness_migration.py`: read fully.
- `lifeos_hook_bridge/memory_distill.py`: read fully.
- `lifeos_hook_bridge/memory_hypotheses.py`: read fully.
- `lifeos_hook_bridge/memory_wisdom.py`: read fully.
- `lifeos_hook_bridge/memory_interview.py`: read fully.
- `lifeos_hook_bridge/memory_interview_scan.py`: read fully.
- `lifeos_hook_bridge/memory_learning.py`: read fully.
- `lifeos_hook_bridge/memory_recurrence.py`: read fully.
- `lifeos_hook_bridge/memory_seed.py`: read fully.
- `lifeos_hook_bridge/memory_state.py`: read fully.
- `lifeos_hook_bridge/memory_telos.py`: read fully.
- `lifeos_hook_bridge/memory_graph.py`: read fully.
- `lifeos_hook_bridge/memory_evidence.py`: read fully.
- `lifeos_hook_bridge/memory_deny_hashes.py`: read fully.
- `lifeos_hook_bridge/memory_derived_sync.py`: read fully.
- `patches/lifeos-memory-access.patch`: read partially, including the managed HTTP and source-access gates at patch lines 370-525, 1110-1200, 1460-1520, the migration publication changes at 4685-4950, the MemoryAccess helper at 6520-6730, and hook call sites at 6728-6830; the rest of the 7,103-line patch was not read line by line.

## No defect found

`lifeos_hook_bridge/memory_native.ts`, `lifeos_hook_bridge/memory_publication.ts`, `lifeos_hook_bridge/memory_runtime.py`, `lifeos_hook_bridge/memory_http.py`, `lifeos_hook_bridge/memory_mcp.py`, `lifeos_hook_bridge/memory_rpc.py`, `lifeos_hook_bridge/memory_policy.py`, `lifeos_hook_bridge/memory_access.py`, `lifeos_hook_bridge/memory_sources.py`, `lifeos_hook_bridge/memory_source_review.py`, `lifeos_hook_bridge/memory_prompt.py`, `lifeos_hook_bridge/memory_history.py`, `lifeos_hook_bridge/memory_lineage.py`, `lifeos_hook_bridge/memory_context_audit.py`, `lifeos_hook_bridge/memory_counts.py`, `lifeos_hook_bridge/memory_pulse_adapters.py`, `lifeos_hook_bridge/memory_pulse.py`, `lifeos_hook_bridge/memory_freshness.py`, `lifeos_hook_bridge/memory_freshness_cache.py`, `lifeos_hook_bridge/memory_distill.py`, `lifeos_hook_bridge/memory_hypotheses.py`, `lifeos_hook_bridge/memory_wisdom.py`, `lifeos_hook_bridge/memory_interview.py`, `lifeos_hook_bridge/memory_interview_scan.py`, `lifeos_hook_bridge/memory_learning.py`, `lifeos_hook_bridge/memory_recurrence.py`, `lifeos_hook_bridge/memory_seed.py`, `lifeos_hook_bridge/memory_state.py`, `lifeos_hook_bridge/memory_telos.py`, `lifeos_hook_bridge/memory_graph.py`, `lifeos_hook_bridge/memory_evidence.py`, `lifeos_hook_bridge/memory_deny_hashes.py`, `lifeos_hook_bridge/memory_derived_sync.py`.

The review used commit snapshots and diffs only. Test suites were not run because they require private fixtures. No repository code was changed.
