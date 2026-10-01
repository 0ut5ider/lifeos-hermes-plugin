# Memory implementation and activation gates

Date: 2026-09-30. Adrian authorizes implementation of the reviewed memory design now. This authorization changes the earlier implementation sequence. Hook parity remains a separate completion gate. Memory ownership and remote sharing require their acceptance evidence before activation.

## Work sequence

1. Build synthetic native fixtures and record the installed read, write, review, and context paths.
2. Implement governed native operations, stable references, truthful receipts, corrections, forgetting, and concurrent-write protection.
3. Integrate the Hermes provider and native hooks with one authenticated context policy for all messaging apps.
4. Implement optional MCP access with credential-bound grants, restricted enrollment, and active-session revocation.
5. Add the preferences page, health checks, review controls, and recoverable ownership configuration.
6. Test fresh installation, lifecycle, backup, restore, update, and failure behavior. Run the existing plugin release tests and independent review.

Native LifeOS files remain the authoritative facts. Integration metadata must not become a second editable fact store. Hooks retain automatic recall and review. Hermes retains history, compression, and skill learning.

## Current status

Implementation started on `feature/lifeos-memory`. No running memory ownership switch or remote sharing activation has occurred. Test data is synthetic. The existing `.211` and `.213` installations remain unchanged.

The current foundation includes governed native fact and proposal operations, a Hermes memory provider, required model-request admission, restricted SSH enrollment, revocation, and development preferences. Native files remain authoritative. Both interfaces use the same operations and permission policy. The provider leaves automatic recall and review to native hooks.

The initial memory foundation passes 95 tests without skips, including the real localhost SSH daemon. Its initial complete plugin suite passes 503 tests with 77 fixture-dependent skips. This does not pass the full release gate. The first full run failed because the isolated environment omitted the plugin's declared parser dependencies. Rebuilding from the complete declared core, development, and plugin requirements resolved those 86 import errors. The bounded host suite passes 131 tests. Existing and memory dashboard interface tests pass seven cases. The actual Hermes dashboard rejects unauthenticated requests with HTTP 401 and permits an authenticated synthetic-fact lookup.

The real localhost SSH test verifies restricted execution, a server-bound client identity, denied writes, private-fact exclusion, active-connection revocation, and reuse of the same native reference. Independent reviews found and closed context propagation, retained admission, installation binding, key identity, minimal grant rendering, and failed-enrollment compensation defects. The primary agent reran both enrollment failure probes. No meaningful finding remains open in that focused review.

### Remaining implementation gates

1. Complete the source and writer inventory. Adoption and bounded retained-source readback are implemented. Owner preferences expose native pending proposals and manual decisions. Native direct proposal decisions, automatic approval, edit and applied-elsewhere outcomes, pending creation, diversion, and target revision checks are implemented. These results do not establish policy coverage for every native reader or writer.
2. Filter restricted LifeOS prompts and verify model inputs and delivery destinations across representative messaging apps and scheduled tasks.
3. Complete child-agent, compression, resume, and model-call route coverage.
4. Implement the fresh ownership transaction, preserved Hermes files, coherent backup and restore, updates, and configuration rollback.
5. Run the full release gate and independent review before enabling lasting-memory ownership.

The page exposes health, current-fact search, and optional client grants. It deliberately has no ownership activation action while these gates remain open. These development controls do not change the live `.212` account.

## Required evidence

- Native remember, recall, correction, forgetting, rejected writes, and request retries.
- Safe interleaving of native reviewers and explicit clients, including stale corrections and interrupted publication.
- Allowed and denied markers in actual model inputs under the common messaging policy.
- Provider discovery and tools with both built-in lasting stores disabled, without duplicate extraction or lost skill learning.
- Optional MCP grants, denied operations, revocation, and shared access to the same native record.
- Separate profile roots, session lifecycle, child and scheduled contexts, schema checks, backup, restore, updates, and configuration rollback.

Each result must identify the fixture, source revision, command, expected result, actual result, and limits. Missing adapter metadata retains restricted access. Representative adapter tests do not establish support for untested adapters.

## Proposal foundation follow-up

The proposal operations add separate create, review, approve, and automatic-approval grants. External clients cannot hold approval grants. Native queue rows remain authoritative, and metadata records only identity, revision, status, and writer provenance. Upgrade diversion uses the native scope classifier. Exact-path publication journals recover interrupted writes without deleting unrelated files.

