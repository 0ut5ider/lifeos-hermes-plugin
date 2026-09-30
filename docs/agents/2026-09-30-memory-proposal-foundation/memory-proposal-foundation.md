# Native proposal foundation review

Date: 2026-09-30  
Role: Independent code and native integration reviewer  
Question: Are the implemented proposal creation, review, decision, receipt, and recovery operations correct at their permission and native publication boundaries?  
Model: GPT-6. The exact model variant is not exposed in this agent context.

## Initial-snapshot conclusion

The original nine proposal tests passed. Independent real-native probes confirmed two meaningful defects in diverted upgrade publication: distinct acknowledged proposals could overwrite one another, and a dangling state-file symlink permitted an outside-boundary write followed by blocked recovery. Both findings were reported immediately with reproduction scripts.

The primary agent then changed the native upgrade ID and publication helper and added regression tests. This report preserves the initial findings. Those changes are recorded in `raw/source-drift.json` and require the separate closure verification below; the original nine-test result is not a claim about a later snapshot.

## Finding 1: acknowledged upgrade records can overwrite one another

Severity: high, loss of acknowledged proposal content.

The reviewed native `Upgrades.addUpgrade()` built its record identifier from a timestamp with one-second resolution and a slug containing the first eight words of the claim. Distinct claims with the same eight-word prefix submitted in the same second therefore selected the same markdown destination.

The governed publication observer snapshotted that destination but did not prevent replacing it. After native publication, `memory_proposals.enqueue()` checked that the new claim appeared in the destination and acknowledged diversion. It did not establish that an earlier acknowledged claim had survived.

`raw/probe_upgrade_collision.py` submits eight distinct synthetic project-scoped proposals through the actual native implementation. No clock or native code was mocked. All eight returned `status: diverted`; only two distinct destination files remained. Retrying the first request returned its original successful receipt, but that receipt's destination no longer contained its claim.

Exact results are in `raw/upgrade-collision.jsonl`. The first observation contains every request, response, and final published file. The second shows the stale successful retry and `retry_destination_contains_original: false`.

Required correction: make distinct native claims select distinct upgrade identities, or detect a different existing claim before publication and reject without losing it. Preserve truthful retries and native diversion behavior.

## Finding 2: dangling upgrade symlink bypasses publication validation

Severity: high, write outside the declared user-data boundary and persistent recovery failure.

The initial `memory_publication.ts` checked `existsSync(path)` before calling `lstatSync(path)` to reject a symlink. `existsSync()` follows the link and returns false for a dangling link. The observer therefore registered the destination as absent. Native `writeFileSync()` then followed the dangling link and created its target.

`raw/probe_upgrade_symlink.py` creates a dangling `UPGRADES/.state.json` symlink whose target is outside synthetic USER_DATA but still inside the disposable fixture home. A diverted proposal then produces:

- A newly created outside-boundary file containing the native upgrade state JSON.
- An `unknown` receipt after Python detects that the destination leaves the boundary.
- A retained rollback journal containing that invalid destination.
- A subsequent review/recovery call failing with `MemoryUnavailable: Native memory reference leaves the user boundary`.

The outside target is synthetic. No production file or credential was used. This probe demonstrates an actual boundary write and blocked recovery, not production data disclosure.

Raw evidence is in `raw/upgrade-symlink.jsonl`. Required correction: use `lstat` to detect a directory entry even when its symlink target does not exist, reject nonregular destinations before adding them to the journal, and retain the physical parent/user-data checks.

## Other verified proposal behavior

The original nine real-native tests cover pending versus applied outcomes, diversion receipts, identical retries, explicit creation permission, private-content rejection, accept and reject decisions, separate approval permission, stale target refusal, review permission, interrupted diversion recovery, and external-client creation versus owner approval. All nine passed in 2.218 seconds.

The API probe in `raw/probe_proposal_api.py` used a real server-side configuration, service methods, and synthetic native target. Thirteen cases passed:

- Seven malformed or unsafe proposal inputs were rejected: invalid target kind, boolean confidence, nonstring edit, private rationale, invalid observed-session count, disallowed identity target, and unknown field.
- Four malformed references were rejected, including boolean and zero revisions, an extra reference field, and a nonstring ID.
- An external creator could not approve a proposal.
- A queue row altered after registration caused a conflict and did not change the target.

The approval recovery probe in `raw/probe_approval_recovery.py` forked a child and called the actual native approval helper. The child exited with status 73 immediately after native acceptance returned, before the Python receipt committed. Both the target and queue had changed, and the journal existed. The next governed review restored the exact original bytes of both files, exposed one pending proposal, and removed the journal. Retrying the same request committed acceptance once; the edit appeared exactly once in the target.

These probes exercise implemented operations only. They do not certify direct native helper interception or automatic approval, which remain open.

## Code review observations

Proposal metadata uses schema version 3 and stores references, target and row digests, revision, state, and provenance. Native queue and upgrade files hold proposal bodies. Older metadata schemas are refused; this review does not promise migration for the development-only schema.

Creation, review, and approval are separate permissions. The implementation additionally requires all native read categories and wildcard project access for these currently unpartitioned proposal operations. External client configuration permits creation and review, and refuses approval. The service exposes the same operations through strict top-level argument validation, then native validation checks proposal field types and text.

Approval checks the recorded pending reference and native row digest, validates the item, and compares the target's current content digest before invoking the native decision. The operation journal snapshots the queue, target, and proposal event log. Upgrade diversion dynamically adds exact native record and state destinations to the journal before each write. The two findings concern that diversion path, not unfinished automatic approval or source interception.

## Evidence and scope

Exact commands are in `raw/commands.txt`. Reviewed plugin and public native source snapshots are preserved in `raw/snapshot-*` and `raw/native-*`, with initial hashes in `raw/hashes.json`. Ending hashes record the primary agent's fixes to `memory_publication.ts`, native `Upgrades.ts`, and `test_memory_proposals.py`; other reviewed file hashes did not change.

All Python commands used `/home/outsider/.cache/lifeos-plugin-memory/memory-plugin-test-env/bin/python`. Tests used real Bun native operations and disposable synthetic fixtures. The fixture copied native TOOLS so its project registry resolved to synthetic user data. No live server, production memory, journal, or fleet host was accessed. No implementation files were edited or committed by this reviewer.

## What deserves Adrian's review

The critical boundary is native publication before receipt commit: destinations must be safe and distinct, and interrupted writes must roll back to the correct files. The initial review proved the two failures above and verified exact rollback for native approval. Ownership remains off. Raw native decision/helper interception, automatic approval, proposal UI controls, complete lifecycle/source coverage, and release activation remain explicitly outside this foundation claim.

## Closure status

The primary agent reported fixes and requested rerunning the two unchanged probes. The closure report will be saved at `closure/memory-proposal-closure.md`, with a fresh source snapshot and independent results. The initial findings above remain an accurate record of the originally reviewed source.

## Verified closure

The independent closure is complete in `closure/memory-proposal-closure.md`. Both original defect probes now pass unchanged. The closure also reran approval interruption/recovery and 13 API-boundary cases, and all 27 affected proposal, policy, service, and MCP tests passed. Closure source hashes were stable. The conclusion is limited to the reviewed proposal foundation and does not approve activation.
