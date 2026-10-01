Date: 2026-10-01
Role: Fresh independent design, implementation, and synthetic behavior reviewer
Question: Do the four memory corrections and the whole implemented memory design preserve their contracts across interfaces, and what else was missed?
Model: GPT-6.1-Sol, inherited high reasoning effort, as identified by the delegating task.

Adrian, I found four material issues in implemented paths. The first correction closes the dashboard bypass. The second closes the denied-reference recovery ordering failure. The third closes explicit remember's unadopted-file failure, but introduces a native delta-summary regression. The fourth fixes the original diagnostic fields, but misses two other fixed fields in the same native report.

The architecture does not need replacement to resolve these findings. Native fact bodies remain authoritative, the registry holds identities and lifecycle metadata, and the recovery journal contains temporary publication copies. The defects are inconsistent contracts among operations that already share that architecture.

The independent expanded gate runs **316 tests: 307 pass, 8 fail, and 1 error, with no skips**. All nine bad outcomes are in `test_memory_delta`. Three independent observation programs additionally reproduce hot-file mutation loss, incomplete diagnostic schema, and lost native source-session provenance. Their exit 0 means the observations completed, not that the observed contracts passed.

## Ranked findings

### F1. Hot correction and forgetting bypass whole-file verification and can erase a neighboring invalid entry

**Medium. Confirmed unintended native-content removal and incompatible current registry state.**

Sources: `lifeos_hook_bridge/memory_access.py:715`, `:720`, `:740`, `:743`. Compare `_hot_snapshot`, `_curate_hot`, corrected `remember`, and `native_set`.

Reproduction uses actual native Bun parsing and publication, independently for principal and assistant memory:

1. Save two governed hot facts, a target and a neighbor.
2. Change only the neighbor on disk to a recognized `RULE:` entry longer than 256 characters. Keep the target unchanged.
3. Correct or forget the target using its current reference.
4. The operation returns `committed`.
5. The native rewrite erases the overlength neighboring entry. Its registry row remains `active`.
6. A subsequent governed whole-file read fails with `Native hot memory changed outside governed publication; review it before adoption`.

All four category/operation combinations reproduce the removal. The four ordinary no-drift controls commit and remain readable. Four valid outside-addition cases commit while retaining the added bytes, but still leave governed whole-file reads blocked. The overlength fixture changes a previously acknowledged neighboring fact before mutation. The demonstrated loss is the current invalid on-disk text, rather than an untouched valid neighboring fact.

Cause: `_content` confirms only the targeted entry. The hot mutation branches then use the lenient native parser's `entries` and call `set_hot` directly. The parser's `dropped_invalid` output and the registry-to-file snapshot mismatch never stop publication. The corrected remember path now uses the stronger invariant, so these sibling operations disagree about the same native store.

A separate grant control supplies a known target reference with no read categories and hot write permission. Both correction and forgetting still read and rewrite the entire hot file. `remember`, `native_add`, and `native_set` require the whole-file read grant. This establishes an inconsistent read/write prerequisite. It does not establish fact disclosure in the response or an operating-system isolation claim.

Smallest correction: require the same hot read/write grant and verified full snapshot before hot reference mutations, inside the existing cooperating transaction. Preserve the targeted correction/forget lifecycle semantics and stable reference behavior. Do not silently use curation to classify unrelated removals. Refuse malformed or unadopted drift before publishing. Keep the existing native validation and journal recovery.

Required regression: both categories, both operations, no drift, valid outside addition, changed neighboring valid entry, invalid neighboring entry, missing read grant, byte preservation on refusal, unchanged neighboring registry rows, and usable governed reads after allowed operations.

Evidence: `raw/probe_hot_neighbors.py`, `raw/hot-neighbors-results.json`, `raw/hot-neighbors.log`, `raw/probe_delta_and_grants.py`, `raw/delta-grants-results.json`.

### F2. The diagnostic correction still omits the fixed `system` and `live` detail fields

**Medium. Confirmed fail-closed loss of a critical health diagnosis and its publication.**