The proposal suite passes 11 tests. Two independent reproductions now pass: eight same-slug claims retain eight native upgrade records, and a dangling upgrade-state symlink creates no file outside USER_DATA. The full plugin suite passes 514 tests with 77 fixture-dependent skips against fresh prepared LifeOS and Hermes sources. The patch generator now covers the required model-request extension. Regeneration and ordered preparation reproduce all 56 changed host files byte for byte. Ownership activation remains disabled.

## Native proposal consumer follow-up

Native consumers now use governed decisions for all five outcomes. Separate creation and automatic-approval grants prevent creation from granting an edit. Three review findings are closed: malformed connector fallback, unvalidated resolution notes, and duplicated proposal bodies in stored receipts. Applied identity changes invalidate retained context. The fresh-source plugin suite passes 527 tests with 77 skips. The independent closure passes 48 focused tests. These results do not enable ownership or establish the full release gate.

## Owner proposal preferences

The preferences page shows pending text, its target, rationale, writer, and exact revision. The authenticated owner can accept, reject, edit, or mark a change as applied elsewhere. It cannot grant automatic approval. A conflict preserves the visible proposal. A failed list refresh preserves the reported committed outcome. Preferences, real FastAPI, and dashboard SDK checks pass 18 cases, and independent local HTTP and interface probes found no material issue. A full browser runtime check remains part of the release gate.


## Native source adoption

The owner can preview and adopt existing native facts, learning notes, and pending proposals. Adoption preserves native files and unknown writer provenance. Unclassified notes stay private. Optional per-file project assignments determine project access. Learning notes retain historical labels. Forgotten and corrected quotes remain excluded. Preview identity includes content, timestamps, metadata, and eligibility outcomes. Changed previews return a conflict, and identical retries retain the receipt.

Independent closure passes 38 focused tests. The complete memory regression passes 145 tests without skips against fresh prepared sources. The primary agent reran the reviewer probes. These results close source adoption and its development preferences controls, but do not close all retained-source readers, restricted prompts, lifecycle, ownership installation, or the release gate.

## Retained native source readback

The governed source interface now covers learning readback, startup relationship and work context, and advisory findings. Source authorization precedes body reads. The interface rejects redirects into configuration files, invalid text, removed claims, and unsupported paths. Unclassified history requires unrestricted owner recall. Accepted standalone native behavior remains available when no connector exists.

Independent review found three output paths that the first 11 tests missed. Native startup rendered a WORK filename into a forgotten title. Advisory readback bypassed the physical source check. Decoded JSON whitespace changed the claim comparison. The fixes check rendered path labels, decoded string fields, and the advisory source before reading. Both original probe scripts now pass unchanged. The primary agent reran them against freshly prepared distributed sources.

The closure review passes 14 tests without skips and finds no further material defect in these bounded paths. The complete plugin run executes 561 tests: 484 pass and 77 skip. There are no failures or errors. The earlier 547-test run had one fixture error because prepared Hermes test additions were untracked during patch regeneration. Marking those existing fixture files for inclusion in Git diffs resolves the error without changing their contents.

Evidence is in `docs/verification/2026-09-30-memory-retained-sources/`. Review closure is in `docs/agents/2026-09-30-memory-retained-sources/closure/`. These results do not enable ownership. Restricted prompts, complete host and source coverage, lifecycle, browser behavior, ownership transactions, and the full release gate remain open. Separate path attestation and reading do not protect against a hostile process with the same operating-system identity replacing files between those operations.

## Rendered prompts and generated model inputs

Memory admission now binds the installed SOUL contents to the conversation. A changed prompt invalidates retained admission. A prompt that contains an excluded exact claim cannot start a fresh admitted conversation. Model-request checks inspect the effective body after supported SDK overrides. Materialized tuple inputs work, while lazy inputs that cannot be inspected are refused without consumption.

Trusted compression inputs receive a separate generated-content check. It covers string Responses input, structured tool outputs, function arguments, and decoded JSON values. Ordinary primary user quotes keep their exception. The actual host compressor refuses the excluded input and returns no summary. Automatic history rebuilding remains open.

Three independent reviews found and closed request representation gaps. The final review passes 52 focused tests and finds no further material issue in this bounded unit. Its unchanged SDK and compression probes send zero requests for excluded claims. The complete plugin regression executes 582 tests: 505 pass and 77 skip. One additional nesting and lazy-input test was added after that run collected its cases. It passes in the subsequent focused closure suite.

