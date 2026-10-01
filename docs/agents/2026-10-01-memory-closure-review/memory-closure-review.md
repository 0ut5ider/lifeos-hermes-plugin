# Independent memory closure review

Date: 2026-10-01. Agent role: independent implementation reviewer. Question: do the corrected memory implementation and its surrounding integration contracts satisfy the approved design within the implemented scope? Model: GPT-6.1-Sol, inherited high reasoning.

Adrian, the independent review is complete. No new material finding remains open in the reviewed implemented scope at `0400794`. The preceding four findings are corrected, and this review finds three further defects that the primary corrects and this reviewer verifies. The final independent affected gate passes 144 tests in 229.294 seconds, with no failures, errors, or skips. The approved ownership split remains sound. The known unfinished activation and release requirements remain open.

Reviewed implementation: `d1a919e28ebcf43ea68163424aa1faa841b60bd2`, branch `feature/lifeos-memory`. A later documentation-only commit, `8dc1b42`, records preceding evidence. `raw/reviewed-source-d1a919e.tar.gz` preserves the initial source. `raw/baseline-sha256.txt` and `raw/prefix-drift-check.txt` establish unchanged tracked implementation, tests, and patches through the independent baseline probes. The primary then begins a correction. The findings below preserve the initial and intermediate failures. The final closure assessment verifies implementation `040079496cb227cf3dabfc701524eed856170af7`.

## Ranked actionable findings

### F1. Recovery leaves an aborted hot addition in the native learned summary

**Medium. Confirmed inaccurate save reporting and uncommitted candidate text in registered model context.**

Sources at the preserved baseline: `lifeos_hook_bridge/memory_access.py:322`, especially publication paths at lines 335, 342, and 354; `lifeos_hook_bridge/memory_transaction.py:74` and `:81`; `lifeos_hook_bridge/memory_sources.py:94` and `:118`. Native `MemoryWriter.ts:457` appends accepted and rejected write events. Native `MemoryTurnStart.hook.ts` composes the admitted current-memory and delta outputs.

The new independent reproduction uses real native publication, a real process interruption, actual journal recovery, and the registered hook:

1. Save `RULE: Synthetic committed recovery control` through governed principal memory.
2. Start a synthetic child that calls governed explicit remember for `RULE: Synthetic aborted recovery candidate`.
3. Exit the child with code 73 when `_record` would register the new fact, after native `setEntries` has published the hot file and appended its write event.
4. Perform a governed hot read. Recovery restores the original file and removes the unknown operation reservation.
5. Confirm current hot memory and ordinary recall contain only the committed control.
6. Run the real registered `MemoryTurnStart.hook.ts` with admitted owner metadata.
7. Its current-memory block has one entry, but its delta block reports `+2 learned` and quotes both the committed control and the aborted candidate.

The uninterrupted control has two actual records and correctly reports `+2 learned`. The interrupted case has one actual record but reports the same count and candidate. `raw/probe_recovery_delta.py`, `raw/recovery-delta-before-results.json`, and `raw/recovery-delta-before.log` preserve this comparison. The probe exits 0 because it completes its observations. Exit 0 does not mean the observed baseline contract passes.

Cause: recovery journals the native hot file, while the native accepted-write event falls outside the publication paths. The old event survives recovery. The governed log projection validates syntax and retirement, but it does not establish that an addition corresponds to a current registry record. A candidate that never committed has no retirement row, so those checks admit it.

The new eight-case root-cause experiment covers principal and assistant memory, explicit remember and native add, and two recovery-capture controls. Without audit capture, all four interrupted writes restore current facts but retain the aborted sample in registered output. A disposable `NativeMemory` subclass that adds the existing `memory-writes.jsonl` path to the same journal restores its prior committed prefix byte-for-byte and removes the aborted sample in all four controls. Each actual child exits 73. The hypothesis program exits 0 after checking those outcomes. It changes no implementation file.

