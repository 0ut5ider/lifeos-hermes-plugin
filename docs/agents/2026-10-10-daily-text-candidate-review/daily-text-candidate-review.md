Date: 2026-10-10

Agent role: Independent code reviewer.

Question: Does the complete proposed LifeOS/Hermes daily text candidate introduce actionable correctness, authorization, data preservation, concurrency, recovery, or integration defects?

Model: GPT-6, Codex harness. The exact backend variant and reasoning setting are not supplied in this reviewer's task context.

Pinned HEAD: `bf53c16dd23d72c9824843cbb85f31db5a48e723`.

Base: `c0b26bd57d6abf5364f60e3c33c6b3bea53c5ab8`.

Repository: `/home/outsider/Projects/Hermes_agent/LifeOS_plugin`.

Candidate branch: `feature/discord-acceptance`. No GitHub PR exists yet.

Two defects are confirmed: one P1 authority defect in three native batch publishers, and one P2 Algorithm recovery defect. Both have reproducible evidence against the actual committed candidate. The P1 affects two commands selected for the daily schedule. I do not recommend accepting this candidate unchanged.

The review uses real native Bun programs, real SQLite transactions, real synthetic owner configurations, and disposable local HTTP servers. Probes insert one deterministic scheduling point around the actual file publisher, call the original publisher, and then perform a real configuration or file edit. They do not replace native rendering, authorization, transaction handling, or HTTP responses. The source tree remains unchanged. No service on a shared server, personal memory, real Discord recipient, credential, deployment, push, or commit is used.

## P1: Native batch publishers continue to mutate files after the owner is revoked

Primary changed location: `lifeos_hook_bridge/memory_session_harvest.py:170-179`.

Also confirmed in changed locations `lifeos_hook_bridge/memory_proposal_gc.py:91-102` and `lifeos_hook_bridge/memory_knowledge_harvest.py:242-255`.

The outer response check is `lifeos_hook_bridge/memory_service.py:260-265`. The transaction finalization path is `lifeos_hook_bridge/memory_access.py:123-141` and `:353-378`.

**Trigger.** A valid owner starts a supported native batch operation. The operation passes its source and owner checks, publishes its first file, and the owner account binding is then removed from the real memory configuration. At least one additional destination remains in the batch.

**Observed behavior.** Each of these new publishers checks current authority before its loop, then performs the remaining mutations without another owner check inside the transaction. The transaction records a committed receipt and removes the publication journal. Only afterward does `MemoryService.native` notice the revoked account and return `EACCESS_CHANGED`. That response withholds the result; it does not reverse the already committed file mutations.

The default consolidation reproduction uses two genuine admitted Hermes transcripts and the actual native extractor with `mine=False`. The observed sequence is:

1. The publisher writes the first correction learning.
2. The probe removes every owner account binding using `MemoryConfiguration.update`.
3. The publisher writes the second correction learning.
4. The service returns `ok:false`, `code:EACCESS_CHANGED`.
5. Both learning files remain. SQLite records `status:committed`, `count:2`, `sessions:2`. The journal is absent.

The ProposalGC reproduction uses actual native `--auto` semantics on two source files. It publishes `OPERATIONAL_RULES.md`, revokes the owner, then rewrites `PROJECTS.md` and appends the cleanup log. The second source loses its superseded proposal after revocation. The response is `EACCESS_CHANGED`, but both changed files and the committed receipt remain, with no journal.

The KnowledgeHarvester reproduction stages one real synthetic queue item. After its first Markdown publication and owner revocation, it writes `.harvest-state.json` and deletes the original JSON queue input. Its service response is also `EACCESS_CHANGED`, while SQLite says committed and the journal is absent. The staged content is retained; the demonstrated defect is mutation and queue consumption after authority changes, not total loss of that content.

**Consequence.** Revocation fails to stop further writes or queue deletion in an admitted batch. A user-visible refusal cannot be used to infer that no mutation occurred. This affects the release's default consolidation and cleanup jobs, plus the supported Knowledge harvesting operation.

**Reproduction.** From the repository root, each command below records its exact environment overrides, arguments, duration, exit code, stdout, and stderr through `run_review.py`:

```bash
python docs/agents/2026-10-10-daily-text-candidate-review/run_review.py harvest-revocation-default /home/outsider/.cache/lifeos-plugin-memory/memory-plugin-test-env/bin/python docs/agents/2026-10-10-daily-text-candidate-review/probe_harvest_revocation.py --default
python docs/agents/2026-10-10-daily-text-candidate-review/run_review.py proposal-gc-revocation /home/outsider/.cache/lifeos-plugin-memory/memory-plugin-test-env/bin/python docs/agents/2026-10-10-daily-text-candidate-review/probe_batch_revocation.py proposal-gc
python docs/agents/2026-10-10-daily-text-candidate-review/run_review.py knowledge-harvest-revocation /home/outsider/.cache/lifeos-plugin-memory/memory-plugin-test-env/bin/python docs/agents/2026-10-10-daily-text-candidate-review/probe_batch_revocation.py knowledge-harvest
```

All three probes exit zero with their defect assertions satisfied. Evidence: [default consolidation](harvest-revocation-default.json), [proposal cleanup](proposal-gc-revocation.json), [Knowledge harvesting](knowledge-harvest-revocation.json). A separate [mining reproduction](harvest-revocation-two-writes.json) confirms the same behavior for two harvested review candidates.

**Minimum correction.** Recheck the initiating owner's current configuration and audience before every mutation, including record transitions and source deletion, and before returning a committed batch receipt. A changed grant must abort through the recoverable transaction path while the receipt is unknown and the journal still exists. Add a regression that revokes the owner between actual publications and requires later writes to stop and recovery to restore the prior artifacts. Test default consolidation, automatic cleanup, and Knowledge queue consumption. Do not solve this by weakening the final response check.

**Introduction and limits.** All three publisher modules are additions since the pinned base. These reproductions exercise `MemoryService.native` and native rendering with app-neutral synthetic owner contexts. They do not run a live scheduler or Discord permissions change. The demonstrated failure uses an actual account configuration change, so it does not depend on network timing or stale Discord caches.

## P2: Algorithm edits finalize a conflict after publishing, leaving no recovery journal

Primary changed locations: `lifeos_hook_bridge/memory_algorithm_edit.py:175-180` and `:188-200`.

Interaction: `lifeos_hook_bridge/memory_access.py:369-378` catches `MemoryConflict` from the callback, saves a finalized conflict receipt, and follows the normal commit path. `lifeos_hook_bridge/memory_transaction.py:224-229` then removes the journal.

**Trigger.** An authenticated owner publishes a new doctrine version. Another owner process edits an admitted Algorithm source after publication begins but before `_matches` validates the complete source set.

**Observed behavior.** The real editor publishes the new version, changelog, and `LATEST`. The probe then edits the earlier `v3.2.1.md` source immediately after the real `LATEST` publisher returns. `_matches` detects the changed source and raises `MemoryConflict`. `_operation` catches that exception as a normal conflict receipt, commits the operation, and deletes its journal. The editor reports that publication needs recovery, although its recovery reservation has already been removed.

The authenticated native HTTP reproduction returns HTTP 503. At that point:

- `LATEST` is `3.2.2`, rather than the original `3.2.1`.
- `v3.2.2.md` and the new changelog entry remain.
- The concurrent edit to `v3.2.1.md` is preserved.
- SQLite records `status:conflict`, with reason `Algorithm publication preserves later source edits`.
- The journal is absent before and after opening a fresh native memory transaction.

A direct native reproduction independently shows the same state. The failure occurs before the Git commit call, so this reproduction does not depend on Git hooks, repository setup, or the previously tested commit timeout.

**Consequence.** The owner receives a failed-save response while the active Algorithm version advances. A fresh transaction cannot perform the recovery that the failure message requests. Retrying can operate on an already advanced version. The concurrent source edit itself remains preserved, but the requested operation is finalized despite failing its post-publication consistency check.

**Reproduction.**

```bash
python docs/agents/2026-10-10-daily-text-candidate-review/run_review.py algorithm-http-conflict /home/outsider/.cache/lifeos-plugin-memory/memory-plugin-test-env/bin/python docs/agents/2026-10-10-daily-text-candidate-review/probe_algorithm_http_conflict.py
python docs/agents/2026-10-10-daily-text-candidate-review/run_review.py algorithm-conflict-probe-fixed /home/outsider/.cache/lifeos-plugin-memory/memory-plugin-test-env/bin/python docs/agents/2026-10-10-daily-text-candidate-review/probe_algorithm_conflict.py
```