Sources: `lifeos_hook_bridge/memory_diagnostics.py:39`; prepared native `LIFEOS/TOOLS/MemoryHealthCheck.ts`, hook-registration clobber finding; prepared `LIFEOS/TOOLS/lib/MemoryAccess.ts`, `sameDiagnosticShape` and `filterMemoryDiagnostic`.

The native hook-registration diagnosis constructs a fixed detail object with `system`, `live`, and `hook`. `HEALTH_DETAIL_FIELDS` includes `hook`, but excludes `system` and `live`.

Actual native reproduction:

1. Set synthetic `settings.system.json` to declare `MemoryTurnStart.hook.ts`.
2. Keep synthetic effective `settings.json` without that registration.
3. Managed no-retirement control emits and publishes the intended critical `settings-hook-missing:MemoryTurnStart.hook.ts` finding with all three detail keys.
4. Save and forget `RULE: system`, then run the same native health checker. It emits generic unavailable JSON and publishes no health log.
5. Repeat with `RULE: live`. The same failure occurs.
6. Remove only the connector in a synthetic control with the retirement unchanged. Native health again emits and publishes the critical registration finding.

Cause: retirement matching removes either undeclared fixed key. The unchanged strict native shape validator rejects the projection. The failure protects content, but suppresses the specific operational diagnosis.

This is a remaining part of the original schema defect, rather than a new reader gate or a reason to weaken the native validator. The original marker, state, invalid-entry, and Cortex assessment correction tests pass in the independent gate.

Smallest correction: declare `system` and `live` at the actual fixed finding-detail location. Enumerate all actual native object construction sites to finish that schema inventory. Keep dynamic nested content keys governed and preserve strict native shape checking.

Required regression: actual native clobber-health calls after retiring each fixed detail key, comparison to managed/unmanaged controls, preserved critical severity, and matching stdout/publication.

Evidence: `raw/probe_schema_provenance.py`, `raw/schema-provenance-results.json`, `raw/schema-provenance.log`.

### F3. Corrected explicit hot remember no longer appears in native learned-count and sample summaries

**Medium. Confirmed behavior regression and existing regression failures.**

Sources: `lifeos_hook_bridge/memory_access.py`, corrected remember through `_curate_hot` and its `set_hot` call; `lifeos_hook_bridge/memory_sources.py:118`; prepared native `hooks/MemoryDeltaSurface.hook.ts`, `AUTONOMIC_WRITER` and row filtering.

The new verified curation path logs the authenticated scope writer as `updated_by`, such as `local:owner`. The retained-log projection and native delta hook both include only rows labeled `MemorySystem.add`. The prior explicit hot add path used that label.

Real registered-composer reproduction saves one permitted explicit hot fact and returns a committed receipt. Its current hot recall appears in the composer output. Its audit row contains the exact addition, but `updated_by` is `local:owner`. The delta reports freshness with no learned count and no current learned sample. It also does not create the delta cursor that the admitted-state test expects.

The isolated cause control changes only that synthetic audit row's `updated_by` to `MemorySystem.add`. The real registered native composer then emits `+1 learned` and the correct sample. No implementation code changes or mocked composer responses are used.

The expanded regression produces eight assertion failures and one missing-cursor error, all in `test_memory_delta`. The full error output is retained. The bounded-volume case completes and fails on the missing count, rather than timing out.

Impact: an acknowledged explicit hot save remains in recall, but disappears from the native activity surface. Existing tests for current samples, cursor state, retained-claim exclusion with current controls, and log volume expose the change. This does not demonstrate missing persisted facts.

Smallest correction: preserve the native operation provenance that the existing summaries expect when an explicit add publishes through verified curation. Keep authenticated writer identity in the registry and receipt. Avoid treating arbitrary user labels as autonomic rows or weakening source admission. Native full-set curation and explicit add should retain their respective summary behavior.

Required regression: restore the whole existing delta module, then retain explicit remember's new drift/refusal and source-provenance tests. Verify ordinary native curation does not get reclassified as an add without an approved reason.

