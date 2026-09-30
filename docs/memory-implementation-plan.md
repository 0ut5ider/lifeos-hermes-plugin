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

1. Complete retained learning sources, adoption, and owner preferences controls. Native direct proposal decisions, automatic approval, edit and applied-elsewhere outcomes, pending creation, diversion, and target revision checks are implemented.
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
