# Hermes memory import review

Date: 2026-10-01

Agent role: Independent design reviewer, Cerebo

Question: What meaningful omissions must the proposed Hermes-to-LifeOS import workflow resolve before implementation and ownership activation?

Model: GPT-6.1-Sol (`gpt-6.1-sol`), high reasoning effort. The delegating agent supplies the runtime identity.

Reviewed repository: `feature/lifeos-memory`, HEAD `d8b4ae5e399437bf5fe2a203e5065190c06eef7f`.

Adrian, the proposal has the correct ownership direction, but it does not yet define a safe import and handoff contract. The main omissions concern the source being edited during publication, changes to target permissions after preview, partial imports, destinations that current governed writes cannot express, and restoration of facts subsequently corrected or forgotten. These are requirements for proposed behavior. This review does not identify an implemented Hermes importer or ownership switch transaction, because neither exists here.

The existing native adoption operation must remain distinct. It registers native files in place, records unknown writers, and preserves their bytes. It does not import `MEMORY.md` or `USER.md`, select individual accepted entries, copy source provenance, or change Hermes configuration. See [memory_adoption.py](../../../lifeos_hook_bridge/memory_adoption.py:169) and [the adoption note](../../../notes/2026-09-30-memory-adoption.md:9).

## Scope and evidence limits

I inspected the approved design, implementation plan, ownership evidence, plugin code, and the owned prepared Hermes and LifeOS sources. I loaded the coding-rules skill before code inspection. I made no source changes, configuration changes, dependency installations, commits, pushes, model requests, memory calls, journal calls, or live-server calls. I ran no test suite and no behavioral experiment. The observations below are source contracts and design deductions, not new runtime guarantees.

The prepared source roots were:

- `/home/outsider/.cache/lifeos-plugin-memory/source-gate-20261001-cortex-final/hermes`
- `/home/outsider/.cache/lifeos-plugin-memory/source-gate-20261001-cortex-final/lifeos/LifeOS/install`

Numbered source copies, hashes, commands, command output, and unsuccessful path lookups are retained in [raw/](raw/). I did not use `.211`, `.213`, or imported `.212` host source.

Whole-install activation remains disabled. The implementation plan explicitly retains native relay, reader inventory, lifecycle, ownership transaction, and release requirements. The preferences API returns `activation_ready: false`; [memory_preferences.py](../../../lifeos_hook_bridge/memory_preferences.py:39) is direct evidence. This import work must not bypass those gates.

## Corrective recommendations in dependency order

The order below follows dependencies, verifiability, subtle failure risk, and blast radius. It does not rank by coding effort.

### 1. Bind the source installation and define lossless discovery

**Gap:** “Profile-scoped files” and “individual entries” need concrete identities and parsing behavior. The source is the exact selected Hermes home, its effective configuration, and `memories/MEMORY.md` plus `memories/USER.md`. A profile display name is insufficient. Bind this source to the authenticated owner, installed LifeOS root, principal, and selected provider state. Multiple Hermes profiles can point to the same LifeOS root; separate profile configuration files alone do not establish separate fact stores.

Hermes resolves memory paths per call through `get_hermes_home()` rather than a process-global path, and the provider checks its profile at initialization. See prepared `hermes/tools/memory_tool.py:38-40` and [memory_provider.py](../../../lifeos_hook_bridge/memory_provider.py:17). Capture the actual selected profile before any file read and retain it throughout the operation. Resolve custom homes explicitly. Reject a substituted profile, changed root, or changed principal.

Hermes entries use the complete `\n§\n` delimiter. The host parser strips a UTF-8 BOM and outer whitespace, preserves a bare `§`, and can return an empty list after a read or decoding failure. See prepared `hermes/tools/memory_tool_store.py:23,491-518`. Do not use that failure-tolerant result to decide that an established installation has no memory. Read exact bytes with an explicit success/error result, then parse the supported format. Preserve the byte snapshot before normalization. Detect missing files separately from unreadable files, directories, unsupported links, and malformed text.

For a multiline chunk with several claims, the preview must allow a reviewed split or whole-chunk exclusion. A deterministic parser must account for every source range. It cannot pretend that Markdown bullets necessarily correspond to independently stored Hermes entries. Give each candidate a stable source occurrence identifier, including file digest and source span, so identical chunks remain individually accounted for.

