# Review inventory

Date: 2026-10-01. Role: independent implementation reviewer. Model: GPT-6.1-Sol, inherited high reasoning.

Reviewed design: notes/2026-09-30-memory-design.md and docs/memory-implementation-plan.md. Reviewed initial source: d1a919e28ebcf43ea68163424aa1faa841b60bd2 on feature/lifeos-memory. Subsequent 8dc1b42 changes documentation and previous evidence only.

Implementation reads: memory_access.py, memory_service.py, memory_policy.py, memory_transaction.py, memory_adoption.py, memory_proposals.py, memory_sources.py, memory_diagnostics.py, memory_pulse.py, memory_context.py, memory_runtime.py, memory_history.py, memory_provider.py, memory_rpc.py, memory_mcp.py, memory_sharing.py, memory_preferences.py, dashboard/plugin_api.py, __init__.py, memory_native.ts, memory_publication.ts. Read the changed commits and preceding correction review. These are interface and implementation reads, with portions of long files selected by dependency and identified risk. The archive does not establish exhaustive line coverage.

Prepared native reads: MemoryWriter.ts publication/validation/cap/guards/logging; MemoryHealthCheck.ts diagnostic construction sites; MemoryAccess.ts interface declarations through the distributed patch; patch diff inventory for 17 native files. Prepared host interfaces are exercised through existing fixtures. No whole native source inventory coverage is claimed.

Independent probes: probe_hot_neighbors.py, probe_schema_provenance.py, and probe_delta_and_grants.py copied unchanged from the preceding review. New probes: probe_recovery_delta.py and probe_recovery_journal_hypothesis.py. New probe uses an actual native child process interrupted with exit 73 after native publication and before registry _record, then performs genuine journal recovery and registered MemoryTurnStart composition. The capture hypothesis uses a disposable subclass, with no implementation changes.

Targeted baseline gate: run-baseline-targeted.sh executes curation, authorization, delegation, delta, and Cortex health modules from the archived baseline checkout. This avoids contamination from primary corrections. The primary reports a separate 321-case expanded gate; this reviewer has not rerun that gate and does not adopt it as independent evidence.

Safety limits: only disposable synthetic HOME fixtures and owned prepared public source are used. No existing installation, server, credential, memory store, memory/journal MCP tool, dependency installation, real model provider, commit, push, or deployment is used. Deterministic local HTTP fixtures used by existing modules are permitted. No new subprocess imports an existing Hermes installation.

Public source revision: LifeOS 5e2f2e8c0abde612da0e99c16c0d07d4ec21b88c; Hermes 758ad514eb0e800547e015edf05aa18f78b78d82. Both prepared sources contain the previously applied public owned patches. public-source-hashes.json records the 17 native patch destinations and nine host files. It is not a whole-tree hash manifest.
