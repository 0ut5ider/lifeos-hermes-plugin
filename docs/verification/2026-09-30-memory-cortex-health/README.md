# Governed native memory health

## Scope

This unit governs native CortexHealth collection and MemoryHealthCheck publication. It uses real Bun commands, the Python memory service, and synthetic owner profiles. The memory patch changes 17 LifeOS files. This unit adds no Hermes patch and changes no running server.

The native controls preserve health decisions, missing-file findings, malformed-line reporting, invalid-entry warnings, counts, and ordinary standalone behavior. Managed calls require unrestricted source authority and exact physical paths. Filtered reports retain operational evidence while excluding retired display text.

## Source preparation

Public Hermes base: `758ad514eb0e800547e015edf05aa18f78b78d82`.

Public LifeOS base: `5e2f2e8c0abde612da0e99c16c0d07d4ec21b88c`.

Final source preparation applies both complete patch bundles from owned clean repositories. Its output is `/home/outsider/.cache/lifeos-plugin-memory/source-gate-20261001-cortex-final`. The final memory patch contains 58,956 bytes in each identical distributed copy. The commands and preparation results are retained in this directory.

## Corrections and evidence

1. The ordinary governed hot reader refuses invalid entries. Diagnostic inspection now reports dropped invalid entries without exposing valid fact entries. The genuine overlength fixture preserves its warning and filters a retired entry.
2. Source and publication preflight rejects redirected files and directories. An optional managed report uses `LIFEOS/MEMORY/OBSERVABILITY/reports/<name>.json`. The name permits ASCII letters, digits, underscores, and hyphens. The report cannot replace configuration or another diagnostic input.
3. Valid clocks in declared native metadata locations remain operational evidence. Fields inside arbitrary errors, content, and samples receive no clock exception. Declared health enums use the same location restriction. Exact retired clocks in free text remain excluded.
4. Diagnostic filtering accepts requests up to 3,145,728 bytes. Other native operations retain a 131,072-byte limit. The service checks the serialized response against a three-mebibyte limit.
5. Managed collection and filtering failures return explicit unavailable JSON with exit 2 before publication. Standalone exceptional behavior remains native. An 8,000-entry oversized fixture creates neither a health log nor an optional report.

`review-regressions-before.txt` reproduces all three initial review findings. `report-namespace-before.txt` reproduces an overwrite of a diagnostic input. `metadata-paths-before.txt` reproduces the nested clock exception, the analogous enum exception, and the changed standalone error semantics. Earlier fixture and assertion failures remain in this directory.

The primary first closure runs 105 cases in 80.429 seconds, with no failures or skips. The first independent closure runs the same 105 cases in 89.910 seconds. Both runs precede the final metadata-path corrections. The primary corrected managed-source gate passes 56 cases in 48.381 seconds. The final distributed-source gate passes 56 cases in 41.269 seconds. Final independent closure passes the same 56 cases in 38.914 seconds. It finds no remaining material defect in this bounded scope. The final report is `docs/agents/2026-09-30-memory-cortex-health-review/final-closure/memory-cortex-health-final-closure.md`. The primary reruns the five archived probes and the additional metadata-path probe. Exact outputs are retained with the `primary-` prefix.

The unchanged original probes now refuse the optional configuration overwrite, preserve warning-level assessment for the retired operational clock, and produce a complete 500-entry report. The primary volume case completes in 1.608 seconds. The actual Stop health hook completes in 1.790 seconds and publishes its expected blocker summary. These measurements use synthetic fixtures, not a live agent conversation.

## Limits

This gate does not establish governed PULSE HTTP requests, every corpus reader, atomic restore, staged publication, restricted prompts, complete lifecycle coverage, or activation readiness. Whole-file native input reads remain unbounded. The same operating-system identity can still access its files directly. Ownership remains disabled on running installations.