Evidence: `raw/regression.log`, `raw/regression-summary.json`, `raw/probe_delta_and_grants.py`, `raw/delta-grants-results.json`, `raw/delta-grants.log`.

### F4. Native hot adds discard the known source session

**Low. Confirmed missing attribution metadata, with correct writer identity preserved.**

Sources: `lifeos_hook_bridge/memory_access.py:517`, compared with `:524`; `memory_service.py`, native add's `source_session=context.session_id` argument; `_curate_hot` default source metadata.

Actual native reproduction uses `MemorySystem.add`, the installed native connector, real Python RPC, and real native Bun publication. The host-bound synthetic context is `chat-a:100`, session `native-session`.

A principal add commits with the correct authenticated writer `chat-a:100`. Subsequent recall returns source kind `native-curation` and session `''`. In the same native process and context, a project add returns the same writer with source kind `native` and session `native-session`.

The direct Python native-add control also reproduces this for principal and assistant memory. The source session is supplied and included in the retry payload, but the hot branch calls `_curate_hot` without passing it. The project branch explicitly records it.

Impact: new native hot facts lose a known source-session link. This does not fabricate another authenticated writer and does not affect native fact persistence or current-reference identity. It is a supported metadata contract failure, not the open backup or whole-install lifecycle gate.

Smallest correction: pass native source kind and the host-bound source session into hot add's curation path. Preserve metadata for unchanged existing entries. Assess full-set curation separately, because a newly added entry in that operation may need the same available session metadata. Do not accept caller-provided writer identity as a substitute.

Required regression: actual delegated principal and assistant adds, project control, duplicate/retry behavior, preserved existing-entry provenance, and stored metadata after restart.

Evidence: `raw/probe_schema_provenance.py`, `raw/schema-provenance-results.json`, `raw/probe_hot_neighbors.py`, `raw/hot-neighbors-results.json`.

## Verification of the four requested corrections

| Correction | Independent result | Limit or follow-up |
| --- | --- | --- |
| Dashboard owner boundary | Verified for real BasicAuth/provider/middleware regression paths, owner/revoked/unknown accounts, all protected routes, and response headers | No new bypass found. Internal `account=None` helpers remain trusted internal entry points. HTTP dependencies always return the qualified verified account. |
| Reference authorization before recovery reads | Existing actual file-open audits pass for category/project denial and stale fact references; proposal and recovery controls pass | No new denied-reference source read reproduced. This is interface authority, not protection from a hostile process with the same operating-system identity. |
| Explicit hot remember verification | New unadopted, changed-file, read-grant, adoption, duplicate, retry, and provenance controls pass | F1 finds weaker sibling mutations. F3 finds an observable summary regression caused by the changed publication path. |
| Diagnostic fixed shapes | Original marker/state/invalid-entry/Cortex detail/evidence cases pass; strict native validator stays intact | F2 demonstrates two undeclared native fixed fields. The whole health schema inventory is incomplete. |

I independently rerun both public-source smoke programs. The real localhost HTTP probe verifies all four anonymous 401 responses, all four owner 200 responses with `no-store`, forget freshness, 403 after account-binding removal, and 401 after cookie logout. The actual owned public Hermes app assembly/lifespan probe verifies middleware installation, anonymous denial, owner access, and private headers on framework 422 and 405 responses. Both exit 0. Logs are `raw/network-auth.log` and `raw/host-mount.log`.

The real host emits its pre-existing SQLite 3.51.2 WAL-reset guard warning and selects DELETE journal mode. That output is preserved in the host log. It is not a new memory finding and was not suppressed.

The exact expanded test command is preserved in `raw/run-regression.sh`. It runs the primary 15 modules plus archive, retained sources, history, delta, actual agent, children, delegation, proposal delegation, review, MCP, SSH, and the Hermes memory provider. The interpreter and both source fixture paths are exactly those requested by the primary task. Result: 316 cases in 355.663 seconds, exit 1, no skips. Its full per-case output and tracebacks are in `raw/regression.log`; `raw/regression.done` contains `1`.

