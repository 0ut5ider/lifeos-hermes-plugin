# Import existing Hermes memory into LifeOS

Date: 2026-10-01. Status: deferred design work. Adrian asks to preserve the original proposal, independent findings, and revised plan before returning to fresh-install completion. This document does not activate memory ownership or implement migration.

The [approved memory design](../notes/2026-09-30-memory-design.md) gives LifeOS ownership of lasting facts. Hermes retains history, compression, and skills. Fresh installations remain the first target. Import applies separately to an established Hermes profile that already has `memories/MEMORY.md` or `memories/USER.md`.

## Original proposal

1. Detect existing built-in memory in the selected Hermes profile.
2. Offer review and import, start LifeOS without importing, or keep the current memory setup. Preserve the original files in all cases.
3. Back up source files and memory configuration privately. Bind the preview to the source contents and reject a changed preview.
4. Review each item. Propose principal preferences, assistant working rules, project facts, or learning records as destinations. Hold uncertain or outdated content for review.
5. Identify exact duplicates and show possible contradictions. Preserve source information without inventing the original author or date.
6. Keep detailed material out of capped active memory. Show pending or excluded items. Do not grant other agents access automatically.
7. Publish approved items through governed operations. Verify native persistence and retrieval before selecting LifeOS and disabling both built-in stores. Rebuild affected session context.
8. Preserve retries and recovery. Restore the previous configuration if requested, without automatically copying subsequent LifeOS facts into Hermes.

The proposal excludes automatic transcript mining and continuous synchronization of two editable stores. It treats import as optional, separate from the fresh-install default.

## Independent findings

The [import review](agents/2026-10-01-memory-import-review/memory-import-review.md) inspects the proposal against implementation `d8b4ae5`. It runs no behavioral experiment or test suite. The primary verifies its central source claims and saved source identities. Findings concern proposed contracts, not defects in an implemented importer.

| Finding | Required change to the plan |
| --- | --- |
| Source identity and lossless discovery | Bind one authenticated profile, effective provider/configuration, target root, and principal. Parse the supported Hermes format. Distinguish missing files from failed reads. Account for every source chunk. |
| Concrete destinations and provenance | Use implemented native write destinations. Learning publication and private archive routing need specific support where promised. Record original source linkage separately from the import actor and target file. |
| Target state and permissions | Bind approval to relevant target references, revisions, capacity, configuration, and permissions. Existing readers can gain access without new grants. Show that exposure before publication. |
| Source writers and old sessions | Establish a bounded last-write point through cutover. Drain writers and rebuild retained agents/managers. Cover old memory dashboard controls as well as tools. |
| Partial outcomes and activation | Keep a private import manifest with item identities, decisions, retry keys, receipts, references, and ownership state. Required pending, unknown, or failed items block the switch. |
| Capacity and transformations | Preview resulting native snapshots and every eviction or transformation. Native limits and validation determine acceptance. No silent truncation, summary, or replacement. |
| Untrusted content and optional processing | Keep source text as data. Quarantine unsafe entries. Classification is optional advice on an approved route, using only selected content. Protect backups, previews, rendering, and errors. |
| Duplicate, conflict, and retirement limits | Guarantee exact checks. Label semantic suggestions as incomplete. Bind corrections to references. Do not revive known retired content through retry or reimport. |
| Restore, cancellation, and forgetting | Distinguish these operations. Restoring old Hermes recall can revive outdated facts. Preserve later data and unrelated configuration. Explain retained source and backup copies. |

The prepared Hermes learning graph reads preserved files without checking the built-in memory flags. Its edit path calls a mutation function that also lacks that check. This static observation requires cutover acceptance coverage. It does not establish a tested browser exploit. Disabling the flags proves the tested agent prompt/tool boundary, not all old-file surfaces.

## Revised implementation plan

