# Native memory source audit

Date: 2026-09-30 (America/Toronto; captured subprocess timestamps extend into October 1 UTC)
Role: Independent source and synthetic fixture reviewer
Question: Which reachable native memory paths remain outside authorization, retained-claim filtering, or governed publication, and what should the next implementation gates cover?
Model: GPT-6. The exact model variant is not exposed in this agent context.

## Conclusion

The prioritized audit is complete. **Ownership activation remains blocked by confirmed native boundary gaps.** This is not a complete review of every native source. The inventory contains 132 candidates; this audit traced relevant sections in 37, including partially traced producers, and eight additional caller, manifest, or documentation files. The remaining 95 candidates have no coverage conclusion. Their status is explicit in `raw/inventory-triage.csv`.

The existing delegated paths remain useful: **33 tests passed in 19.651 seconds**, with no failures or skips. Those tests cover native add/read/set/recall, retained startup and learning readers, and proposal decisions. They do not exercise the ungoverned siblings found here.

Confirmed outcomes in disposable fixtures:

- The registered per-turn composer renders a genuinely forgotten claim from the real native write log. It also returns current private content without caller context.
- The real PULSE memory handler returns current hot memory without caller context, including with an invalid connector.
- Native diagnostics return retained proposal or reviewer text outside the memory service.
- Cortex reads and KnowledgeQuery return retained or unclassified archive content outside the memory service.
- Native MemoryRestore replaces a current hot file with a genuine snapshot containing a forgotten claim. Governed reference resolution correctly detects the resulting inconsistency.
- KnowledgeHarvester promotion copies a retained forgotten claim into the active native archive without registration or permission checks. Governed recall still excludes it, but other native readers expose it.
- The PULSE context builder emits unclassified identity content without caller authority. Its public no-query cache also reuses authorized hot content after caller context is removed. The current Siri route always supplies a nonempty query, so that route does not establish reachability of the cache branch.

These are application boundary failures, not proof that the memory service is an operating-system sandbox. A same-UID process can already read or alter its owner's files. The relevant defect is that supported native operations and loaded consumers bypass the plugin's declared governance instead of participating in it.

## Source and evidence identity

Plugin review began at `2f0a84ea6502b6dd6c747f1b83a2be05c5513f16`. The documentation checkpoint advanced HEAD to `5cdb33d39d82d4cb60f250e4df855d4dffcf83c2` during the audit, on `feature/lifeos-memory`.

Native public base: `5e2f2e8c0abde612da0e99c16c0d07d4ec21b88c`, with distributed patches in:

`/home/outsider/.cache/lifeos-plugin-memory/source-gate-20260930-app-startup/lifeos/LifeOS/install`

Host source was restricted to the sibling `hermes` directory. No live installation was imported or bootstrapped. The interpreter was `/home/outsider/.cache/lifeos-plugin-memory/memory-plugin-test-env/bin/python`.

Artifacts:

- `raw/source-metadata.json`: source revision, branch, coverage counts, and paired-patch equality.
- `raw/native-source-hashes.json` and `raw/native-source-hashes-final.json`: SHA-256 for all inventory candidates and eight additional files. **No native source hashes changed between these captures.**
- `raw/plugin-source-hashes.json` and `raw/plugin-source-hashes-final.json`: plugin and test hashes. The parent began fixing delta handling during report preparation; `memory_sources.py` and `memory_service.py` changed between these captures. Their committed baseline is saved under `raw/plugin-baseline/`. The public prepared native source tested here was unchanged. This report does not review the parent's subsequent fix.
- `raw/sources/`: complete snapshots of the selected public files. A snapshot is evidence preservation, not a claim that every line was audited.
- `raw/source-evidence.txt`: exact relevant source paths and line numbers.
- `raw/commands.txt`, the three probe scripts, and `raw/run_tests.sh`: reproducible commands and private fixture construction.
- `raw/native-reads.txt`, `raw/writers-context.txt`, `raw/secondary-paths.txt`: exact subprocess argv, exit codes, stdout, stderr, native receipts, and persisted-state observations.
- `raw/tests.txt`, `raw/tests.done`: independent 33-test result.
- `raw/initial-checkpoint.md`: original incomplete checkpoint, preserved separately.

## Findings and required gates

### F1. Registered turn-start delta bypasses authorization and retirement filtering

**Priority: first implementation gate. Confirmed with actual native publication and forgetting.**