Evidence: `raw/probe_recovery_journal_hypothesis.py`, `raw/recovery-journal-hypothesis-results.json`, `raw/recovery-journal-hypothesis.log`, and `raw/recovery-journal-hypothesis.done`. Each result retains the journal contents, prior audit prefix, published audit row, recovered log, current hot snapshot, and exact registered output.

Smallest correction: include the known hot-write audit log in the existing recovery capture for every governed hot publication. Check its exact physical observability location before capture, so it cannot redirect into a different user file. In the existing learned-log projection, require additions to match current registry content and the supported hot category identified by that event. Keep historical audit data and eviction treatment explicit. A new native patch is unnecessary for the measured publication gap.

Required regressions: both categories, both addition entry points, interrupted add before metadata commit, unchanged prior audit prefix, recovery before another native write, safe identical retry, missing initial audit file, normal native rejected-write evidence, full-set/correct/forget interruption controls, and redirected audit paths. Retain the genuine registered-composer control, delta cursor behavior, retirement filtering, counts, sample order, and bounded native execution tests. A full log rollback is justified by the cooperating transaction. This review does not establish safety against a hostile or ungoverned process that appends outside that lock.

### F2. The first recovery correction rereads native memory per distinct delta addition

**Medium. Confirmed registered-hook availability regression at follow-up commit `39baa58`.** This defect is introduced by the first F1 correction, rather than present in the initial `d1a919e` source. The initial baseline finding remains preserved above.

The new probe publishes real native hot entries under the native addition label and then adopts the actual native source through the governed adoption operation. A two-entry control completes the real registered composer in **0.926 seconds**. Two files at their native caps contain 48 valid current entries each, with 96 valid references. The composer completes in **13.027 seconds**, beyond the eight-second registered-hook gate. It reports the intended `+96 learned` only because the observation allows 45 seconds.

Cause: the new current-registry validation memoizes by `(file, entry)`, but each distinct current addition calls `_content`, which starts another native `read_hot` subprocess. The repeated-entry volume control does not cover this valid maximum number of distinct entries. A full-cap source can require 96 extra native subprocesses.

Smallest correction: obtain one verified `_hot_snapshot` per supported category inside the existing transaction. Use the verified current entry set to confirm each native addition. Keep registry status and permitted-category checks and preserve native counts, cursor order, samples, malformed-row handling, and historical retirement exclusions. This removes per-entry subprocess work while retaining source verification.

Evidence: `raw/probe_distinct_delta_latency.py`, `raw/distinct-delta-latency-results-39baa58.json`, `raw/distinct-delta-latency-39baa58.log`, and `raw/recovery-correction-39baa58.tar.gz`. The source archive preserves the exact first recovery correction before any performance fix. This is a measured bounded fixture result. It does not establish a whole-file I/O bound or all fabricated oversized input behavior.

### F3. Explicit context-bound tools discard the known host source session

**Low. Confirmed missing source attribution with correct authenticated writer and native persistence.** This defect exists in the initial `d1a919e` implementation and remains at `39baa58`. It is outside the prior native-add source-session correction.

`MemoryService.call_context` resolves the authenticated context to a scope, but passes no source-session metadata to `_call`. The explicit remember branch calls `memory.remember` with its sessionless default source. The explicit proposal branch also calls native add without the available host session. The source kind is correct, and the authenticated writer remains separate and correct.

The new context probe saves actual native principal, assistant, and project facts from context `chat-a:100`, session `native-session`. Every receipt and registry readback has source kind `explicit` and session `''`. The same context's native-add control records `native-session`. The actual complete Hermes `AIAgent.run_conversation` probe confirms this behavior through the provider and native tool loop: the turn has session `session`, while its successfully saved project fact has source kind `explicit` and session `''`.

Smallest correction: pass the trusted context's source session through the common dispatch for explicit remember and proposal creation. Leave sessionless dashboard and external process calls explicit about missing host sessions. Preserve the existing writer identity boundary, saved source metadata, and identical-retry receipts. Do not accept a source-session tool argument as proof of writer identity.

