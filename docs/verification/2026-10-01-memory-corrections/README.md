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

## Fresh closure findings

The first expanded primary gate passes 321 tests without skips in 359.196 seconds. The [fresh whole-design review](../../agents/2026-10-01-memory-closure-review/memory-closure-review.md) then identifies an interrupted-save contract that those tests do not cover. A real process exits after native publication and before metadata commit. Recovery restores the fact file, but the uncaptured native audit row still reports the aborted candidate as learned. The primary independently reruns the same registered composer probe and confirms the defect.

Commit `39baa58` journals the exact native hot-write log with every hot publication. It checks the log's physical observability path before capture. Recovery restores the prior committed prefix, including removal of a previously absent log. Delta additions require current registered native content rather than audit evidence alone. Three pre-fix regressions cover four category/addition crashes, an unregistered log sample, and a redirected log. An intermediate redirect fixture lacks its CONFIG directory; the corrected fixture reproduces the real committed-write failure. The corrected 57-case delta, curation, native, and authorization gate passes in 99.706 seconds. Six additional correction, forgetting, and full-curation crash subcases pass in 11.192 seconds.

The first delta authority check reads native memory once per distinct addition. The reviewer measures 13.027 seconds at 96 valid current entries. The primary independently measures 12.700 seconds. A new actual eight-second registered-hook regression times out before the next correction. Commit `0860988` uses one verified snapshot per supported hot category. The unchanged probe then takes 7.194 seconds at 96 entries and 0.923 seconds at two entries. All 23 delta tests pass in 55.558 seconds. The eight-second gate now passes; maximum-capacity timing still has limited headroom. Remaining per-record retrieval costs are a measured limit, not a claim of failure under the tested contract.

The review also identifies missing session provenance in explicit context-bound saves and proposals. The authenticated writer and native persistence are correct. The dispatch must retain trusted session metadata without allowing tool arguments to supply it. Sessionless MCP and owner helper calls must not invent a host session. Real three-category, proposal, and complete Hermes turn regressions fail before this correction. Final correction and closure evidence follow below.

Commit `0913b30` carries the trusted context session through explicit save and proposal dispatch. Its pre-fix regressions fail in five subcases. Its corrected 35-test delegation, proposal, service, and actual-agent gate passes in 50.673 seconds. Identical retries retain their receipts, duplicate saves preserve the prior source, and sessionless client calls keep an empty host session.

The primary gate before the corpus correction runs all 27 modules: **328 tests pass in 374.358 seconds, with no skips, failures, or errors**. `followup/expanded-before-corpus-cache.log` and its done marker preserve this gate. `followup/expanded-before-recovery.log` retains the earlier 321-test gate. `followup/closure-source-identity-before-corpus-cache.json` identifies implementation `0913b30` and records no native patch change or live change.

The independent closure at `0913b30` passes 113 tests in 202.430 seconds. Its separate capacity observation takes 8.294 seconds, although an isolated actual timeout test passes in 7.547 seconds. This variance leaves marginal headroom. Real RPC instrumentation finds 100 native hot reads: 96 in retrieval, two for explicit file reads, and two for delta authority checks. The 100 reads consume 6.460 seconds of a 7.210-second instrumented turn. The retrieval call path is `relevant_context`, `_corpus`, `_content`, and `_native`.

Commit `0400794` reuses native parsed entries per file only inside each locked retrieval. It retains category filtering before reads and each reference's native digest check. Project section handling stays unchanged. A real four-fact wrapper regression observes four reads before correction and two afterward. Restricted principal recall reads only its file; project-only recall reads neither hot file. A changed digest still refuses. An intermediate characterization wrongly expects native duplicate-line rejection; the actual native parser normalizes those duplicates. The corrected characterization preserves that existing result.

The corrected 61-test native, delta, and delegation gate passes in 109.869 seconds. The unchanged capacity probe then measures 0.948 seconds for 96 valid facts and 0.935 seconds for two facts. The previous 328-test log is preserved as `followup/expanded-before-corpus-cache.log`. The final source identity is now `0400794`. The final 330-case gate and independent closure verify this last change. There is still no native patch or running-server change.

## Final correction closure

The expanded primary suite at `0400794` passes **330 tests in 371.570 seconds**, with no skips, failures, or errors. `followup/regression.log` preserves each case. Its done marker contains `0`. `followup/closure-source-identity.json` records the implementation hashes, identical distributed native patches, and no running installation change.

The fresh reviewer independently passes **144 tests in 229.294 seconds** across 11 affected modules. Its six observation phases cover audit recovery, seven interruption/retry controls, distinct native capacity, real native call counts, explicit tool provenance, and a complete Hermes turn. The isolated actual eight-second capacity test passes in 1.644 seconds. The unchanged 96-fact observation takes **0.979 seconds**. Retrieval performs two native hot reads, and complete registered composition performs six. All final observation checks pass. The final whole-design report records no further material defect in the reviewed implemented paths.

The primary's 27-module suite includes the reviewer's 11 modules. The primary independently reruns the new instrumentation probe against the same implementation. The registered full-capacity turn takes 1.098 seconds. Its six native hot reads consume 0.395 seconds. The retrieval accounts for two of those reads. `followup/corpus-instrumentation-results.json` preserves call counts, frames, durations, and registered output. This is a synthetic native-source measurement, not a real-model latency claim.

The whole-install activation requirements remain open: native HTTP relay and browser credentials, complete native-reader inventory, managed restore and staged publication, restricted route and lifecycle acceptance, recoverable ownership setup, and the full release gate. This correction closure does not activate memory ownership or optional sharing. It adds no dependency or Hermes/LifeOS patch change. It changes no running server and performs no push or deployment.