Declare the first supported scope. Import these two built-in stores for one selected profile. If another external provider is configured, show that provider and explain what selecting LifeOS stops. Do not imply that its database, model-side memory, or callbacks are migrated. An unsupported provider handoff must stay blocked or require a separate, explicit path.

**Minimal contract:** Missing files can be empty. Failed reads cannot be empty. Preview and import use the same immutable byte snapshot and profile identity. No automatic discovery of neighboring profiles or transcript archives.

### 2. Define available destinations, sensitivity, and import provenance

**Gap:** The proposed labels do not all map to existing governed operations. The supported policy categories are `project`, `principal`, and `assistant`; there is no `learning` write category. Governed `native_add` supports memory, knowledge, idea, and proposal items. Native adoption can recognize existing learning files, but that is not a governed importer for newly created learning notes. See [memory_policy.py](../../../lifeos_hook_bridge/memory_policy.py:12), [memory_access.py](../../../lifeos_hook_bridge/memory_access.py:507), and [memory_adoption.py](../../../lifeos_hook_bridge/memory_adoption.py:93).

Specify which real native operation creates a migrated lesson. Either add and verify the smallest necessary governed learning publication primitive, or obtain an explicit destination decision in the preview. Do not silently label project knowledge as native learning. The labels have observable retrieval consequences: current learning references return historical status and use `noteClass: learning`; [memory_access.py](../../../lifeos_hook_bridge/memory_access.py:618).

“Archive appropriate facts” also needs an access contract for detailed personal material. `remember(category='project')` requires a nonempty project. Unassigned native archive records are restricted to the unrestricted owner, but ordinary `remember` cannot create them that way. A named project is visible to its granted readers, including wildcard readers. Archive overflow from principal memory must not acquire project visibility just because the hot file is full. See [memory_access.py](../../../lifeos_hook_bridge/memory_access.py:165) and [memory_access.py](../../../lifeos_hook_bridge/memory_access.py:568). Missing private archive routing is a missing primitive or a visible pending item, not permission to improvise a public project.

Keep import actor and original author separate. The authenticated owner authorizes the import; that does not prove that the owner authored the old text. Record source profile, source file, snapshot digest, source span, original date if actually evidenced, unknown original date otherwise, authorship uncertainty, import date, transformation approval, and resulting native reference. The existing registry's `path` identifies the target native file, and its source fields only store kind/session. It cannot currently retain all these links. See [memory_access.py](../../../lifeos_hook_bridge/memory_access.py:88) and [memory_access.py](../../../lifeos_hook_bridge/memory_access.py:271).

Store this linkage as import metadata. Native files remain the authoritative accepted fact content. The source backup and temporary review snapshot are retained historical copies with an explicit retention purpose; they must not become a second editable fact database. For exact duplicates, attach import-source linkage without changing the existing fact's original writer, revision, or date merely to record the import.

**Minimal contract:** Every accepted item names an implemented native destination, its access scope, its known/unknown source provenance, and any reviewed transformation. Credentials and obviously sensitive configuration values remain excluded from active fact import. Backup privacy does not authorize model processing or publication of their contents.

### 3. Bind approval to target state and permissions, as well as source contents

**Gap:** Source hashes alone do not preserve the meaning of an approval. A LifeOS fact can change, a conflicting fact can appear, a project grant can widen, the owner account can be revoked, or a proposal target can change between preview and publication.

Native adoption already binds candidate records, pending proposals, target files, and their modification times in its signature; it rechecks inside the memory transaction. Its signature does not include Hermes source configuration or the full sharing/destination policy. See [memory_adoption.py](../../../lifeos_hook_bridge/memory_adoption.py:155). Current owner preferences load configuration before the memory operation, and the native operation uses its own lock. A new import cannot assume that these independent locks make its approval atomic with policy changes. See [memory_preferences.py](../../../lifeos_hook_bridge/memory_preferences.py:83), [memory_service.py](../../../lifeos_hook_bridge/memory_service.py:150), and [memory_access.py](../../../lifeos_hook_bridge/memory_access.py:113).

Bind the reviewed manifest to source identity, target root/principal, relevant current references and revisions, hot snapshots, effective Hermes memory settings, and effective LifeOS access policy. Revalidate the relevant state before each publication and before final cutover. Invalidation should show which items or permissions changed. Do not hold database locks while the owner reads the preview. Use a consistent lock order for the short apply window and recheck authorization under that order.