Evidence: `raw/probe_explicit_context_provenance.py`, `raw/explicit-context-provenance-before-results.json`, `raw/explicit-context-provenance-before.log`, `raw/probe_agent_source_session.py`, `raw/agent-source-session-before-results.json`, and `raw/agent-source-session-before.log`. The complete turn uses the existing scripted local model endpoint, rather than an external model or live installation. The successful turn proves attribution loss, rather than missing saved facts or a writer spoof.

## Verification of the preceding corrections

| Previous finding | Independent result | Concrete evidence and limit |
| --- | --- | --- |
| Unsafe hot correction and forgetting | Closed in the reviewed baseline | The unchanged neighbor probe covers both categories, both operations, no drift, overlength drift, and unmanaged addition. Allowed controls commit and remain readable. Drift refuses publication and preserves bytes. Write-only correction and forget now reject. |
| Missing fixed diagnostic `system` and `live` fields | Closed in the reviewed baseline | The unchanged real health probe retires each name and preserves the critical hook-registration diagnosis and its publication. All three fixed detail names remain present. Content values still receive retirement filtering. |
| Explicit remember loses native addition labeling | Closed in the reviewed baseline | The unchanged registered-composer probe shows the explicit saved fact, `MemorySystem.add`, `+1 learned`, and the current learned sample without the previous label intervention. |
| Native hot add loses the host-bound source session | Closed in the reviewed baseline | The unchanged actual delegated native add probe returns authenticated writer `chat-a:100` and source kind `native`, session `native-session`, for both hot/project controls. The direct hot probe checks both hot categories. |

The correction-focused unittest gate runs separately from these observation programs. Its exact command and final output are preserved in `raw/run-baseline-targeted.sh`, `raw/baseline-targeted.log`, and `raw/baseline-targeted.done`. It runs from the archived baseline checkout so primary edits cannot contaminate its source identity. The independent baseline gate passes **85 tests in 130.557 seconds**, with no failures, errors, or skips. Its done marker is `0`. This passing gate coexists with the separately reproduced recovery defect.

The primary reports its own 321-case expanded baseline gate. This reviewer does not present that result as independently rerun evidence. The new recovery finding is outside the tests in that gate.

## Broader design and integration assessment

The implementation continues to keep fact bodies in native LifeOS files. The schema 3 registry stores references, lifecycle state, digests, writer/source provenance, and retry receipts. Temporary private journals contain recovery copies. These copies are part of recovery, rather than an additional editable fact archive. F1 identifies an incomplete publication set, rather than a failure of the ownership model.

`MemoryService` loads configuration once per request and binds its scope and root to that same configuration. Client grants remain server-owned. The policy binds qualified author accounts, exact destination/audience, visibility, model route, categories, project grants, and proposal capabilities. Configuration updates use a separate private lock and publish atomically. Dashboard mutation paths recheck owner/root inside configuration updates. No new root/grant mix or dashboard authority bypass is found in the inspected code.

The Hermes provider obtains its authority from runtime admission. Required request checks verify actual routes and request model overrides, current installed prompt identity, retirement generation, retained messages, generated auxiliary inputs, and inherited contexts. Native RPC uses the host-bound context and common policy. Unknown routes and restricted installed prompts refuse owner-context execution. The unfinished restrictions and delivery work remain explicit capability limits. This review does not claim all model payload fields or every host route are covered.

The hot mutation fixes verify a full current snapshot before publication, and require read and write grants for hot reference operations. Archive publication preserves earlier section content and updates offsets when native frontmatter changes. The native curation path distinguishes additions from full-set writes and records host source-session metadata for newly created entries. Current fact references remain separate from proposal references. Retry keys remain authenticated-writer scoped, and a changed payload receives a conflict.

Proposal creation and approval require separate grants. Targets and queue revisions receive validation before application, and pending/diverted outcomes remain distinct from committed edits. Adoption signs actual native content, metadata, and project assignments. Retained-source and diagnostic projections apply native validation and lifecycle filtering. Exact diagnostic field locations preserve operational schema without granting arbitrary nested text a metadata exception. No second new material defect is found in these inspected paths.