The managed startup hook now uses source authorization for remote conversations. Two independently configured synthetic apps receive approved relationship context. Missing context, unknown authors, restricted grants, and broken connectors expose no retained markers. Unmanaged remote startup retains native isolation. These results do not establish restricted static-prompt filtering or final delivery.

Evidence is in `docs/verification/2026-09-30-memory-rendered-prompts/`. The final report is `docs/agents/2026-09-30-memory-rendered-prompts/third-closure/memory-generated-input-closure.md`. Complete agent invocation, compression rotation, the full route inventory, ownership transactions, browser behavior, and release gates remain open. Ownership is still disabled on running installations.

## Built-in ownership configuration characterization

The real Hermes constructor confirms that provider selection alone preserves both built-in stores. The ownership transaction must select `lifeos-hook-bridge` and explicitly disable `memory.memory_enabled` and `memory.user_profile_enabled`. Four tests verify prompt exclusion, failed writes through direct and freshly loaded built-in tools, exact file preservation, skill-tool availability, unavailable-provider behavior, and restoration in fresh processes.

These tests establish the required target configuration without a new host patch. They do not implement the ownership transaction or prove a live session switch, automatic skill learning, or every file mutation path. Filesystem access by the same operating-system identity remains possible. The earlier 582-test full run predates this four-test addition. Ownership activation stays disabled.

## Complete explicit agent turn

A real Hermes `AIAgent.run_conversation` turn now verifies explicit native persistence and receipt propagation. The local model endpoint requests a remember tool call and returns the actual tool receipt on its second response. The saved native record contains the authenticated writer, project, category, and exact content. Neither disabled built-in memory marker reaches either HTTP request. An unknown author stops before any model call or native save.

Independent review passes 16 relevant tests and finds no material issue. This includes the two complete turns, four ownership cases, and ten SDK cases because their shared endpoint fixture changed. The primary agent reruns the native-writer probe. These results do not close native automatic recall, all agent and route contexts, background review, compression rotation, history repair, delivery, or activation. The model endpoint is deterministic, so no real-model reasoning result is claimed.

Evidence is in `docs/verification/2026-09-30-memory-agent-turn/`. The report is `docs/agents/2026-09-30-memory-agent-turn/memory-agent-turn-review.md`. The earlier full regression predates these two complete-turn tests. No running server or memory ownership configuration changes.

## Corrections and forgetting inside an owner turn

Required plugin execution middleware now projects retained chat content before final admission. A fact-only generation change can refresh that admission. Identity, policy, destination, route, and installed prompt checks remain required. The projection preserves transcripts and tool identifiers. It removes exact excluded content from generated messages and decoded tool results while preserving the native mutation receipt.

Six complete agent cases pass, including real LoadMemory recall through the governed native connector. The owner receives the actual committed correction or forget receipt in the final model response. The next model request excludes the earlier retrieved fact and appended hook recall. Admission stores only a hash, kind, and length of the original user input. It does not create another transcript store.

Independent review exposed and drove fixes for concurrent registry publication, the current-user native recall exemption, and auxiliary original-input handling. Both primary and independent final closures pass 71 cases without skips. The final review finds no further material defect in this bounded unit. The primary reruns the archived reproductions and accepted controls. Auxiliary Responses string input and encoded instruction content now receive exact-claim checks. These changes add no Hermes or LifeOS patch files.

Evidence is in `docs/verification/2026-09-30-memory-history-repair/`. Resume repair, changed installed prompt reconstruction, full compression rotation, Responses repair, restricted prompt delivery, complete source coverage, the ownership transaction, and the release gate remain open. The current complete-turn evidence uses a scripted local model endpoint. Ownership activation remains disabled on running installations.


## Conversation repair full regression

The complete plugin suite executes 612 tests against the fresh prepared sources: 535 pass and 77 skip. There are no failures or errors. The fixture-dependent skips remain release requirements. The log is `docs/verification/2026-09-30-memory-history-repair/full-regression.txt`. This run predates the background skill review work. Ownership activation remains disabled.


## Hermes skill review and ordinary foreground continuation

The real background review fork now uses generated-content checks. It cannot borrow the primary human-quote exemption. The actual tool loop creates a Hermes skill with its default write policy, or stages the write when skill approval is enabled. Both built-in lasting-memory files remain unchanged and excluded from model input. Forgotten review focus, forgotten retained human quotes, and an unapproved review model reach no model completion request. The ordinary model metadata probe remains available.

Independent review finds a separate foreground continuation defect. The prompt-check worker records a new input proof, while the parent retains the previous proof. A no-review control reproduces the failure. Primary execution now rebinds only the worker proof when scope, fact generation, installed prompt, and context match. Actual input verification remains required. Auxiliary and direct final checks cannot use this handoff.