The promised access preview must include existing MCP clients and Hermes destinations, not only newly created connections. Adding an item to an already shared category or project immediately makes it eligible for existing readers. The current permission predicate operates on category/project/path, not an import-specific unpublished flag. See [memory_service.py](../../../lifeos_hook_bridge/memory_service.py:253) and [memory_access.py](../../../lifeos_hook_bridge/memory_access.py:165). Show this before the first accepted write. If privacy requires no external exposure until complete publication, the present primitives do not supply that staging guarantee; block applicable readers during the bounded apply window or implement the specific publication barrier.

**Minimal contract:** “No new grants” is weaker than “no new exposure.” Approval covers the actual existing readers. Permission changes require renewed review before publication. Do not promise per-record isolation the current category/project policy cannot provide.

### 4. Close the source-writing and session window during handoff

**Gap:** “Changed sources invalidate preview” needs an end point. A final source hash checked before the first write does not detect a Hermes edit during a multi-item import. An edit after the last check but before disabling the old store can be lost from LifeOS recall even though the original file survives.

Hermes mutations use separate `.lock` files and reread under lock. LifeOS uses its own lock and journal; it does not acquire the Hermes locks. See prepared `hermes/tools/memory_tool_store.py:166-207,245-274` and [memory_transaction.py](../../../lifeos_hook_bridge/memory_transaction.py:40). Before apply, stop or drain the selected profile's foreground, scheduled, child, and review writers. Acquire the supported source locks in a fixed order, reread the exact source snapshot, and retain the barrier through handoff. If this cannot be done for a running profile, require the profile to be stopped. Do not claim that an advisory lock blocks arbitrary direct filesystem editors; check physical file identity and contents at the commit boundary and disclose that direct same-user edits remain outside interface enforcement.

Two flags are necessary for supported constructor prompt/tool behavior, but they do not establish that all preserved-file surfaces become read-only. A concrete host limitation exists in the prepared source: `agent/learning_graph.py:148-172` reads the preserved files without consulting the flags, and `agent/learning_mutations.py:116` calls `MemoryStore._mutate` directly. `_mutate` at `tools/memory_tool_store.py:245-274` has no enabled-flag check. This source path can therefore bypass the usual tool availability check. I did not execute its HTTP caller, so this is a static host surface limitation, not a measured browser exploit or an importer defect.

Audit these supported old-file controls as part of the migration gate. The user should see them as historical preserved files with editing disabled, or edits must be explicitly labeled as edits to inactive memory. Do not claim that the old store has ceased being editable solely from the two configuration flags.

Existing agents hold frozen snapshots, and the host can reuse an existing external memory manager across turns. See prepared `hermes/tools/memory_tool_store.py:133-164` and `hermes/agent/agent_init.py:1345-1351`. The safe initial migration contract can require rebuilding selected-profile agents and draining pending provider work. A restart alone does not erase memory text embedded in conversation or compression history. Fresh current context and resumed historical context need the already required lifecycle admission checks. Preserve conversation records, while preventing removed or private old claims from being treated as current authoritative memory.

**Minimal contract:** Source memory has one bounded last-write point. No old admitted session can write or inject a frozen source snapshot after cutover. The operation identifies which processes must restart before memory is considered active.

### 5. Define per-item outcomes and the exact activation barrier

**Gap:** “Verify accepted writes before switching” does not say what happens when the fourth write fails after three commits, when a save is pending review, or when all records save but native hook retrieval fails. A generic batch success flag would conceal the distinction.

Current recovery and retry guarantees are per governed operation. The operations table keys receipts by writer/request ID and payload digest. The journal recovers its selected cooperating native publications. It does not encompass a Hermes source backup, two configuration files, provider callbacks, or a whole import batch. See [memory_access.py](../../../lifeos_hook_bridge/memory_access.py:289) and [memory_transaction.py](../../../lifeos_hook_bridge/memory_transaction.py:74).

Use one private migration manifest with stable item identifiers, accepted decisions, derived per-item request IDs, native references, receipts, and a separate ownership state. Suggested states are preview, approved, applying, applied, verified, switched, restart-required, complete, and blocked. These are operation metadata, not a second fact store. The aggregate result must show every source item as committed, existing duplicate, pending review, excluded by choice, rejected, conflict, or unknown.