Both probes exit zero with their defect assertions satisfied. Evidence: [actual HTTP response and persisted artifacts](algorithm-http-conflict.json), [independent direct reproduction](algorithm-conflict-probe-fixed.json). The first version of the direct probe failed because its observation code attempted to express an isolated render path relative to the installed fixture; [that probe error](algorithm-conflict-probe.json) is preserved and is not a product failure.

**Minimum correction.** Treat a failed consistency check after publication as a recoverable abort. Preserve the unknown receipt and journal until recovery can restore the operation's unchanged destinations while preserving the later owner source edit. Do not convert a post-publication abort into a finalized conflict receipt. The simplest local correction can use an exception path that the transaction treats as an abort; a broader transaction change must preserve normal pre-publication conflict semantics. Add an authenticated HTTP regression that checks both the failed response and recovery of `LATEST`, changelog, and the new version. Audit the other newly added post-publication `MemoryConflict` callers for the same contract mismatch.

**Introduction and limits.** The Algorithm editor is new since the pinned base. The generic conflict finalization contract predates it. This finding is the new caller's use of that contract after it has published artifacts. The HTTP probe runs the actual native handler and authenticated local dashboard. It does not test live systemd, an actual owner's repository, or browser JavaScript.

## Source identity and reviewed scope

[review-identity.json](review-identity.json) records the pinned Git identity, tracked status, changed runtime/test inventory, patch hashes, registries, canonical source manifests, and native behavior file comparisons. [finding-source-lines.txt](finding-source-lines.txt) retains the exact cited source excerpts.

All 11 Hermes patches and 25 LifeOS patches have byte-identical packaged copies. The install and prepare-source registries agree. Both complete prepared source trees validate against their manifests, and their selected patch hashes match the current candidate. Seven behavior files used by the dependency-reuse native source match the canonical prepared source byte for byte, including MemoryAccess, all three affected batch tools, Algorithm, user-index, and Content. The runtime diff passes `git diff --check`. Tracked Git status remains clean.

The scope checklist describes coverage rather than declaring the unchecked branches safe:

- [x] Read the task brief, shared AGENTS instructions, coding-rules, its JavaScript reference, and experiment-method.
- [x] Read the base/head runtime inventory, patch registry, source preparation path, and source-manifest/patch identities.
- [x] Review current memory configuration, authority resolution and final response checks, the native operation dispatcher, publication reservation, recovery, expected digests, and preserved later artifacts.
- [x] Review hot/archive write and recall boundaries, retirement filtering, fixed source path checks, operational snapshot collection, user-index publication, Content action/disposal, and fixed file moves.
- [x] Review and reproduce default session consolidation, proposal cleanup, Knowledge harvesting, and Algorithm editing at actual mutation boundaries.
- [x] Read Conduit capture, Atlas insight, LocalIntelligence refresh, manual state publication, morning-brief, Menubar, and related native dispatcher paths. Run selected native controls for these publication areas.
- [x] Review Discord audience resolution and delivery policy, inspect the prepared SDK delivery gate, and run actual SDK/HTTP private-delivery tests.
- [x] Read child inference and web research command paths and owner-job process handling. Run selected child authorization, profile configuration, shutdown, and descendant termination checks.
- [x] Read the release plan, TODO, daily deployment selection, step 1 acceptance scope, and installed acceptance record. Inspect prior PR3/PR4 findings for context. Do not repeat inherited selection findings as newly introduced defects.
- [ ] Exhaustive line and branch review of every newly added reader and all documentation/evidence files. This candidate contains 3,330 changed files; this report focuses on actual runtime changes and release boundaries.
- [ ] Complete combined repository regression sweep and production-equivalent dashboard build. The build is not run because its normal outputs would mutate shared prepared source/dependency paths.
- [ ] Independent live browser, private-channel admission/delivery, systemd scheduling/restart, recovery backup, or separate daily guest acceptance.
- [ ] Exhaustive fresh preparation/installation, remote compatibility, current-account changes across every endpoint, every patch interaction, and adversarial concurrent filesystem alias replacement.