Both primary and independent closure pass 81 cases without skips. The unchanged archived reproduction now completes the foreground turn, real skill write, and next foreground quote with four HTTP requests. The parent origin remains `assistant_tool`. The final review finds no further material defect in this bounded unit. Evidence is `docs/verification/2026-09-30-memory-background-review/`. Review closure is `docs/agents/2026-09-30-memory-background-review/closure/`. The fix adds no host or native patch.

These results verify actual review fork execution, not every automatic cadence, idle queue, cancellation, or model judgment. Stale generated review history can still be refused; automatic rebuilding remains open. Resume, changed SOUL reconstruction, compression rotation, Responses repair, restricted prompts, delivery, ownership transactions, and the release gate remain open. No running installation changes.

The next source inventory scan records 132 candidate files and 555 reference lines in `docs/verification/2026-09-30-memory-native-inventory/`. Text references are candidates, not coverage proof. Native diagnostics and PULSE consumers require actual read and publication-path checks.


## Background review complete regression

The committed background review and continuation implementation executes 622 plugin cases against the owned prepared sources. Of these, 545 pass and 77 skip. No test fails or errors. The raw log is `docs/verification/2026-09-30-memory-background-review/full-regression.txt`. The skips require separate native, browser, SSH, Docker, or installation fixtures and remain release requirements. The source and writer audit now continues against the pinned public source. Ownership stays disabled.

## Native source audit and turn-start summary

The prioritized independent audit traces sections of 37 inventory candidates and eight additional callers or manifests. The remaining 95 candidates have no coverage conclusion. Its report records confirmed registered-summary, PULSE, diagnostic, alternate corpus, restore, staged publication, and context-builder gaps. The primary independently reruns the three native probes. Measurements preserve genuine native log and snapshot behavior and distinguish synthetic diagnostic fields, latent functions, and missing dependency failures.

The first resolution governs the registered MemoryTurnStart composer before cursor and injection side effects. Standalone delta output requires the same source authority. Exact observability and cache paths use the existing service, physical-path checks, native validation, and retirement filtering. JSONL rows receive checks before truncation. Current owner updates, health warnings, freshness, and heartbeat remain available. Fourteen new cases and the 33 neighboring cases pass against a fresh distributed source tree. The unchanged native audit probe verifies the corrected composer and preserves the other open findings. No Hermes patch changes. The native memory patch adds two hook files, for 13 files total.

The first independent delta review finds three defects beyond its 47 passing cases: per-row validation exceeds the native eight-second deadline, malformed samples suppress later updates, and filtered health rows can replay older status. The corrections select the native 500-row window before one batched validation operation, check row structure, and retain only the newest health snapshot with a safe enum projection when text is excluded. Fifty focused cases pass. The primary reruns the reviewer's unchanged volume probe: 500 rows complete in 0.603 seconds, compared with 34.440 seconds before correction. A 1,000-row regression verifies the native window under the actual deadline.

Next, govern diagnostics and direct PULSE snapshots, alternate corpus readers and derivatives, managed restore and staged publication, then the remaining capture and synthesis routes. Preserve authorized owner controls before changing a native boundary. The full audit is `docs/agents/2026-09-30-memory-native-audit/memory-native-audit.md`; delta evidence is `docs/verification/2026-09-30-memory-native-delta/`. Independent delta closure is pending. The 622-case full regression predates these 17 additional cases. Ownership remains disabled.

The following complete regression executes 639 cases: 562 pass and 77 skip, with no failures or errors. The second delta review closes the previous three findings but discovers a four-megabyte connector response limit. Summary projection then exposes a separate cursor-order defect, which the third review reproduces. The corrected response preserves full counts and up to two additions and one eviction per row. The native renderer applies the cursor before choosing global samples. Full records still receive validation and retirement checks before projection. The primary's unchanged large-history probe returns the current sample in 326 bytes, instead of exceeding the connector buffer. The unchanged managed and unmanaged follow-up probes now agree. All 53 focused cases pass; the 639-case regression predates this byte correction. Final independent delta closure is pending. The native patch still changes 13 files, and Hermes patches are unchanged.

