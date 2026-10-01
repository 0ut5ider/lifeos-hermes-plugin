# Review reading and command inventory

Date: 2026-10-01. This list records what informed the report. Snapshots do not imply complete review.

Instructions read: `/home/outsider/.agents/AGENTS.md`, coding-rules/SKILL.md, coding-rules/references/javascript.md. The supplied user instructions and parent task constrain this review. No additional project AGENTS.md was found in this repository.

Complete small-module reads: memory_policy.py, memory_rpc.py, memory_native.ts, memory_sources.py, memory_adoption.py, memory_preferences.py, memory_provider.py, memory_transaction.py, memory_publication.ts, memory_sharing.py, memory_mcp.py, memory_context.py, memory_history.py, native_capabilities.py, tests/native_memory_calls.ts. A few combined command outputs were truncated; claims rely on the visible relevant sections and later focused reads.

Focused code reads:

- memory_access.py: constructor/boundary/connection/transaction/native-worker/path/permissions/content/validation/archive sections; records/operation/publication-path sections; hot snapshot/curation/native add/remember/recall/corpus/relevant context/filter history/target/get/correct/forget. Particular verified lines are listed in the report. No exhaustive every-line audit claim.
- memory_service.py: schemas/argument checks/config validation/locking/native dispatch/client scope/context service/tool dispatch. Tool-dispatch output tail was truncated.
- memory_runtime.py: rendered/input helpers, admission/state/context, configuration and stamp, environment binding, primary and auxiliary request checks and history projection. Reviewed through displayed sections, with output truncation disclosed.
- memory_diagnostics.py: fixed/dynamic field and metadata-path classification, numeric/enum projection, read/diagnose/filter report. Full snapshot preserved; focused schema and filtering regions re-read.
- memory_pulse.py: complete owner snapshot, physical source attestation, runs, hot entries, cadence, diagnostic view projection.
- dashboard/plugin_api.py: lines1-185, actual memory routes, middleware and owner scope entry points.
- plugin __init__.py: lines1-95, provider and prompt admission registration.
- scripts/prepare_sources.py: lines1-140, source pins, patch ordering, capability record, atomic prepared-tree publication.
- install_source.py: memory patch inclusion search only.
- native MemoryAccess.ts: full displayed helper, configuration/command checks, source/diagnostic calls and validators, with exact shape lines114-137 re-read.
- native CortexHealth.ts: interfaces/assessment search results; lines106-end collection, path/index/evidence, filter call.
- native MemoryHealthCheck.ts: source authority, marker-corruption/dropped-entry sections, final filter/publication; source searches for all filter/check/report boundaries.
- native MemoryWriter.ts: cap/drop search, lock/snapshot/atomic-write/observability sections360-520, read section640-715.
- native MemorySystem.ts: proposal/upgrade publication and hot wrapper sections300-430; eviction/routing/validation/add search.
- native MemoryRetriever.ts: governed retrieval and supplied-corpus branch at685-750.
- native PULSE memory module: first210lines, raw source paths, runs, hot parser, native snapshot construction. Full source archived. Existing open relay path was not re-tested.
- native memory-proposals.ts: first62lines and governed list/decision patch additions, not a new complete native proposal review.
- native memory patch: diff headings plus all governed access/check/filter additions via rg, not an exhaustive patch audit.
- owned Hermes dashboard_auth/middleware.py: lines1-195; web_server.py owner/plugin gate search results; BasicAuth provider username/login source search.

Test inspection: fixture construction and focused tests in test_memory_native.py, test_memory_delegation.py, test_memory_service.py, test_memory_cortex_health.py, test_memory_pulse.py, test_memory_pulse_auth.py, test_memory_proposals.py, test_memory_preferences.py; adoption/curation/proposal/dashboard test searches. Twelve complete test modules executed as recorded in run-regression.sh.

Documentation: README.md memory and compatibility sections; memory-implementation-plan.md status/gates and recent closure sections; memory-design.md ownership/privacy/authority/receipts provisions; update-policy.md; native audit report first115lines; health final closure targeted schema/shape sections. Large combined output was truncated, so these are focused design/claim reads, not complete document proof.

Exact executable commands preserved in run-probes.sh, run-controls.sh, run-dashboard-extra.sh, run-regression.sh and the three Python programs. Investigation uses pwd, rg --files, rg -n, cat, sed, nl, wc, git status --short and git rev-parse HEAD. No git operations changed state. before/after-hashes.json records SHA-256 collection performed by Python. patch-packaging.json records direct byte equality.

Unreviewed: exhaustive native reader/writer inventory, live app/model integration, final delivery, complete host patch contents, full fresh setup/update/rollback transactions, real remote SSH daemon/enrollment in this review, actual PULSE server/relay/browser/graph/wiki. Existing selected tests cover some native recovery/sharing paths but do not establish these broader gates.