Retries reuse the same item key and payload. Editing an item after approval creates a new approval and request key. An unknown receipt requires recovery before new writes or activation. A committed reference that was later corrected or forgotten must not be recreated merely because the manifest is retried; revalidate its current state and ask for a new explicit decision if reactivation is intended. The current per-operation retry returns the old receipt, which is useful evidence of the previous operation but is not proof that the saved fact is still current.

Switch only when all items designated as required for this handoff have committed or verified duplicate outcomes, every pending/excluded item is explicitly acknowledged, no unknown outcome remains, and actual supported provider tools and native recall work in the candidate configuration. If an accepted rule still waits for review, it is not a committed required import. A preferences status call that performs native ranking on an empty corpus is not a read/write/recall proof; [memory_preferences.py](../../../lifeos_hook_bridge/memory_preferences.py:55).

Use reference readback for each accepted write or duplicate. Verify representative native hook retrieval and actual model input in a disposable candidate configuration, including permitted and denied access. Search rank alone cannot prove that every accepted item is retrievable; result limits and relevance can omit valid records.

On failure, preserve already committed LifeOS items and report them. Leave prior ownership configuration active unless the ownership transaction already crossed its declared commit point. Do not silently delete successful imports or roll back unrelated concurrent LifeOS facts. Resuming and cancelling are explicit operations with explicit retained results.

**Minimal contract:** Per-item recovery can succeed while ownership remains unchanged. “Import complete” and “LifeOS owns memory” are distinct, verifiable states.

### 6. Preview real capacity and every eviction or transformation

**Gap:** Advising against filling hot memory is not a capacity plan. Each hot category has a 48-entry cap and a 256 UTF-16-unit content constraint in the native writer. Governed publication rejects incomplete or altered snapshots. See prepared `lifeos/LifeOS/install/LIFEOS/TOOLS/MemoryWriter.ts:68-69,221-225,558-564` and [memory_access.py](../../../lifeos_hook_bridge/memory_access.py:440).

Calculate the resulting hot snapshot against existing entries, source-internal duplicates, target duplicates, and actual native validation. Display before/after counts, overflow, every proposed eviction, and full reviewed replacement text. Do not automatically evict a preexisting LifeOS rule to make an imported rule fit. Native curation marks omitted records superseded; capacity trimming is therefore a real semantic operation, not a presentation detail. See [memory_access.py](../../../lifeos_hook_bridge/memory_access.py:449).

Apply capacity tests to the serialized submitted representation. The native `op:set` validator also bounds full entry strings, so a promise about “256 characters” should use actual native validation rather than an independently guessed character count. Unicode, prefixes, multiline chunks, and existing at-cap files belong in acceptance tests.

If a valid source chunk cannot be stored losslessly at the proposed destination, show a reviewed split, alternate permitted archive destination, pending item, or explicit exclusion. Do not silently summarize it or describe an unreviewed summary as the imported original. Recheck capacity if the target changed after preview.

**Minimal contract:** No dropped bytes, items, or existing records can be hidden behind a successful aggregate result. The exact destination and transformation are approved.

### 7. Treat old content as untrusted throughout preview and optional processing

**Gap:** Keeping model classification optional does not itself prevent source text from acquiring instructions or sending data to a model before the user makes a disclosure choice. Hermes scans loaded entries for threat patterns and substitutes a blocked placeholder in its system prompt while preserving original bytes. See prepared `hermes/tools/memory_tool_store.py:26-29,133-147`. LifeOS native item validation verifies allowed fields, size, control characters, frontmatter/comments, and sanitization; it does not prove the semantic truth or authority of a rule. See prepared `lifeos/LifeOS/install/LIFEOS/TOOLS/MemorySystem.ts:679-725`.

The importer must preview original data, including entries Hermes would block, and visibly quarantine unsafe entries instead of importing the blocked placeholder or blindly trusting the raw original. Source text cannot change destinations, project grants, tool calls, account bindings, model routes, file paths, or the import manifest. Owner confirmation of a working rule must be a specific reviewed decision, not a classifier's inference from confident wording.