Final independent delta closure passes 53 tests and all five archived probes, with no material issue remaining in that bounded scope. A separate managed and unmanaged control verifies addition and eviction counts, sample order after the cursor, smoke exclusions, and unrelated writers. The primary reruns that control and confirms the result. Stable hashes identify the reviewed source. This closes the five measured delta defects. It does not establish a whole-file I/O bound, safety for fabricated oversized strings, the remaining native reader and writer inventory, or activation readiness. The next implementation unit is governed diagnostic readback and trusted PULSE request scope.

## Native status and insights diagnostics

The diagnostic source interface checks exact paths and unrestricted source authority. MemoryStatus and MemoryInsights preserve operational fields and full requested windows. Forgotten or superseded proposal samples remain excluded. Unknown callers, changed audiences, restricted scopes, invalid connectors, and redirected files receive an explicit unavailable result. Standalone LifeOS retains native behavior.

The initial independent review passes 69 cases but finds three defects: valid large proposals lose their samples, escaped responses exceed the connector buffer, and extreme numeric values raise an exception. Four regression cases reproduce these defects and verify full-record retirement checks before sampling. The correction validates fields separately, preserves the native UTF-16 display prefix, measures the serialized response, and rejects unsafe numeric values before conversion. The unchanged primary probe reduces the escaped-history response from 4,663,294 bytes to 118,724 bytes. The first closure independently passes 73 cases and closes those three defects. It also finds a smaller availability flag error for malformed edits. That correction has a separate regression and final review.

This unit adds MemoryStatus and MemoryInsights to the existing LifeOS memory patch, which now changes 15 files. It adds no Hermes patch. Evidence is `docs/verification/2026-09-30-memory-diagnostics/`. The broader 639-case regression predates this unit. CortexHealth, PULSE scope, alternate corpus readers, restore, staged publication, remaining inventory, lifecycle, ownership, and release requirements remain open. No running ownership or server configuration changes.

Final diagnostic closure independently passes 21 cases and the three archived probes, with no remaining material finding in the bounded unit. The primary reruns the corrected 21-case suite and the unchanged limits and controls probes. The earlier 73-case closure covers the unchanged neighboring paths. Failed pre-fix runs and the obsolete assertion failure remain in the evidence. Continue with governed CortexHealth evidence and trusted PULSE request binding.


## Governed Cortex health and publication

The native health collectors require unrestricted source authority and exact physical input paths. Diagnostic-only hot inspection preserves invalid-entry warnings without returning valid fact entries. Managed optional reports use a dedicated observability reports directory and cannot replace configuration or diagnostic inputs. Text filtering preserves operational clocks and enums only at declared metadata locations. Arbitrary structured error, content, and sample fields remain governed. Requests and serialized responses have explicit byte limits. Managed failures produce unavailable JSON before publication, while standalone exceptional behavior remains native.

The first primary and independent closure gates pass 105 cases. Review identifies two further metadata-path and standalone-compatibility defects; real regressions reproduce both, plus the analogous enum exception. The final primary distributed gate passes 56 cases in 41.269 seconds. Final independent closure passes 56 cases in 38.914 seconds, five archived programs, and an additional real-retirement metadata-path probe. No remaining material finding exists in that bounded scope. The primary independently reruns those probes. The preceding 53 neighboring cases remain separate, unchanged evidence.

This unit expands the existing LifeOS memory patch to 17 files and adds no Hermes patch. Commands, failures, corrected results, and final source identity are retained in `docs/verification/2026-09-30-memory-cortex-health/`. Ownership remains disabled. PULSE request identity, corpus and derived readers, restore, staged publication, remaining inventory, prompts, lifecycle, installation transactions, and release requirements remain open. The next implementation boundary is PULSE per-request identity and governed snapshots.

## Governed PULSE snapshot projection

The plugin invokes real native snapshot, state, health, and run readers under owner source authority. It checks exact physical inputs before collection. Cadence output contains only four supported numeric settings. Current hot entries receive registry verification. Their count and UTF-16 character count preserve native semantics. Historical filtering and current-entry publication share one transaction.

The initial independent review finds current corrected facts hidden and dynamic JSON keys exposing retired claims. Both original probes reproduce independently. The first closure finds state-schema inheritance and missing fixed proposal and health names. Regression tests expose these defects. Field schemas now use exact view locations. Dynamic field names receive current retirement matching; historical values retain source-age filtering. Commands and failed results remain in `docs/verification/2026-10-01-memory-pulse-http/`.

The request identity review recommends the existing authenticated Hermes dashboard boundary. Each request must resolve its verified provider/account binding against fresh private memory configuration. Ambient agent identity cannot authorize native HTTP reads. The native relay must use incoming request credentials and a fixed trusted endpoint, with no raw fallback. This work does not include graph or wiki routes. HTTP and browser acceptance, the remaining inventory, and ownership activation remain open.