1. Authenticate the installation owner. Resolve one supported source profile, its provider, target LifeOS root, principal, and activation prerequisites. Do not discover or copy other profiles automatically.
2. Read the exact supported source files with explicit success/error outcomes. Offer review/import, start without importing these sources, or keep current ownership. An existing LifeOS store is never erased by the empty-import choice.
3. Create private byte backups and an immutable review snapshot. Record file presence, identity, digests, permissions, effective settings, and policy. Preserve original bytes before normalization.
4. Parse supported entries and account for every source occurrence. Show reviewed splits, transformations, uncertain dates/authorship, real destinations, existing readers, duplicates, and known retirement matches.
5. Offer optional classification only after content selection and route disclosure. Treat its structured output as advice. Keep deterministic manual review usable without a model.
6. Approve one import manifest. Preflight native validation, destination support, target revisions, capacity, evictions, and permissions. Separate required items from acknowledged pending or excluded items.
7. Stop or drain selected-profile writers and queued provider work. Acquire supported source locks in a fixed order. Revalidate source and target state under the apply barrier. Material changes return to review.
8. Publish approved items with governed operations and stable per-item request identifiers. Save receipts and resulting references. Resolve unknown outcomes before continuing. Report partial commits without changing ownership.
9. Read back every accepted or duplicate reference. Verify native recall, provider tools, and permitted/denied behavior under the candidate configuration. Required pending items or verification failures block cutover.
10. Run a recoverable ownership transaction with expected-current-configuration checks. Select LifeOS, disable both Hermes built-in flags, and record the exact commit/recovery state. Preserve history, compression, and skills.
11. Rebuild affected agents and managers. Verify fresh prompts and retained-session admission before declaring active memory. Unavailable LifeOS must not silently reactivate Hermes memory.
12. Show the final item ledger, ownership/restart state, effective readers, and backup retention. Resume, cancellation, restoration, and forgetting retain their separate effects.

The first supported handoff may require stopped profile processes. Per-item native recovery is an existing primitive; aggregate migration and configuration recovery are not. Import metadata must not become a second editable fact store.

## Acceptance and scope

## Reversible evaluation and return to Hermes

Date: 2026-10-02. Adrian requires installation and removal choices in the overall plan. A separate trial profile, import into the current profile, and activation without import are distinct choices. A dedicated fresh installation is the current acceptance target, not a permanent product restriction.

Return to preserved Hermes memory restores its selected provider and supported files after review of known correction and forget conflicts. Facts learned only in LifeOS remain in retained LifeOS data. They are not copied automatically. Return with current LifeOS knowledge requires a separately reviewed reverse migration. Validate the supported Hermes format, capacity, destination identity, transformations, and every accepted item before switching. Preserve pending or excluded material without claiming it is active Hermes memory.

An uninstall transaction drains writers, resolves unknown operations, checks current configuration, restores only owned changes, rebuilds affected agents, and verifies Hermes recall. Plugin-managed hook, prompt, guard, and program changes require verified removal. Shared program patches require an explicit scope explanation. Updated or edited code must not receive an unchecked reverse patch. Retained LifeOS data and private backups remain until the owner separately requests deletion.

Add acceptance cases for interrupted removal, restore conflicts, changed patch bases, later memory writes, profile isolation, reverse-export limits, and known retired claims in preserved Hermes memory. Implement this work after the current fresh-install foundation. Do not advertise reversible established-installation support before those cases pass.


The review defines [19 acceptance cases](agents/2026-10-01-memory-import-review/memory-import-review.md) for profiles, parsing, path substitution, duplicates, races, grants, unsupported destinations, capacity, retired claims, untrusted text, optional processing, interruptions, partial outcomes, sessions, old-file controls, restore, retained copies, and release compatibility.

Run these with disposable profiles and synthetic facts when import implementation begins. Current native adoption registers existing LifeOS files in place. It does not import Hermes memory or establish this handoff.

Existing-user migration remains deferred. The active work is the [fresh-install memory completion plan](memory-implementation-plan.md): native PULSE relay/browser authentication, remaining readers, managed restore/staged publication, restricted routes and lifecycle, then ownership setup and the full release gate.