Reachability: `hooks/hooks.json:340` registers `MemoryTurnStart.hook.ts`. Its line 113 calls `MemoryDeltaSurface.run()`. The delta implementation reads `memory-writes.jsonl` directly at line 179, samples additions and evictions at lines 190-195, and advances the cursor at line 199. It has no managed caller check. Its instruction-shape sanitizer does not implement memory policy.

The probe saved a principal claim through `NativeMemory.remember`, forgot the exact returned reference, and saved a different current principal claim. The unmodified native write log contained the actual additions and eviction. Running the complete composer without `LIFEOS_MEMORY_CONTEXT` returned empty delegated hot-memory blocks, then rendered both the forgotten cormorant claim and the current private pelican claim in a line the model is instructed to repeat verbatim. Running with the approved owner context still rendered the forgotten claim. Both processes exited 0 with empty stderr.

This establishes an upstream context bypass. It does not establish that the final Hermes model guard transmitted the exact retired claim. A downstream refusal or projection is useful defense, but it does not authorize the native read or its side effects. A truncated sample can also differ from the complete retained-claim fingerprint; filtering must precede truncation.

Smallest functional correction: authorize the source collection before reading, advancing the delta cursor, or changing injection/heartbeat state; apply retained-claim and source validation to full log items before rendering samples. Preserve authorized owner counts, freshness, and cadence. Do not remove the delta feature. Include health/freshness free-text fields in the same boundary rather than fixing only `additions`.

Tests: real remember/correct/forget logs; owner current samples retained; forgotten additions and evictions excluded; unknown/restricted/invalid connector denied; denied calls do not consume an owner's cursor; long truncated claims and decoded JSON cannot evade filtering; unchanged unmanaged behavior. The parent reports this fix in progress in managed-source. It requires a fresh distributed-source closure.

### F2. PULSE memory HTTP handler bypasses governed hot and proposal reads

**Priority: high, direct delivery surface. Confirmed handler behavior and source-traced route.**

`LIFEOS/PULSE/pulse.ts:231` loads `modules/memory.ts`; lines 947-948 forward `/api/memory`. The module uses `parseMemoryContent(readFileSync(...))` at line 118. Importing MemoryWriter's parser does not invoke MemoryWriter's governed `read`. It reads proposal and health JSONL directly and returns recent proposal rows at line 246.

The real exported handler returned the current private principal marker with no caller context. After replacing the connector with invalid JSON, the same handler still returned the current private marker and a retained rejected-proposal edit. The HTTP response was produced by the actual handler, not a simulated implementation. No live PULSE server was started.

Server boundary: the reviewed `pulse.ts` listener defaults to loopback and checks the Host header against DNS rebinding. `LIFEOS_PULSE_BIND_ALL=1` changes the listener to all interfaces and disables that loopback Host check. The traced memory dispatch has no per-request memory grant binding. A Host check is not a memory principal identity. This report does not claim public Internet exposure, an active LAN configuration, or a successful network attack. Hermes dashboard authentication is a different server and does not automatically authenticate native PULSE.

Smallest functional correction: bind a trusted PULSE request to an explicit memory scope, then obtain hot files, proposals, and diagnostics through governed operations. Preserve the owner's dashboard and distinguish unavailable from an empty store. Avoid using ambient process owner context for every HTTP requester.

Tests: actual private localhost server route with the intended authentication boundary; full-owner, missing, revoked, restricted, and invalid connector requests; pending/resolved proposals with retained quotes; health error fields; no per-request cache cross-contamination. Existing proposal-decision tests do not cover this raw snapshot reader.

### F3. Diagnostic readers expose raw retained text

**Priority: high for caller-bound diagnostic output; confirmed raw output, limited provenance claim.**

- `MemoryStatus.ts:210-216` parses and returns the entire last JSONL row. `--json` includes fields not declared in its TypeScript summary interface. Our synthetic failed-reviewer row's `error` text was returned unchanged.
- `MemoryInsights.ts:201-205` prints the most recent proposal `edit` samples directly. A native-shaped rejected proposal containing the forgotten marker was printed without caller context.
- `CortexHealth.ts:131-138` preserves `latest.error` in collected evidence. The actual collector returned the forgotten marker from the same class of synthetic failed-reviewer row. `MemoryHealthCheck.ts` places that evidence in its JSON report and health log. The health gate itself emits summary counts, not that error body, which limits the hook exposure claim.

These rows were deliberately populated in the synthetic observability fixture. Unlike F1, the probe did not make the normal reviewer generate the marker in an error. Thus it establishes arbitrary retained field readback, not a claim that every ordinary successful reviewer row contains facts. The parent independently reproduced the whole-row MemoryStatus behavior with another field.