The optional MCP process uses a fixed server-selected client and reloads grants for each operation. Restricted SSH enrollment uses a separate public key, a fixed forced command, private key-file checks, and configuration-first revocation. The declared model route can remain unknown and is shown as such. This is interface authorization. It does not protect memory from a process with the same operating-system access, and it does not establish downstream client model routing.

## Known unfinished requirements

These remain distinct from F1 and are not newly broken implemented behavior:

- Native HTTP PULSE relay and browser identity/credential integration.
- Ninety-five untraced native inventory candidates, alternate corpus and derived readers, graph/wiki paths, and remaining capture/synthesis routes.
- Managed restore and staged publication with full backup/update/rollback acceptance.
- Restricted rendered prompts, final delivery permissions, all messaging adapter metadata, complete resume/compression/Responses repair, and lifecycle coverage.
- Fresh installation ownership transactions, optional connection setup acceptance, and the full release gate.

Ownership remains disabled on running installations. This review provides no activation or deployment authorization.

## Evidence, restrictions, and review needs

`raw/review-inventory.md` documents the modules and native construction/publication paths inspected. `raw/command-inventory.md` records invocation conventions. The initial source archive and baseline hash manifest preserve the reviewed revision. The prepared public sources are LifeOS `5e2f2e8c0abde612da0e99c16c0d07d4ec21b88c` and Hermes `758ad514eb0e800547e015edf05aa18f78b78d82`, with the already prepared owned patches. `raw/public-source-hashes.json` covers the 17 native patch destinations and nine relevant host files. It is not a whole-tree integrity audit.

All probes use disposable synthetic homes. No existing memory store, running server, credential, real remote model provider, dependency installation, memory/journal MCP call, implementation edit, commit, push, or deployment is performed. The primary owns any subsequent implementation correction. The preserved source archive does not imply every line was inspected.

Adrian should review the corrected transaction's publication set and its treatment of audit history most closely. Recovery must preserve previously committed audit rows and all current facts. Current learned samples must agree with registry authority. Unmanaged native behavior and committed native rejected-write evidence need controls when the fix is verified. The unfinished whole-install release requirements remain outstanding after this bounded defect is corrected.

## Correction sequence and measured performance follow-up

The primary implements the corrections. This reviewer preserves the failing source and observations, reviews the changes, and reruns independent controls. No reviewer implementation edit occurs.

| Source revision | Correction and verification state |
| --- | --- |
| `39baa587f754f2aa206ac879243ca6bf236d25da` | Adds the attested native hot-write audit log to governed hot publication journals. Requires each addition sample to match an active current fact. Closes the phantom-learning cause, but the new projection rereads native hot memory per distinct addition. |
| `0860988ce303c38a8bd24cde22a513cfa865dcec` | Validates current addition sets with one verified snapshot per supported hot category. Preserves the registry and content authority checks. |
| `0913b3044816968199eeb753a722f07ebca4a20d` | Explicit context-bound remember and proposal dispatch pass the trusted host source session. Sessionless calls keep their empty session. Input arguments cannot inject source metadata. |
| `040079496cb227cf3dabfc701524eed856170af7` | Reuses the native parsed hot entries per file only within `_corpus`'s existing locked retrieval. Scopes filter records before parsing. Each reference still receives its own digest match, and project content stays on its existing path. |

The first two performance checks produce different conclusions for distinct source revisions. At `39baa58`, the independent full-cap composer takes **13.027 seconds**. At `0913b30`, the nine-module independent gate passes **113 tests in 202.430 seconds**, including the actual eight-second native cap test. The isolated native cap test passes in **7.547 seconds**. However, the unchanged observational probe takes **8.294 seconds** with 96 facts. This marginal observation is retained as evidence, rather than removed because the test passes on another run.

