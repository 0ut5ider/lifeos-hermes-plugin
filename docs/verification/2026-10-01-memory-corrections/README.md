# Fresh memory review corrections

The fresh review identifies four defects at implementation interfaces. These corrections preserve the approved memory ownership design. The work uses owned public source and synthetic profiles. It makes no live configuration change.

## Dashboard owner authorization

Every private memory dashboard route requires a verified Hermes Session. The preferences operations check its qualified account against the same configuration that supplies the installed root and owner scope. Sharing, enrollment, and revocation check the owner binding again inside the configuration update. Internal owner helpers retain their existing trusted use without an HTTP identity. Private responses, including host denials, disable caching.

Four regression cases fail before the correction. They cover disabled host authentication, revoked bindings, distinct authenticated accounts without a binding, and a revoked forget operation. The corrected 34-case dashboard, preferences, and sharing gate passes. A separate three-action race case passes after removal of the owner binding between initial authorization and configuration update.

`dashboard-after.log` preserves the intermediate failed run. Two failures come from a fixture override that needs the added account argument. The third comes from the host's shared password-login rate limit. The corrected fixtures preserve real authentication and use the host's test-only reset to isolate rate-limit state between tests. `dashboard-final.log` and `dashboard-owner-race.log` contain the passing results.

The correction adds no Hermes or LifeOS patch. Memory ownership remains disabled. The broader native coverage, relay, lifecycle, installation, and release requirements remain open.

## Reference authorization before recovery reads

Publication path selection uses the mutation scope. A fact reference must have the required write grant, active status, and current revision before the journal receives its source path. Proposal decisions require their approval grant and current pending revision. A denied or stale callback can still record its refusal receipt, but its empty publication set opens no source file.

Two regressions use actual Python file-open audit events. Before the correction, eight category, project, and stale-reference subcases open forbidden or obsolete sources. After the correction, all refuse without source access or byte changes. The complete native, proposal, and authorization gate passes 40 tests in 25.041 seconds, including publication interruption, retry, and recovery controls. The files `source-authorization-before.log` and `source-authorization-after.log` retain both results.

## Explicit hot-memory publication

Explicit hot remember requires read and write grants for the current file. It verifies the whole native snapshot before duplicate detection or publication. It uses the existing verified curation operation, with the explicit writer's source metadata. Adoption remains a separate reviewed action. Project-note publication retains its native archive path.

The before run fails six subcases across unadopted principal and assistant entries, outside additions, changed recorded entries, and a missing read grant. The corrected native, curation, adoption, and authorization gate passes 48 tests in 49.989 seconds. The controls verify byte preservation on refusal, existing references, explicit provenance, duplicate and retry behavior, and a usable governed read after adoption. Evidence is `hot-publication-before.log` and `hot-publication-after.log`.

## Native diagnostic schema

The projection declares the fixed finding fields used by MemoryHealthCheck and CortexHealth. It preserves schema labels in both `detail` and `evidence`, plus the exact invalid-entry row locations. The native response validator retains its strict key, array, and primitive-type checks. Unknown dynamic keys and all fact-bearing strings remain governed.

The original marker and state reproductions fail before the correction. Additional actual native calls reproduce invalid-entry label removal and the Cortex assessment format. The corrected four-case collector gate passes in 20.555 seconds. The separate assessment case passes in 4.091 seconds. Critical marker diagnoses, warning details, and publication survive retirement of their schema words. Nested content keys still receive filtering.

The intermediate logs retain probe mistakes. Native reports omit details for successful checks, and identifiers and filenames still receive text filtering. The corrected tests inspect warning details and the existing success summary. An invalid-entry probe first uses a line the native parser ignores, then uses a recognized overlength entry to reproduce the real label failure. These fixture errors do not establish implementation failures.

These four corrections add no Hermes or LifeOS patch. The prepared native memory patch remains unchanged. `run-regression.sh` runs the combined 15-module gate and writes `regression.log` and `regression.done`. A passing correction gate does not close the outstanding whole-install activation requirements.

## Expanded review and additional corrections

The first combined gate passes 215 tests without skips in 204.223 seconds. The [expanded independent review](../../agents/2026-10-01-memory-correction-review/memory-correction-review.md) runs 316 tests across 27 modules. It finds four additional issues. All nine bad test outcomes are delta summary failures. Separate actual native probes establish the other three defects. The primary copies and reruns all three observation programs before changing code; `followup/*-before-results.json` retains their observations.

1. Hot correction and forgetting now require read and write grants. They check the whole native snapshot before the recovery copy and again before publication. Malformed neighbors, valid outside additions, and changed valid neighbors refuse publication. Registry records and native bytes stay unchanged. Real file-open audit tests verify that a write-only caller does not open the hot source. The initial regressions fail in 12 subcases; the corrected 34-test native, curation, and authorization gate passes in 43.110 seconds.
2. Fixed diagnostic `system` and `live` labels survive at the exact native finding-detail location. Their values still receive retirement filtering. A real missing-hook report stays critical and publishes with the same schema. The pre-fix regression fails. An intermediate assertion incorrectly expects a retired filename to remain visible; the corrected assertion preserves the intended value filtering. The final focused test passes in 3.707 seconds. The full diagnostic gate runs again during closure.
3. Hot append operations retain the native `MemorySystem.add` log label. The registry retains the authenticated writer. Native delta readers receive learned counts and current samples again. All 20 existing delta tests run before the fix with eight failures and one error. All 20 pass after the fix in 39.051 seconds. Full curation retains its distinct label.
4. Native hot additions retain the authenticated source session, as project additions already do. Full native curation retains the session for newly created facts through both supported call paths. Existing facts retain their previous provenance. Actual Bun-to-RPC regressions fail before each correction. The corrected 30-test delegation, curation, and service gate passes in 44.517 seconds.

Implementation commits, in review order: `f5470a9`, `7657980`, `866ee07`, and `d1a919e`. These corrections remain inside the plugin. They add no native patch and change no running installation. `followup/run-regression.sh` runs the expanded closure suite. Its result and the fresh whole-design review are recorded after completion.