## Whole-design assessment and review limits

The ownership split remains consistent: LifeOS owns durable fact bodies and native automatic memory hooks; Hermes owns conversations, compression, and procedural skills. Explicit tools and optional MCP operations share `MemoryService`, `MemoryPolicy`, native storage operations, references, and lifecycle metadata. Approved context resolution binds account, exact audience, destination, route, categories, projects, and proposal capabilities. The restricted installed prompt refusal remains an explicit supported-limit decision. No app-specific permission branch was found in the common memory policy.

The dashboard now uses a real verified host Session and a current owner mapping. Preferences actions bind root selection and scope to the same loaded configuration. Configuration mutation actions recheck root and owner inside the update lock. The trusted optional-account helpers cannot be reached from a memory HTTP handler without the dependency's account string. The real host's stateless BasicAuth bearer contract is unchanged; account-binding removal controls subsequent private memory access.

The temporary recovery journal and SQLite reference registry are compatible with the single-authoritative-fact-store requirement. Retry keys are writer-scoped. The cooperating lock, recovery, archive offset updates, private entity gating, proposal creation/approval split, adoption preview signatures, retained-source filtering, and reference status checks receive regression coverage. Those mechanisms do not establish full crash durability for all future native writers or the forthcoming whole-install backup/restore transaction.

The most consequential design risk is duplicated implicit publication contracts. Whole-file mutation prerequisites, operational writer labels, source provenance, and diagnostic shape have different interpretations at neighboring call sites. These findings can be corrected by using existing verified paths and passing explicit operation metadata. A second fact store or replacement runtime is unnecessary.

Breadth is documented in `raw/review-inventory.md`. The review reads the governed module interfaces and implementations, dashboard owner actions, design/plan/README/correction evidence, native connector and publication helper, and selected native readers/writers/hooks. Tests cross those units with real native files and prepared-host behavior. Source snapshots preserve evidence, but do not imply every line of every snapshot was reviewed.

Known incomplete gates remain separate from these findings: native PULSE relay/browser credentials; alternate corpus, graph/wiki, and derived readers; raw restore and staged promotion; restricted rendered prompts and delivery; full lifecycle/resume/compression and Responses repair; ownership/update/backup/rollback/MCP setup; and complete release validation. The prior native candidate inventory contains 132 candidates with 95 still untraced. This review does not close that inventory or claim complete native coverage. No running ownership or sharing activation is justified by these tests.

## Evidence identity and correction order

Reviewed branch: `feature/lifeos-memory`. Source HEAD remains `e4f70aecc22054d1b4e121223f587beac5eb6981` for this entire review. `raw/before-hashes.json` and `raw/after-hashes.json` compare 32 captured implementation/native files with zero changes. `raw/source-drift.json` records that limited audit; additional finding source hashes and source snapshots are retained. This is not a hash audit of every file in both source trees.

Only owned prepared public source, project files, and disposable synthetic homes were used. No running .211/.212/.213 installation was imported, bootstrapped, read, changed, or contacted. No credentials were read, dependency installed, real remote model used, implementation edited, commit made, or deployment performed. Real synthetic HTTP model endpoints inside the existing host tests are deterministic fixtures. Remote SSH acceptance uses the existing local disposable test fixture, not an existing installation.

Suggested correction order follows dependencies and verification:

1. Finish fixed diagnostic fields and native source metadata using narrowly scoped regressions.
2. Preserve explicit-add operation labels through the verified publication path, then rerun the existing delta module.
3. Extend full hot-file verification and read/write prerequisites to correction and forgetting while preserving their lifecycle semantics.
4. Run all selected modules together, then continue the already approved remaining native and activation gates.

The primary should reproduce each finding from the unchanged scripts before source changes. F1 needs the closest review because one native rewrite updates several entries while the reference operation promises to change one record. F3 needs a clear decision about native operation labels versus authenticated writer identity. F2 needs the completed list of actual fixed diagnostic construction sites. F4 should preserve existing-entry provenance when new-entry source metadata is added.