Keep deterministic local preview usable without a model. Before optional classification, show the exact selected source content, model route, and what is disclosed. Send only selected content under the approved processing context. Use a tool-free bounded classification call whose structured result is untrusted advice. Route fallback needs a new decision if it changes disclosure. Do not upload all excluded entries, configuration backups, or transcript history merely because classification is enabled.

Preview rendering and downloads must treat source Markdown and metadata as text. Escape HTML, links, path strings, and error strings. Bound file/input/output bytes and candidate counts with explicit errors or explicit pagination. A limit must not silently truncate the import. Keep source excerpts out of logs, telemetry, Git artifacts, and public error responses. Protect durable backups and manifests with owner-only permissions, and show their location and retention policy.

**Minimal contract:** Imported source never executes as a command or instruction. Approved destination rules remain explicit owner decisions. No model call is required to review, exclude, or import a deterministic valid item.

### 8. Limit duplicate and contradiction promises, and preserve retirement decisions

**Gap:** “Detect contradictions” sounds stronger than current primitives can establish. Existing duplicate detection verifies exact target content within category/project and permitted entity visibility; it does not perform semantic contradiction detection. See [memory_access.py](../../../lifeos_hook_bridge/memory_access.py:261). The workflow should guarantee exact duplicate reporting and comparison against current referenced LifeOS records. Semantic conflict suggestions can be optional assistance, labeled incomplete. Absence of a suggested conflict is not proof that the stores agree.

An import item that corrects an existing record must use its referenced revision, rather than appending a contradictory new record. Show keep-current, reviewed correction, separate historical claim, and exclude as concrete outcomes where applicable. Do not invent chronology from source file modification time or import date. A source may predate a correction even when its file was copied yesterday.

Also compare source candidates with forgotten/superseded claim metadata before approving them. Existing claim blocking and retained-quote filtering are useful starting points, but their exact normalized claim and age rules do not prove semantic equivalence across paraphrases. See [memory_access.py](../../../lifeos_hook_bridge/memory_access.py:212) and [memory_access.py](../../../lifeos_hook_bridge/memory_access.py:661). A source text that contains an old removed claim can require review even when the whole chunk's digest differs. Unknown source date and uncertain authorship must remain visible. Reactivation requires a later explicit owner request.

**Minimal contract:** Guaranteed exact checks, visibly limited semantic suggestions, revision-bound corrections, and no accidental revival of known retired content. Duplicates within the source remain accounted for in the manifest even if one native fact suffices.

### 9. Separate restoration, import cancellation, and forgetting

**Gap:** Restoring the preserved Hermes files can reactivate content that LifeOS subsequently corrected or forgot. “Rollback does not copy subsequent LifeOS facts” is true but does not explain this reverse effect.

The ownership evidence proves that a fresh process can reread preserved old files when built-in configuration is restored. It explicitly does not establish transactional rollback or live switching. See [ownership evidence](../../../notes/2026-09-30-memory-host-ownership.md:9). Therefore a byte-exact restore can intentionally restore outdated recall. Before restoring ownership, show source facts that conflict with current corrections/forget decisions where known, and explain the possible reappearance of old facts. Do not silently edit the preserved backup to hide this problem. Restore current facts through a separate reviewed import only if requested.

A rollback should restore only owned memory configuration keys with an expected-current-state check, preserving unrelated user configuration changes. Restore old file bytes only if they changed as part of the transaction, or if the user explicitly selected file restoration. The importer itself should leave source files unchanged. Never overwrite newer Hermes edits or roll back the entire LifeOS root over later records and revocations.

Define retained copies for forgetting: source files, source backups, preview artifacts, migration receipts, native audit/snapshots, and Hermes conversation history. Ordinary LifeOS forgetting does not erase those copies; the current forget receipt already lists retained categories in [memory_access.py](../../../lifeos_hook_bridge/memory_access.py:760). Import previews and background reviewers must not automatically republish them. Backup retention and erasure are separate user choices. Cancellation before any publication leaves no facts; cancellation after partial publication reports the surviving references. Restoring ownership does not undo imported facts.

**Minimal contract:** Rollback restores ownership settings, preserves subsequent data, and warns about restored stale recall. Forgetting cannot be undone by retrying an import or automatically revisiting its preserved source.

## Revised minimal workflow

