Date: 2026-10-01
Role: Fresh independent architecture, code, and behavior reviewer
Question: Does the Hermes and native LifeOS memory implementation preserve its approved contracts across independently tested units?
Model: GPT-6, inherited from the parent. The exact model variant is not exposed in this agent context.

Adrian, I found four confirmed defects in existing implementation paths. The architecture still matches the accepted ownership direction. These failures need correction before activation, alongside the separately documented incomplete work. No implementation, deployment, credential, or ownership change was made by this review.

The selected regression passes **188 tests with no failures, errors, or skips**. The new reproductions still fail their intended contracts. Existing green tests therefore do not close these interfaces.

## Ranked new findings

### F1. Dashboard memory controls bypass the installation owner binding

**High. Confirmed private fact disclosure and native mutation.**

Source: `lifeos_hook_bridge/dashboard/plugin_api.py:109`, `:144`, `:151`, `:158`, `:165`, `:172`, `:177`; `lifeos_hook_bridge/memory_preferences.py:63`, `:67`. The newly protected PULSE route checks an actual verified Session and passes its qualified account to `pulse_snapshot`. The other memory controls do not consume the current Session or check its account binding. `review` constructs an unrestricted `dashboard:owner` scope.

Real reproduction uses the prepared Hermes BasicAuth provider, actual authentication middleware, FastAPI HTTP requests, and real Bun/native fact persistence in a synthetic profile:

1. An owner logs in, then the private memory configuration removes that dashboard account binding.
2. `GET /memory/pulse/snapshot` correctly returns 403.
3. `POST /memory/review` with `lifeos_memory_search` still returns 200 and the private principal fact.
4. `POST /memory/sharing` with `enabled: true` still returns 200 and enables sharing.
5. The same revoked session executes `lifeos_memory_forget`, receives `status: committed`, and actual native recall returns an empty result afterward.
6. A distinct real BasicAuth user, `synthetic-other`, with no memory owner binding logs in successfully. PULSE returns 403; the review search still returns the principal fact.

The optional no-gate control also returns private facts from `/memory/review` without an authenticated Session. This does not demonstrate exposure of a running installation. The authenticated unknown-account and revoked-account controls already establish the defect independent of that control.

Impact: removing the memory owner binding protects the new PULSE read route but leaves an alternate private read route and destructive owner controls usable. The same inconsistency reaches adoption, sharing, and enrollment/revocation routes by code inspection. Enrollment itself was not attempted by this probe.

Smallest fix: use one request authentication and installation-owner check for every memory route that needs owner authority. Pass the qualified verified account into preferences actions, and check it from the same fresh configuration load as root selection and scope construction. Do not use a binding check from one configuration snapshot with a later privileged action from another. Apply the private response-header policy to private memory read/review responses as appropriate. Preserve the existing host authentication contract.

Required regression: real approved-owner controls, distinct authenticated unknown account, revoked binding on an open authenticated client, disabled host gate, and refusal before native reads or mutations across every memory route. Include search, forget, sharing, and synthetic enrollment controls.

Evidence: `raw/probe-results.json`, `raw/dashboard-extra-results.json`, `raw/probe_review.py`, `raw/probe_dashboard_extra.py`.

### F2. Explicit remember publishes into an unadopted hot file that native governed readers reject

**Medium. Confirmed incompatible publication and read behavior.**

Source: `lifeos_hook_bridge/memory_access.py:545`, especially `:555` and `:558`. Explicit `remember` takes the hot-file branch through native `add`, then records only the submitted fact. It does not call `_hot_snapshot` to verify the current file against recorded active entries. In contrast, the native add and curation paths use `_hot_snapshot` before publication, and `read_hot` enforces that check at `:376`.

Real reproduction:

1. Native unmanaged `MemorySystem.add` publishes `RULE: Synthetic unmanaged control` into an isolated principal file before adoption.
2. Governed `remember` appends `RULE: Synthetic governed addition` and returns `status: committed` with a reference.
3. The file now contains both entries, while SQLite records only the submitted entry.
4. Governed `read_hot` raises `MemoryConflict: Native hot memory changed outside governed publication; review it before adoption`.
5. Explicit registry recall returns the submitted fact, demonstrating that one interface reports a usable current fact while the native full-file reader remains unusable.