Smallest functional correction: use explicit typed diagnostic projections and governed source access. Keep useful operational counts, timestamps, status codes, thresholds, and owner-visible diagnostics. Free-form error, proposal, filename, or evidence text still needs policy filtering; casting parsed objects to interfaces is insufficient. Readback should not erase history from disk merely to hide it from a caller.

Tests: approved owner diagnostic control; unknown/restricted/invalid connector denial; unexpected JSON fields; legitimate failed-run error text; proposal resolved history; nested/decoded text; health-report-to-PULSE output. Preserve the native health exit semantics and cadence.

### F4. Cortex and KnowledgeQuery read retained/unclassified archive records directly

**Priority: high, supported agent-facing read surfaces. Confirmed native CLI behavior.**

`Cortex.ts:284` enumerates the physical canonical corpus before read operations. `get` and `export` return full selected content at line 299. Source validation enforces file boundaries, schema, validity windows, and private-content sanitation, but it does not bind a memory principal, consult the registry, or apply tombstones. Its write branch correctly delegates to MemorySystem.add at line 274. `CortexAdapter.ts` exposes the same read functions to named agent adapters; an adapter name is not authorization.

A synthetic historical archive note containing an actually forgotten hot claim was returned by `Cortex.ts get audit-retained`, both without caller context and with invalid connector JSON. The claim was unclassified archive content, not a managed active record. A separate real `KnowledgeQuery.ts --json` returned the forgotten title of the note published in F6.

Smallest functional correction: managed Cortex and KnowledgeQuery must build their views from authorized current records and permitted historical sources. Preserve native ranking, pagination, graph bounds, validity windows, and output contracts. All graph edges and metadata need the same authorized corpus. Explicit `--memory-root` and alternate adapter paths must not turn a managed operation into an unmanaged bypass. Standalone operation without a connector remains a separate supported control.

Tests: owner current corpus; project/private entity restrictions; corrected/forgotten/unclassified notes; malformed or dangling connector; status/search/get/export/timeline/graph; record IDs and pagination after filtering; approved standalone root. Existing governed retriever tests do not cover raw Cortex enumeration.

### F5. MemoryRestore publishes raw snapshots outside the transaction and registry

**Priority: high, supported recovery writer. Confirmed actual byte replacement.**

The documented CLI `MemoryRestore.ts restore` reads a snapshot at line 61 and writes the hot file at line 62. `latest` repeats that raw copy at lines 71-72. Neither route enters the plugin's cooperating transaction, checks a current revision, checks the caller, or records a receipt.

The probe selected a genuine native pre-forget snapshot, restored it without caller context, and observed the forgotten claim restored and a later current claim removed. The next governed `get` for the current reference raised `MemoryConflict: The referenced fact changed outside its recorded revision`. This is good downstream detection; it does not repair the overwritten bytes. No claim is made that the registry marked the forgotten reference active.

The initial observation script stopped on that uncaught conflict. Both the original script and traceback are retained. The adjusted observer catches the exception and records the bytes and failure explicitly, without changing production behavior.

Smallest functional correction: route managed restore through the existing authorized hot replacement transaction with current revision checks, retained-claim validation, reference updates, and crash recovery. Preserve owner recovery functionality. Define explicitly whether and how an owner can intentionally restore a retired claim; a raw file copy must not silently decide that policy.

Tests: current authorized restoration, stale snapshot/CAS, forgotten entries, missing and revoked caller, concurrent acknowledged write, interrupted restore, snapshot path validation, unchanged unmanaged restoration. `MemorySystem.ts` also has a CLI smoke-test final raw backup restore at line 1070; that diagnostic mutation path needs a separate managed-state guard or a hermetic synthetic-only contract.

### F6. KnowledgeHarvester promotion publishes retired content outside governance

**Priority: high for publication completeness. Confirmed native CLI mutation.**

`KnowledgeHarvester.ts` routes `promote` to `cmdPromote` at line 1326. At line 1057 it copies the staged body into KNOWLEDGE, removes staging, regenerates indexes, and updates harvest state. There is no memory service call. Staging and explicit promotion are real native functionality and should remain available to an authorized owner.

With a valid managed connector but no caller context, the real command successfully promoted a synthetic Research note containing the exact forgotten albatross claim. It removed the staged file and published the quote. Governed recall remained `[]`, showing that publication did not create an authorized registry record. KnowledgeQuery then exposed the retained title, demonstrating a readback route independent of governed recall.

Smallest functional correction: make managed promotion an authorized publication operation under the cooperating transaction, validating the staged identity and destination and recording its outcome. Reuse existing native rendering and staged-review flow. Do not treat copying into the native archive as implicit approval to adopt unclassified content.