The independent native instrumentation at `0913b30` identifies the remaining cost. Registered full-cap composition performs two hot reads for ordinary hot loading, two for governed delta projection, and **96** in registered retrieval through `relevant_context -> _corpus -> _content`. All **100** hot reads take **6.460 seconds**. The whole instrumented composition takes **7.210 seconds**. Each observation still invokes the actual native parser with unchanged arguments. The cause is repeated parsing within the existing retrieval, rather than model latency or a persistent cache miss.

`raw/corpus-instrumentation-results-0913b30.json` retains action counts, caller frames, durations, and exact registered output. `raw/distinct-delta-latency-first-final-0913b30.json` preserves the 8.294-second observation. `raw/final-targeted-0913b30.log` preserves the passing 113-case independent gate. `raw/isolated-cap-0913b30.log` preserves the passing isolated eight-second test. These outcomes coexist and explain why the primary instruments and corrects the remaining retrieval work.

The primary's transaction-local correction preserves native duplicate normalization, reference digest rejection after a physical file change, and category-grant filtering. It introduces no persistent cache, native patch, whole-file recall policy, new store, or architecture change. The completed final independent closure follows below.

## Final whole-design closure assessment

Final implementation revision: **`040079496cb227cf3dabfc701524eed856170af7`**, branch `feature/lifeos-memory`. The implementation remains unchanged throughout the final independent run. All 186 tracked plugin, test, and patch paths in the source manifest match their captured final bytes. All 26 recorded prepared native and host source files match the initial public-source hashes. The approved design remains unchanged. These checks identify the reviewed source; they do not imply a line-by-line audit of every archived file.

**No new material finding remains open within the reviewed implemented scope.** F1, F2, and F3 are closed by the corrections above and the independent controls below. The preceding four correction findings also remain closed. The approved ownership boundary is preserved: native LifeOS files hold fact content, the registry holds reference/lifecycle/digest/provenance metadata, and private recovery journals hold temporary recovery copies. The fixes add no native patch, persistent cache, alternate fact archive, host deployment, or architecture change.

| Review finding | Final independent result | Reproduction and controls |
| --- | --- | --- |
| F1, aborted hot addition remains learned | Closed | The unchanged interruption reproduction exits its native-writing child with code 73. Recovery restores one current fact, the registered composer reports `+1 learned`, and the aborted candidate is absent from ordinary recall and registered output. The successful two-fact control reports `+2 learned`. |
| F1, broader hot publication and retry contracts | Closed | Seven real interruption cases verify principal/assistant correction, forgetting, and full-set publication, plus an initially absent audit log. Prior hot and audit bytes are restored, neighbor references remain valid, retries commit, and identical repeated requests return the same receipts. The affected gate also checks both categories and addition entry points, fabricated unregistered additions, redirected logs, and normal native controls. |
| F2, bounded registered composition | Closed | The unchanged two-fact control takes **0.940 seconds**. The unchanged 96-fact native-cap control takes **0.979 seconds** and retains `+96 learned`. The actual eight-second test passes independently, one test in **1.644 seconds**, and passes again in the affected gate. |
| F2, measured native-call cause | Closed | Actual registered retrieval performs **2 hot reads**, one per supported file, instead of 96. The entire instrumented composer performs **6 hot reads** instead of 100. Those reads take **0.410 seconds**; the instrumented composition takes **1.106 seconds**. Native parsing and each reference's digest checks remain active. |
| F3, explicit tools lose known session | Closed | Real principal, assistant, and project remember calls retain source kind `explicit`, trusted session `native-session`, and authenticated writer `chat-a:100`. The actual complete Hermes turn saves source session `session`. The affected gate also verifies proposal provenance, same-request retries, new-request duplicate provenance, and sessionless calls. |

### Final independent verification

The final sequential script is `raw/run-closure-0400794.sh`. It runs six probe programs, the isolated native capacity test, and the 11 affected modules. The affected modules cover native references and retrieval, archives, hot curation, authorization, native delegation, registered delta, native Cortex health, explicit service dispatch, proposal delegation, the complete Hermes turn, and optional MCP. The gate passes **144 tests in 229.294 seconds**. There are **zero failures, zero errors, and zero skips**. Each of the nine final phase and aggregate completion markers is `0`.