The receipt truthfully identifies a physically written fact. Its defect is accepting and publishing into a state that the other governed interface refuses, while adding no requirement to complete adoption first. This is distinct from the documented incomplete MemoryRestore implementation: the failing mutation is the existing governed explicit remember operation.

Impact: fresh native data or later out-of-band changes can let the explicit tool save more facts while native hot recall and PULSE remain blocked. The publication advances a partially indexed store instead of refusing before modification. The probe does not show erased facts or an incorrect reference for the new fact.

Smallest fix: verify the full current hot snapshot in the same cooperating transaction before explicit hot remember, and publish through the existing verified curation path. Unadopted or changed content should return a conflict before publication. Keep adoption an explicit reviewed operation, with truthful provenance.

Required regression: before adoption, after adoption, after an out-of-band addition, and after an out-of-band recorded-entry change. Verify both receipt and native governed read behavior, plus unchanged bytes on refusal. Preserve ordinary explicit remember and duplicate semantics.

Evidence: `raw/probe-results.json`, probe `remember_with_unadopted_hot_content`.

### F3. Diagnostic dynamic-key filtering breaks native fixed-shape health reports

**Medium. Confirmed fail-closed availability failure.**

Source: `lifeos_hook_bridge/memory_diagnostics.py:35`, `:93`, `:339`; native `LIFEOS/TOOLS/lib/MemoryAccess.ts:114`, `:125`, `:135`; native `LIFEOS/TOOLS/MemoryHealthCheck.ts:311`, `:408`.

The Python projection correctly tries to remove retired content from dynamic dictionary keys. Its fixed-field inventory does not include all native numeric finding-detail fields. Native `filterMemoryDiagnostic` requires the projection to retain every original dictionary key through `sameDiagnosticShape`. The two contracts disagree.

Real reproduction saves and forgets `RULE: begins`, then gives the real native principal file one BEGIN marker and two END markers. With the connector present, `MemoryHealthCheck.ts` returns only generic unavailable JSON and does not publish a health log. Without retiring the word, the same managed corruption produces the intended critical `markers-corrupt:principal` finding. With the connector removed, the same corruption and retirement also produce the intended native critical finding.

A smaller direct native contract probe isolates the cause. Python filters this native-shaped detail:

```json
{"findings":[{"severity":"critical","detail":{"begins":1,"ends":2,"inverted":false}}]}
```

It returns the detail with `begins` omitted. The actual native `filterMemoryDiagnostic` then throws `The native diagnostic service returned an invalid result`.

Impact: an otherwise legitimate forget operation can suppress a later real structural-health diagnosis and its publication. It does not leak the retired claim; the failure is closed. Counts, clocks, and enums tested in the prior health closure do not cover every numeric fixed finding field.

Smallest fix: declare the native fixed finding-detail fields in the correct schema locations and align the Python projection with the native response contract. Keep dynamic content keys governed. Do not relax the native validator to accept arbitrary missing keys without establishing the diagnostic schema. Verify the other actual native finding-detail shapes, including shape differences inside Cortex assessment evidence.

Required regression: actual native health calls after retiring each fixed detail field, legitimate warning/critical outcomes preserved, dynamic keys still omitted or safely represented, and publication matching stdout. Direct Python projection alone is insufficient.

Evidence: `raw/control-results.json`, `raw/dashboard-extra-results.json`, `raw/probe_controls.py`, `raw/probe_dashboard_extra.py`.

### F4. A denied reference mutation reads its source before authorization

**Medium. Confirmed source-access ordering violation; no proven response disclosure.**

Source: `lifeos_hook_bridge/memory_access.py:299`, `:300`, `:340`, `:343`, `:715`; `lifeos_hook_bridge/memory_transaction.py:74`, `:78`.

`_operation` computes publication paths and prepares backup copies before invoking the mutation callback. For reference operations, `_publication_paths` selects the record without checking the scope. `prepare` reads the entire source into a private recovery journal. Only the callback subsequently calls `_target` and rejects a caller without write permission.