Tests: owner promotion control, forgotten/corrected source denial, missing/revoked writer, project classification, same-title/destination conflicts, stage changed since preview, crash ordering of destination/staging/index updates, and unchanged unmanaged behavior.

### F7. PULSE context builder has an unclassified read path and an unbound cache

**Priority: app-context and delivery gate. Confirmed builder behavior; cache route limited.**

`PULSE/lib/lifeos-context.ts:125` reads identity, TELOS, and projects directly, while hot-memory reads at line 152 correctly delegate. An absent caller therefore removes hot facts but leaves the synthetic private identity marker in the returned context block. These static sources were already an open restricted-prompt gate; this audit locates a concrete additional builder, not a regression in the reviewed Hermes prompt guard.

The no-query branch returns `cachedContext.text` at line 119 based only on time and file mtimes. In one real Bun process, an approved call cached a hot marker; removing `LIFEOS_MEMORY_CONTEXT` and calling again without a query returned the identical block, including that marker.

Reachability distinction: `modules/siri.ts:90` passes a nonempty text query, and line 190 rejects empty text. Thus the current Siri route bypasses the no-query cache branch. Its direct identity read remains relevant: the returned block is appended to an actual Claude Agent SDK system prompt at line 120. Siri has its own bearer authentication, but the traced builder does not translate that identity into a memory grant. No real SDK or model request was made in this audit, and no claim of final model transmission is made.

Smallest functional correction: bind the context source collection and any cache to current scope, policy, source revisions, and caller. Preserve full owner identity and goal context. Verify the actual app credential-to-memory route mapping before claiming Siri is governed. Do not blanket-disable owner startup context.

Tests: full-owner Siri-shaped builder call; missing/revoked caller; no-query cache caller switch and policy revocation; source change; malformed connector; restricted static source behavior and final model/destination admission when that gate is implemented.

## Additional traced paths and evidence limits

| Path | Reachable operation and governing boundary | Evidence and remaining work |
| --- | --- | --- |
| MemoryTurnStart hot and retrieval siblings | LoadMemory uses governed read; MemoryRetriever uses supplied authorized corpus. | Delegation tests pass. Raw memoryHash/injection state also requires admission before side effects; F1's full composer is the useful boundary. |
| MemorySystem.find | Calls MemoryRetriever.getRelevantContext. | Source trace establishes delegation; do not misclassify it as a raw reader merely because its own function lacks memoryAccess. |
| MemoryWriter read/set | Native RPC, observed revision, managed full-list replacement. | Existing CAS, caller denial, unmanaged control, and stale reviewer tests pass. Pure parse/serialize helpers are not authorization boundaries. |
| MemoryReviewer | Filtered exchanges, governed current snapshot, governed add and automatic proposal decisions. Stop hook inherits environment into detached reviewer. | Existing 10 delegation plus 6 proposal-delegation tests pass. This audit did not execute a full detached cadence-to-inference-to-publication lifecycle. Preserve its cadence when extending governance. |
| PULSE/lib/memory-proposals | Queue load and accept/reject/edit/applied-elsewhere delegate; direct queue/apply/mark writers refuse managed mode. | Six real native delegation tests pass. That does not govern modules/memory.ts raw queue reads. |
| LoadContext, learning-readback, advisory-readback | Gated native source paths, exact retained text and timestamp filtering, attested advisory reads. | 17 source tests pass. They do not govern unrelated native diagnostics, wiki, graphs, or derived writers. |
| PULSE/edit/edit-handler.ts | Exported applyEdit raw hot-file overwrite. | Real function rewrites forgotten bytes and causes current-reference conflict. **No production caller/import found** in searched PULSE TS production files. Treat as latent writer capability, not a proven HTTP endpoint. |
| PULSE/wiki | pulse.ts forwards wiki routes; index and detail readers open raw knowledge/work/learning/wisdom bodies. | Source-traced boundary gap. Direct handler probe failed before execution because prepared PULSE cannot resolve minisearch. Exact stderr retained; no behavioral success claim. |
| PULSE/Observability memory graph | `/api/memory/graph` serves stored graph titles/tags generated by MemoryGraph. | Source-traced cached derivative. Need build-then-correct/forget-then-fetch test and actual listener authentication trace. No server run here. |
| ProposalGC | PULSE.toml schedules `--auto`; direct rename rewrites proposal sections in always-loaded identity/project/config files. | Source-traced writer outside managed transaction. Test approved GC, concurrent proposal approval, target revision invalidation, and error behavior before changing its removal semantics. |
| SessionHarvester and LearningPatternSynthesis | PULSE.toml schedules transcript harvest and weekly synthesis; deriver has additional frame and inference paths. | Selected source sections show raw reads and derived writes. Whole command graphs, generated-input admission, and publication were not run. These are priority remaining behavioral gates, not confirmed end-to-end model leaks. |
| WorkCompletionLearning and SatisfactionCapture | Registered hooks directly write learning/feedback records from session and work content. | Captured records have governed downstream readers, but write provenance/grants and alternate consumers remain unverified. Historical capture is distinct from activating a current fact. |
| PULSE hypotheses/work/upgrades | Raw frame decisions, ISA/cache reads, and upgrade consumers appear in selected source. | Partial trace only. Need current route auth, grant binding, retired-text behavior, and publisher transaction evidence. |
| CortexHealth index digest | Enumerates raw canonical source to compute digest. | Source hash/count exposure is distinct from returning body text. Its free-form reviewer error exposure is confirmed separately in F3. |