1. Authenticate the owner and resolve one supported Hermes profile, its effective provider/flags, the intended LifeOS installation, and all activation prerequisites. Show a blocked state if required whole-install gates are incomplete.
2. Detect the exact two built-in source files with explicit read outcomes. Offer review/import, start without importing, or keep current setup. Explain that “start without importing” refers only to these Hermes sources; it does not erase an already populated LifeOS store. Explain any existing external provider's disposition.
3. Create owner-only byte backups and an immutable review snapshot. Bind file presence, physical identity, digest, profile, principal, target root, effective settings, and policy. Preserve absent-versus-present state and permissions needed for recovery.
4. Parse supported Hermes entries without hidden loss. Show each source chunk and any proposed splits, transformations, dates, attribution uncertainty, destination, existing readers, duplicates, known retirement matches, and suggested conflicts. Uncertain rules remain review items until the owner explicitly confirms them.
5. Run optional classification only after an explicit selection and route disclosure. Its output proposes decisions; it cannot write memory or change the manifest. Keep local manual review available.
6. Finalize one approved manifest. Account for every source item. Preflight native validation, exact destination support, resulting caps, existing evictions, target revisions, and current permissions. Record required committed items separately from acknowledged pending/excluded items.
7. Stop or drain selected-profile writers and queued provider work. Acquire cooperating source locks and revalidate the source, configuration, target state, and access policy. If anything material changed, return to review before publication. Keep the handoff barrier through configuration commit.
8. Publish with governed native operations and stable per-item request IDs. Record every receipt immediately. Recover unknown outcomes before continuing. Report partial commits without switching ownership or deleting committed items.
9. Read back each accepted reference, verify duplicates remain current, and establish actual native recall/provider behavior under the candidate configuration. Required pending items, failed reads, unknown receipts, unsupported destinations, or failed retrieval block cutover.
10. Run the recoverable ownership transaction: set the LifeOS ownership configuration, select `lifeos-hook-bridge`, and disable both Hermes built-in flags as one coordinated handoff with explicit recovery state and expected-current-configuration checks. Preserve history, compression, and skill settings. Do not expose intermediate configuration to running sessions.
11. Rebuild the selected profile's affected agents and managers. Verify actual fresh model input and resumed-session admission. Mark complete only when the supported restart and recall contract succeeds. An unavailable LifeOS provider must stay unavailable rather than silently reactivate Hermes memory.
12. Present the final ledger: current accepted references, existing duplicates, pending/excluded/rejected/conflicting items with reasons, ownership state, restart state, effective readers, and backup retention. Offer resume, restore ownership, or separately reviewed forgetting with their distinct consequences.

## Current primitives and missing primitives

| Requirement | Existing support | Missing import-specific contract or primitive |
| --- | --- | --- |
| Authenticated owner and installation binding | Preferences owner binding; private memory config; profile-bound provider initialization | Whole migration must bind the same identity/root/profile across preview and apply |
| Native fact adoption | In-place registry references, source signature, existing learning recognition, project assignments | Hermes byte parsing, item selection, transformation review, source provenance links |
| Governed writes and corrections | Native validation/publication, native references, target revision checks, hot snapshot checks | Preflight for a complete import, concrete learning/private archive publication where promised |
| Retry and interruption recovery | Writer/request payload receipts; private publication journal; cooperating writer lock | Durable aggregate manifest, recovery of configuration handoff, resume/cancel semantics |
| Duplicate handling | Verified exact category/project target duplicates | Source-internal accounting and provenance attachment for unchanged target records |
| Access control | Category/project grants, owner-only unclassified adopted sources, fresh client configuration reads | Approval-to-policy binding and any promised unpublished staging boundary |
| Forgetting and correction exclusion | Retired claim metadata, governed current retrieval, retained source filtering | Import-source linkage, stale retry suppression, restore warning and retirement-aware preview |
| Ownership configuration target | Evidence that provider plus two disabled flags preserves files in fresh processes | Coordinated recoverable transaction, process/session barrier, complete old-file UI controls |
| Operational health | Preferences status and actual native calls | Actual accepted-reference and candidate runtime verification; complete release gate |

## Acceptance tests required for this migration

These are proposed tests, not tests executed in this review. Use disposable profiles and synthetic markers. Test the real owned host and native operations rather than mocked publication.