The probe writes a private principal fact with an owner grant, then calls forget using the project-only READER scope and that reference. Python's actual file-open audit records a read of `PRINCIPAL_MEMORY.md`, followed by its publication flush open. The returned receipt is correctly rejected with `The memory reference is unavailable or has no write grant`.

Impact: a restricted supported operation crosses its category authority boundary and creates a recovery copy before refusal. An interruption in that interval can leave the unauthorized operation's private journal for later recovery. The probe does not demonstrate that the requester can read that journal, that secret text is returned, or that the denied request changes facts. Same-UID arbitrary filesystem access remains outside the claimed interface boundary.

Smallest fix: resolve and authorize the target reference, including the required revision/status checks, before computing and reading publication paths. Keep that preflight and publication under the same cooperating lock. The journal should receive only destinations for an already authorized operation. Preserve safe retry and crash-recovery behavior.

Required regression: an actual file-open audit for denied correct and forget across category and project grants, plus allowed-operation and interruption/recovery controls. A test that only asserts a rejected receipt misses the violation.

Evidence: `raw/control-results.json`, probe `source_authority_before_journal`.

## Architecture and implementation direction

The core ownership choice remains appropriate: native LifeOS files hold authoritative fact bodies; the SQLite registry holds references, revisions, retirement fingerprints, writer/source metadata, and operation receipts. The temporary publication journal supports recovery instead of introducing an editable competing fact store. Hermes keeps its own conversation and procedural-skill responsibilities. The provider supplies explicit tools while the native hooks own automatic recall and review.

The shared policy uses qualified account bindings, destination visibility, exact participants, project/category grants, proposal capabilities, and approved model routes. The current Hermes runtime explicitly refuses restricted installed identity prompts and unknown routes. This is an honest capability limit. The optional MCP service resolves server-owned grants for each tool call, and restricted SSH enrollment separates key-bound identities from caller tool arguments. These mechanisms support the design, but F1 shows that dashboard owner capabilities are a second authority path with inconsistent entry checks.

There is no reason from these findings to replace the architecture. The avoidable complexity is maintaining multiple implicit contracts: separate explicit and native hot-write paths, a Python diagnostic schema and a native universal shape assertion, and privileged dashboard actions without a common owner entry point. Consolidate those contracts using existing paths and shared invariants. Do not add another memory store or another extractor.

Recovery code serializes cooperating operations, reserves an unknown receipt before native publication, flushes files before final metadata commit, and restores journaled files after interrupted outcomes. The selected native/proposal tests pass. F4 shows that recovery preparation cannot be treated as exempt from authorization. This review does not establish power-loss durability for every publication or the future whole-install ownership transaction.

Capability checks remain bounded. Provider availability checks a host middleware API version, the ownership flag, and the native access file. Status probes native retrieval and proposal exports. Those checks are not a release-readiness assertion and do not establish complete native reader/writer coverage. The distributed native memory patch and its installed-plugin copy have identical bytes; source preparation lists nine Hermes patch groups and ten LifeOS patches, including the 17-file native memory patch. No fresh packaging/update transaction was run here.

## Separately documented incomplete work

These are release blockers already identified by the implementation plan and source audit, not newly discovered defects in this report:

- Native PULSE HTTP relay and browser credential integration; raw native memory HTTP handling is outside the closed governed projection/owner API unit.
- Alternate corpus, graph/wiki, context-builder, and derived readers; full current source coverage is not established.
- Managed restore, staged promotion/publication, and their interaction with registry and retirement metadata.
- Restricted rendered prompts and final audience delivery, full lifecycle/resume repair, changed installed prompt reconstruction, complete compression rotation, and outstanding Responses repair.
- Fresh ownership setup, backup, restore, update, rollback, source/schema migration, and the complete release gate.

The prior audit inventories 132 candidates and reports sections traced in 37 plus eight additional files, leaving 95 untraced. This review does not upgrade that coverage claim. The broad historical 639-case suite also predates later changes. Do not represent the 188 selected cases here as a current full-system gate. Running installations must keep memory ownership and sharing disabled until their respective activation requirements pass.