## Recommended implementation sequence

1. **Close the registered turn-start composer.** Reproduce F1, govern the complete source collection before cursor/injection side effects, and keep owner current delta/heartbeat behavior. This immediately protects a loaded prompt path. Parent changes are pending separate fresh-source review.
2. **Close the shared diagnostic/readback boundary and direct PULSE memory snapshot.** Introduce caller-bound, typed diagnostic output and authentic PULSE request scope. Verify owner controls before replacing raw consumers. Include MemoryStatus, MemoryInsights, CortexHealth report readback, and free-text fields in health/freshness.
3. **Close alternate corpus readers.** Use the same authorized record/source selection for Cortex, KnowledgeQuery, wiki, and graph projections. Start with deterministic CLI and handler fixtures, then actual authenticated route and cache invalidation tests. Resolve the missing PULSE dependency through the project dependency process before claiming wiki behavioral coverage.
4. **Close managed restore and staged publication.** Route supported recovery and harvester promotion through current reference validation, the cooperating transaction, and durable receipts. Then test concurrency and interruption. Include the smoke-test raw restore path and scheduled ProposalGC before claiming all native writers cooperate.
5. **Trace the remaining capture, synthesis, and application routes.** Keep owner learning and reviewer cadence. Establish source permission before model calls, authorized publication afterward, and destination permission before delivery. Record static-prompt and Siri credential binding explicitly. The 95 untraced inventory candidates remain a work list, not a clean result.

This order follows reachability, dependency on shared boundaries, and ease of confirming behavior. It is not a recommendation to ship separate partial production releases.

## Tests, failures, and controls

Independent command:

```sh
PYTHONPATH=.:tests \
LIFEOS_MEMORY_SOURCE=/home/outsider/.cache/lifeos-plugin-memory/source-gate-20260930-app-startup/lifeos/LifeOS/install \
LIFEOS_HERMES_SOURCE=/home/outsider/.cache/lifeos-plugin-memory/source-gate-20260930-app-startup/hermes \
/home/outsider/.cache/lifeos-plugin-memory/memory-plugin-test-env/bin/python \
-m unittest test_memory_delegation test_memory_sources test_memory_proposal_delegation -v
```

Result: **33 passed, 19.651 seconds, exit 0**. No broad plugin suite was rerun by this reviewer. The parent's reported complete 622-case regression is separate evidence and does not replace these missing-path probes.

The probes intentionally observe defects instead of asserting the desired safe outcome. Their successful process exit means the measurement completed, not that memory governance passed. The initial writer observer failed on the correctly raised MemoryConflict and was amended only to record that outcome. The wiki process failed with `Cannot find package 'minisearch'`; no dependency was installed and no implementation was altered to bypass that failure. All other recorded probe subprocess stderr was empty except the context builder's structured warning lines, which are part of stdout and captured verbatim.

## What deserves Adrian's review

The main product decisions are how trusted local PULSE access maps to memory authority, and how intentional owner recovery interacts with retired claims. Existing native features should remain useful for the owner: diagnostics, context, curation cadence, snapshot recovery, staged promotion, and native corpus navigation need governed implementations rather than blanket suppression.

This audit does not approve ownership activation or prove all 132 candidates safe. It does not prove full session resume repair, changed-SOUL repair, compression rotation, Responses repair, restricted static prompting, every model route, delivery authorization, browser behavior, installation recovery, backups, or the full reviewer/deriver lifecycle. Only private fixtures and repository evidence files were written. No live services, accounts, settings, memory, or journal were accessed or changed. No implementation edits, commits, or pushes were made by this reviewer.