`raw/closure-observation-checks.json` records explicit checks of the saved probe values. In particular, it checks candidate removal and the genuine `+1`/`+2` controls, all seven recovery cases, both capacity observations below eight seconds, the two retrieval reads, three explicit category sessions, and complete-turn session metadata. This separates an observation program's successful execution from its observed contract result.

The primary independently reports its expanded **330-test gate in 371.570 seconds**, with no failures, errors, or skips and `regression.done=0`, at the same final implementation. This reviewer reads that completed output but does not present the primary run as a second independent 330-test execution. The reviewer's affected gate supplies the independent 144-test result. The earlier 85-test baseline and 113-test intermediate gates remain preserved with their source identities. The primary also reruns the unchanged native instrumentation program independently: the composer takes 1.098 seconds, with six total hot reads, two retrieval reads, and 0.395 seconds in native hot reads. This reviewer reads the saved JSON and preserves it as `raw/primary-corroboration-corpus-results.json`.

### Source and evidence record

- `raw/reviewed-source-d1a919e.tar.gz` and `raw/baseline-sha256.txt` preserve the initial implementation before correction.
- `raw/recovery-correction-39baa58.tar.gz` preserves the recovery correction that introduces the first distinct-addition performance regression.
- `raw/final-source-0913b30.tar.gz`, the suffixed probe results, and the 113-case gate preserve the intermediate source and marginal capacity result.
- `raw/closure-source-0400794.tar.gz`, `raw/closure-sha256-0400794.txt`, and `raw/closure-revision.txt` preserve final plugin/test/patch source identity.
- `raw/closure-final-integrity.json` checks every final manifest path, public prepared-source integrity, final test count, clean result, and completion markers. `raw/approved-design-integrity.json` confirms the approved design has identical initial and final bytes. `raw/report-evidence-checks.json` verifies cited artifact presence, authored prose constraints, and probe/script syntax.
- `raw/corpus-instrumentation-results.json` retains actual native operation/action counts, timings, caller frames, and registered output. The `-0913b30` result retains the measured repeated retrieval cause.
- The final probe JSON files preserve native hot snapshots, journals, before/after audit evidence, retry receipts, writer/source metadata, and complete registered or host outputs. Revision-suffixed copies preserve earlier observations.
- `raw/review-logs.tar.gz` preserves the logs in their original text format, including files that Git's log ignore rule would otherwise omit. `raw/command-inventory.md` and the shell scripts record invocation and completion conventions.

### Precise remaining limits and Adrian's review

This closes the reviewed implemented memory work against the approved design within its declared enabled scope. It does not close the unfinished design requirements listed above, and it does not authorize activation or deployment. Ownership remains disabled. Native HTTP PULSE and browser identity, the 95 untraced candidates and derived readers, managed restore/staged publication, restricted prompt and delivery support, complete lifecycle paths, fresh ownership acceptance, and the full release gate still require their own implementation and evidence.

The measured recovery guarantee depends on cooperating operations holding the private lock. The review does not prove isolation from a hostile or ungoverned same-user process that changes a file during a transaction or appends outside the lock. Performance measurements cover supported native caps and the existing bounded log fixtures on this local interpreter and public prepared source. They do not establish a bound for arbitrary oversized files or every deployment environment. The Hermes turn uses a real host runtime and scripted local HTTP model endpoint; it performs no real provider request. Optional SSH/MCP review uses synthetic local fixtures, not a live remote enrollment.

Adrian should review the audit log's addition to the recovery publication set, current-fact validation of learned samples, and the temporary retrieval reuse most closely. They are the changes this review's measurements require. The source session remains attribution, while the authenticated writer remains the authority. No deployment, live configuration, existing memory store, credential, or external system changes occur in this review. There is nothing outside the report's synthetic fixtures to undo.