BasicAuth cookie logout does not revoke copied stateless bearer tokens. That is the documented host contract, not a new finding. F1 concerns the private memory binding that is already supposed to deny the next memory request.

## Verification and suggested correction order

All three reproduction programs run successfully as observation programs, with their contract failures recorded in JSON rather than hidden behind test success. The selected existing regression command is:

```sh
PYTHONPATH=.:tests \
LIFEOS_MEMORY_SOURCE=/home/outsider/.cache/lifeos-plugin-memory/source-gate-20261001-cortex-final/lifeos/LifeOS/install \
LIFEOS_HERMES_SOURCE=/home/outsider/.cache/lifeos-plugin-memory/source-gate-20261001-cortex-final/hermes \
/home/outsider/.cache/lifeos-plugin-memory/memory-plugin-test-env/bin/python -m unittest -v \
  test_memory_native test_memory_curation test_memory_service test_memory_proposals \
  test_memory_diagnostics test_memory_cortex_health test_memory_pulse test_memory_pulse_auth \
  test_memory_runtime test_memory_sharing test_memory_context test_memory_adoption
```

Result: 188 tests, 122.313 seconds, OK, no skipped cases. Full per-case output is `raw/regression.log`; exit marker is `raw/regression.done`.

The first auxiliary control program had a missing `finally` and failed with a SyntaxError before any probe executed. Its source and log are preserved as `raw/probe_controls-first-failed.py.txt` and `raw/controls-first-failed.log`. The corrected program includes fixture cleanup and completed with exit 0. This was a reviewer probe error, not an implementation failure.

Recommended sequence follows dependency and risk:

1. Close dashboard owner authorization across all memory routes, because private reads and destructive controls already have a demonstrated alternate entry point.
2. Move reference authorization before recovery source access, preserving the current transaction protocol.
3. Make explicit hot remember share current-file verification with native publication.
4. Reconcile the health projection schema and native shape contract, with actual health publication controls.
5. Continue the already planned native coverage and activation gates, then run the complete compatibility/release package gate.

Each finding needs a failing behavior regression before its fix. The existing 188 cases should remain green, but their success cannot substitute for the added cross-interface probes.

## Evidence identity, scope, and limits

Reviewed branch: `feature/lifeos-memory`. Plugin HEAD remained `e313d322f36937ce0b84cd37e29b97724744fa22`. Native public base: `5e2f2e8c0abde612da0e99c16c0d07d4ec21b88c`; Hermes public base: `758ad514eb0e800547e015edf05aa18f78b78d82`. Only the owned prepared public source, the project, and disposable synthetic profiles were used. No live Hermes checkout was imported or bootstrapped. No .211, .213, or running .212 installation was accessed.

`raw/before-hashes.json` and `raw/after-hashes.json` compare 38 captured implementation/native/document files: no captured source hash changes occurred. `raw/source-drift.json` records that limited drift audit. It is not a hash audit of every file in either source tree. `raw/patch-packaging.json` proves distributed memory-patch equality. `raw/git-before.txt` and `raw/git-after.txt` retain repository identity/status. Only this review's evidence files were written by the reviewer.

`raw/review-inventory.md` distinguishes complete small-module reads, focused source sections, test inspection, and unreviewed areas. Source snapshots are evidence preservation and do not mean every line was reviewed. The reports and test logs for previous closures were used to understand claimed limits, not as proof for these new failures.

No live model inference, actual native PULSE server/browser, real remote enrollment, production deployment, complete host SDK/model suite, complete plugin suite, or native 132-file inventory was exercised by this review. No implementation changes, commits, dependency installation, or network messages were made. Native health and file behavior were real; HTTP requests used real in-process FastAPI and prepared-host authentication, without a live service.

Adrian's review should focus on the scope of owner authority across all dashboard controls, adoption behavior before hot-file mutation, and which health fields are schema versus content. The riskiest unresolved integration remains activation across all native consumers and whole-install lifecycle/update transactions.
