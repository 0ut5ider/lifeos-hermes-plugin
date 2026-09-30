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

The memory suite passes 95 tests without skips, including the real localhost SSH daemon. The complete plugin suite passes 503 tests with 77 fixture-dependent skips. This does not pass the full release gate. The first full run failed because the isolated environment omitted the plugin's declared parser dependencies. Rebuilding from the complete declared core, development, and plugin requirements resolved those 86 import errors. The bounded host suite passes 131 tests. Existing and memory dashboard interface tests pass seven cases. The actual Hermes dashboard rejects unauthenticated requests with HTTP 401 and permits an authenticated synthetic-fact lookup.

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