| Order | Case | Required observation |
| --- | --- | --- |
| 1 | Default, named, and custom profile; two profiles sharing one LifeOS root; unrelated provider configured | Correct selected files/config only; target sharing shown; unsupported handoff explicit; no neighboring profile changed |
| 2 | Missing, empty, unreadable, invalid UTF-8, BOM, CRLF, bare `§`, full delimiter, duplicate and multiline chunks | Exact backup bytes retained; every chunk accounted for; failed read never treated as empty; normalization and splits visible |
| 3 | Symlink/path substitution or changed profile/root/principal between preview and apply | Import rejected before unintended reads/publication; no cross-root fact or backup written |
| 4 | Existing target duplicate and same-source duplicate | One appropriate native fact; each source occurrence recorded; existing writer/revision retained; repeated import adds no duplicate |
| 5 | Source edit, delete, creation, or change during a paused apply; active scheduled/review/dashboard writer | Source barrier prevents cooperating writes or detects drift; cutover blocked; committed subset reported |
| 6 | Target correction, competing conflict, grant widening, owner revocation, or project change after preview | Relevant approval invalidated; no unapproved overwrite or exposure; unrelated target facts preserved |
| 7 | Existing MCP and Hermes destination readers; wildcard projects; principal overflow | Access preview matches actual allowed/denied retrieval; archived personal material does not acquire unintended project visibility |
| 8 | Unsupported lesson/private archive route | Explicit pending/rejected destination result; no silent category substitution; no ownership success that pretends the item was saved |
| 9 | Hot file at 47/48 entries, multiple new entries, Unicode, long prefixes, multiline source, approved/unapproved eviction | Actual native limits enforced; preexisting entries preserved unless explicitly reviewed; no dropped content hidden by success |
| 10 | Conflicting current fact; exact, wrapped, and suggested paraphrased retired claims; unknown dates | Revision-bound decision; known retired matches blocked or explicitly reactivated; semantic limitations visible; no invented fact date |
| 11 | Instruction injection, blocked Hermes entry, script-like preview text, source text requesting a path/grant/model change | Text remains data; rendering does not execute it; no tool or grant change; original suspicious bytes remain privately reviewable |
| 12 | Classification off, classifier failure, partial output, unknown route, route fallback, excluded secret marker | Manual review works; no model request when off; only selected authorized content disclosed; model output cannot authorize publication |
| 13 | Lost response and interruption before/after each item publication, metadata receipt, backup creation, and configuration publication | Recovery resolves old outcomes; retries use identical keys; no duplicate facts/proposals; aggregate ledger and active provider are consistent |
| 14 | One accepted item rejected or pending; empty native health succeeds but actual retrieval fails | Accepted/pending/failing items distinct; cutover blocked; prior settings preserved; partial native facts reported |
| 15 | Fresh agent, existing frozen agent/manager, resumed/compressed history, child and scheduled run, former provider queued callback | No old admitted current-memory injection or writes after switch; genuine history and skills retained; private/retired context admission correct |
| 16 | Preserved learning graph/edit surfaces after both flags disabled | Supported surfaces show inactive historical state and enforce the declared editing contract; no claim inferred solely from flags |
| 17 | Retry after imported fact is corrected/forgotten; restore after later writes/grant revocation and unrelated config edit | No automatic resurrection or data rollback; original import receipt is historical; restore uses configuration checks and shows stale source consequences |
| 18 | Backups/manifests/errors/downloads and explicit forget/cancel | Private modes and no source-text telemetry; retained copies explained; cancel before publication saves nothing; cancel after publication reports retained references |
| 19 | Complete supported install compatibility/release gate | Migration acceptance remains separate; no activation until native reader, relay, lifecycle, ownership, and release gates pass |

## What deserves Adrian's review

The substantive decisions are the initial supported profile/provider scope, whether imported facts may become visible to existing grants before the full batch completes, the real native destination for lessons and detailed private material, which acknowledged omissions permit switching, and the meaning of restored stale Hermes recall. Current primitives do not establish atomic batch import, universal semantic contradiction detection, or a live provider/session handoff. The minimal safe first version can require stopped profile processes for cutover, use per-item native publication plus a durable ledger, and preserve all source files. Those limits must appear in the actual workflow and acceptance evidence.

No runtime guarantees were tested in this review. No source or configuration changed. Only this review directory was written. There is no external change to undo.