Final projection closure passes 72 tests on both primary and independent runs. Seven archived probes pass on both runs. The independent review identifies no remaining material finding in that bounded scope. The primary gate takes 44.507 seconds; the independent gate takes 45.155 seconds. The existing LifeOS memory patch remains at 17 files. This projection adds no Hermes patch or running configuration change. Continue with the authenticated owner API and managed HTTP relay.

## Authenticated PULSE owner API

The protected API accepts four fixed read views. It requires an actual verified Hermes dashboard session and a fresh account-to-principal binding. MemoryPreferences checks the binding and installed root from the same private configuration load. Unknown accounts and caller-supplied query scopes receive no owner authority. Registry errors and configuration failures return sanitized unavailable results.

The first review identifies uncaught database corruption and missing cache headers on host and framework errors. Real regression tests reproduce both. Plugin-owned ASGI middleware covers the exact memory route prefix, including denied requests. Actual owned Hermes app assembly installs this middleware before startup without a host patch. It preserves unrelated headers and removes validators only from protected responses. The primary 38-case gate passes in 19.432 seconds. Actual localhost HTTP and owned-host startup checks pass. Independent closure remains recorded separately.

The tested Basic provider clears browser cookies on logout but cannot revoke a copied stateless bearer. Memory account-binding removal denies that bearer immediately on the next request. No stronger host-session revocation claim is made. The managed native HTTP relay, browser credential integration, graph and corpus boundaries, remaining native readers and writers, lifecycle, ownership transaction, and release gate remain open.

Final independent API closure passes 38 cases in 20.273 seconds, the real HTTP probe, the actual owned dashboard mount, and 40 concurrent header controls. The primary independently reruns the error, identity, header, and HTTP probes. The final review identifies no new material finding in that bounded scope. The change remains inside the plugin. Continue with managed native relay delegation to these protected routes.

## Whole-design review corrections

The fresh review closes owner authorization across all memory dashboard operations, authorization before source recovery copies, verified explicit hot publication, and fixed diagnostic schemas. Its first combined gate passes 215 tests without skips. The expanded 316-test review identifies neighboring hot mutation drift, two additional diagnostic fields, a native learning-summary regression, and missing native hot session provenance. Plugin-only corrections address all four in that order. Full curation also records the session for new facts. Existing references and provenance remain stable.

The [correction evidence](verification/2026-10-01-memory-corrections/README.md) preserves failed regressions, independent observations, passing focused gates, source identities, and activation limits. The expanded closure gate and fresh whole-design review follow these corrections. Memory ownership stays disabled. This work changes no running installation and does not close the remaining native relay, complete source inventory, lifecycle, ownership transaction, or release gates.

The next whole-design review finds aborted hot publication in learned summaries. Recovery now captures the attested native hot-write audit log with the fact publication. Delta additions require current registry/native content. Maximum distinct capacity exposes a per-entry native-read regression. One verified snapshot per category restores the eight-second registered-hook contract. The reviewer also identifies missing explicit tool session provenance; context dispatch retains trusted session metadata while sessionless clients keep an empty host session. These follow-up corrections retain the same native patch and ownership design.

Follow-up capacity timing remains marginal until actual call instrumentation identifies 96 repeated reads in the existing retrieval path. Transaction-local per-file parsed entries retain native reference checks and category grants. The unchanged 96-fact composer then takes 0.948 seconds. The final gate and independent closure use this corrected source rather than the earlier marginal revision.

Final correction closure at `0400794` passes 330 primary cases in 371.570 seconds, without skips. The independent reviewer passes 144 cases in 229.294 seconds and finds no further material defect in the reviewed implemented paths. Its unchanged 96-fact observation takes 0.979 seconds. Primary instrumentation independently confirms two retrieval hot reads and six total hot reads. The whole-design report and correction evidence preserve the failed revisions, measured root causes, controls, source identities, and remaining activation gates. Memory ownership stays disabled, and no running installation changes.

## Resumed fresh-install completion

Date: 2026-10-01. Adrian asks to document existing-user import and resume the outstanding implementation. The [deferred import plan](memory-import-plan.md) preserves the original workflow, review findings, revised plan, and acceptance requirements. It is separate from these active gates.