The accepted deferrals remain accepted: voice and Content media processing, import/reverse migration, the complete Hermes-managed installer, and the native Pulse Hermes core-file editor. Atlas initialization, real private-channel admission/delivery, final combined regression/review, final release backup, and separate daily deployment remain open launch gates. They are not counted as missing implementations. The existing acceptance documents distinguish their earlier packages and installed stages from those open gates; this review supplies no deployment approval.

## Tests and failure accounting

Every test/probe invocation has a same-named JSON command record and log file. `data.json` assembles the exact arguments, environment overrides, exit codes, timings, stdout, stderr, findings, and evidence locations. Passing defect probes mean that the assertions reproduced the defect, not that the product behavior is correct.

| Run | Actual result | Scope and limits |
| --- | --- | --- |
| `discord-tests` | 52 tests, unittest reports OK, exit 0; one ResourceWarning | Actual Discord SDK/HTTP synthetic delivery, audience, child command controls, daily profile, optional text release, shutdown, and owner process cancellation. Output is not warning-clean. |
| `algorithm-regressions` | 19 tests pass, exit 0 | Actual authenticated Algorithm editing, immutable tags, interrupted publication, real Git hooks and commit timeout. Does not cover the newly reproduced post-publication conflict. |
| `publication-clean` | 69 tests pass, exit 0 | Current publication authority, recovery, bounded owner output, user-index publication, Content disposal, response authority, Algorithm transport, native Content actions. |
| `native-types` | 5 tests pass, exit 0 | Native dashboard TypeScript check without emitting or incremental outputs, native configuration/import behavior, subordinate tab rendering, and health JSON source check. |
| `native-regressions` | 95 tests attempted, one failure and 19 errors, exit 1 | The Algorithm fixture requires `LIFEOS_HERMES_SOURCE`; the first runner omitted it. All 19 Algorithm setup errors are recorded. The failure is the standalone staging fixture described below. |
| `staging-isolated` | 12 tests, one failure, exit 1 | Repeats the standalone staging fixture failure in isolation. The other 11 checks complete. |
| `remaining-native` | 55 tests attempted, one loader error, exit 1 | I mistakenly named a nonexistent `test_memory_conduit_publication` module. The other 54 tests complete; the corrected invocation is recorded separately. |
| `remaining-native-corrected` | 96 tests, one failure, exit 1 | Corrected modules plus proposal cleanup and Knowledge mining. All other 95 checks complete. The failure is the same managed-context contradiction in the standalone Knowledge mining fixture. |
| `unmanaged-compatibility` | Three real native operations pass, exit 0 | Standalone rejection, promotion, and harvesting without a connector or managed context. |

The standalone staging and Knowledge mining failures are fixture contradictions, not evidence of a supported unmanaged runtime regression. `test_memory_staging.native_call(managed=False)` removes the connector but still exports a managed `LIFEOS_MEMORY_CONTEXT`, because its default `context=True` remains active. The current native fail-closed guard correctly refuses an admitted caller that loses its connector. Re-running the native operations with both `managed=False` and `context=False` confirms that ordinary unmanaged rejection and promotion still work. The Knowledge helper makes the same connector-removal/context-export mistake. Knowledge harvesting also succeeds under valid unmanaged inputs. The original failure is preserved; the published fixture needs correction before a clean combined regression can be claimed.

No full-suite count is inferred from selected passing checks. Tests that pass are evidence for their exercised paths. They do not establish that authority or source invariants hold between every publication step.

## Residual risk and required review

The author should review the transaction exception contract and all multi-artifact writers. The P1 requires checks while mutations remain recoverable; a final HTTP response refusal is too late. The P2 requires the recovery reservation to survive a failure after publication. Regressions should inspect persisted file bytes, SQLite receipts, and journal state in addition to checking response status.

The other new synthesis modules use post-publication source comparisons and some raise `MemoryConflict`. Their interaction with the same finalization path deserves a focused audit. This is a source-based follow-up, not another reproduced finding. Owner job process handling terminates groups on timeout/cancellation; survival of a descendant after a normally exited parent was not proved for a supported native job and is not reported as a confirmed defect.

No code correction is included in this review. Only review artifacts and disposable synthetic fixtures are written. The parent must independently rerun the retained probes and regression commands before using these findings to approve a revised release.