1. Complete the exact managed native PULSE HTTP relay and authenticated browser path. Use current Hermes owner authentication. Preserve governed response shapes, per-request authorization, no raw fallback, and no-store behavior. Verify actual network and browser requests.
2. Finish the native memory-reader inventory, including alternate and derived readers. Record every candidate's active entry point, source policy, and result. Govern supported consumers and explicitly refuse unsupported managed paths.
3. Govern managed restore and staged publication. Preserve current records, permissions, retirement state, source identities, and pending operations through interruption and retry. Do not roll back unrelated later writes.
4. Close restricted prompt, final delivery, retained-session, compression, child, scheduled, and lifecycle cases. Apply the same identity and access contract to every connected messaging adapter.
5. Implement recoverable fresh ownership setup and run the full release gate. Verify supported installation/update/backup/restore/rollback paths before enabling ownership in a disposable acceptance installation.

Work uses owned prepared sources and synthetic profiles. Working `.211` and `.213` servers remain unchanged. No live memory import, ownership activation, or deployment follows from documenting the deferred migration.

## Managed native PULSE relay

The native module delegates four exact read views to the authenticated owner endpoint. Successful responses bind the configured Hermes profile, LifeOS root, and principal. Incoming request credentials supply authentication. Internal agent flags do not grant HTTP authority. Missing connectors, invalid configuration, stopped endpoints, redirects, malformed responses, and wrong installation responses refuse without native fallback. A persistent managed marker preserves this behavior across connector loss and restart.

The [relay evidence](verification/2026-10-01-memory-pulse-relay/README.md) records failing regressions, corrected results, and source preparation. A real Chromium session uses the existing Hermes sign-in form, reads four native views across localhost ports, rejects cross-origin reads, and loses access after logout. This proves the root cookie path on localhost. It does not prove the full native UI, graph/wiki readers, Secure LAN deployment, or prefixed browser cookies. The ownership transaction must create the private relay configuration and managed marker.

Continue with the native source and derived-reader inventory, then managed restore and staged publication. Ownership remains disabled on running installations.

## Governed alternate Cortex corpus

A live synthetic probe reproduces an unbound native canonical read. The corrected reader authorizes the caller and root before collection, verifies current registered facts, and delegates canonical parsing to Cortex. Current projections exclude retained retired sections without rewriting native files. Native fixed metadata keys and type directories remain operational values. Dynamic metadata still receives retirement filtering.

All 16 focused native cases pass without skips. The [inventory evidence](verification/2026-10-01-memory-consumer-inventory/README.md) preserves failed hypotheses, controls, passing results, source identity, and limits. The canonical transport limit is 3 MiB, below the native whole-corpus maximum. Unregistered notes require adoption. This unit adds Cortex to the existing LifeOS memory patch, for 19 native files, and adds no Hermes patch group. The complete consumer inventory, derived readers, managed restore, staged publication, restricted prompts, lifecycle, ownership, and release gate remain open.

The preceding relay regression passes 351 cases in 399.814 seconds without skips, failures, or errors. Its raw output and completion marker are stored with the relay evidence. This regression predates the canonical corpus unit.

Native KnowledgeQuery now consumes the governed current-note corpus. Its native parser and filters preserve owner query output. Ten new cases reproduce and close metadata admission, forgetting, unregistered sources, retired titles, and directory traversal. The combined Knowledge-query and Cortex gate passes 26 cases without skips. This expands the existing native memory patch to 20 files. It does not close derived indexes or the complete consumer inventory.

## Managed current-fact recovery

Managed MemoryRestore now previews an exact native snapshot and applies its signature through the cooperating publication transaction. Recovery reconstructs registered current hot facts and preserves later acknowledged facts, references, revisions, and source metadata. Forgotten, superseded, and unknown snapshot entries remain excluded. Unregistered current facts require adoption review. The owner must review a fresh preview after an intervening write or source change.

Native parsing and validation retain the writer's locks, caps, guards, snapshots, and audit events. Recovery results contain counts and preserved references without quoting excluded eviction text. Genuine process-death tests check both sides of the operation commit. The [recovery evidence](verification/2026-10-01-memory-restore/README.md) records raw failures, controls, source preparation, and focused verification. The native snapshot ring remains best-effort evidence. Complete backup restoration and ownership transactions remain separate gates. This unit adds MemoryRestore to the existing native memory patch, for 21 native files, and adds no Hermes patch group.

The distributed recovery gate passes 66 cases in 148.415 seconds without skips, failures, or errors. It includes 18 recovery cases and neighboring curation, publication, and delegation controls. This focused result does not close the staged publication or complete ownership gates.

## Managed staged Knowledge publication

The owner previews a staged note or a bounded 50-note batch. Native validation and canonical parsing preserve the note bytes and exclude retired content. Publication removes the native pending-review marker, registers current body references, preserves authenticated source metadata, and publishes native derived indexes plus harvest state in the same cooperating transaction. Unclassified notes remain private. Explicit project assignment controls project recall.

The renderer consumes declared current sources. It preserves native parsers and templates without scanning unregistered or retired notes. Current registered notes remain visible. A clock regression closes arbitrary text in harvest metadata. An equal-width ID probe reproduces search/export selecting different notes under one native ID. Canonical and staged corpus checks now reject duplicate native identifiers. The [staging evidence](verification/2026-10-01-memory-staging/README.md) preserves failures, source-age controls, real process-death recovery, source identity, and limits.

## Native PULSE context and current subprocess metadata

Managed PULSE context requires current unrestricted owner recall, governed identity sources, and current native hot facts. It does not reuse the standalone process cache. It refreshes configured display names and excludes invalid or retired labels. Source redirects, unavailable connectors, missing caller context, and policy revocation refuse access. Standalone context retains its native behavior.

The native connector now passes its current environment explicitly to the Python subprocess. Real probes establish that Bun otherwise retains its initial environment after caller context changes. The [context evidence](verification/2026-10-01-memory-context/README.md) preserves both failing probes and valid native controls. The existing native memory patch changes 23 files and adds no Hermes patch group. Siri credential mapping, restricted context, final delivery, other caches, and lifecycle remain open.

## Native wiki rendering foundation

A real localhost native wiki handler returns unregistered notes and retains a forgotten note in its index and body route. The top-level PULSE Host guard does not supply a memory grant. The [wiki evidence](verification/2026-10-01-memory-wiki/README.md) records route responses and a declared native renderer.

The renderer preserves native parsing, tree, search, excerpts, note bodies, backlinks, and graph output from declared content. It does not reopen raw bodies. It clears temporary indexes after each result and rejects duplicate page identities. Nine native cases pass. Authenticated HTTP delegation and current source selection remain open. The renderer is not an admission boundary. The [reader trace](verification/2026-10-01-memory-wiki/reader-boundaries.md) records related graph, Observability, sidecar editor, derivative, and SDK paths without claiming complete inventory coverage.

This unit expands the existing native memory patch to 22 files and adds no Hermes patch group. It governs promotion and its derived index generation. Harvester collection, review, rejection, other derived readers, complete source inventory, restricted prompts, lifecycle, ownership setup, coherent backup, and the full release gate remain open. Ownership remains disabled on running installations.

The distributed staging, recovery, canonical, and Knowledge-query gate passes 65 cases in 72.749 seconds without skips, failures, or errors. The broader memory regression follows this source revision. This result does not pass the full release gate.

## Authenticated native wiki Knowledge routes

Managed wiki startup avoids raw indexing, watchers, and safety rebuilds. Its six read routes delegate incoming credentials through the fixed local Hermes dashboard endpoint. Each request checks the actual dashboard session and current installation owner binding. One cooperating transaction selects registered current Knowledge notes and invokes the declared native renderer in an isolated worker.

The native directory determines the wiki category. Frontmatter type remains part of the note content. Live correction, forget, revocation, cross-origin refusal, connector failure, missing pages, and dashboard shutdown preserve the HTTP and current-source contracts. The [distributed focused gate](verification/2026-10-01-memory-wiki-relay/README.md) passes 85 cases without skips, errors, or failures. The implementation extends two existing native patch paths and adds no Hermes patch group.

The complete retained-silo and documentation corpus still needs governed source collection. Managed editing, reindex, skills, hooks, and Arbol routes remain unavailable. Complete PULSE browser deployment, the other reader and publication boundaries, restricted delivery, lifecycle, ownership setup, and the full release gate remain open. No running installation activates memory ownership.

The complete distributed regression at `cad81ce` passes 477 memory cases and 12 neighboring Hermes provider, preparation, and patch cases without skips, errors, or failures. [Additional native probes](verification/2026-10-01-memory-wiki-relay/other-reader-boundaries.md) reproduce raw Observability Knowledge reads and edits, native sidecar hot-memory edits, and forgotten identity text in the actual mount renderer. The existing prompt guard refuses that obsolete generated prompt. The main mount renderer is outside the original hooks, TOOLS, and PULSE candidate scan. Complete inventory work must include the HERMES directory and the install and update callers.
