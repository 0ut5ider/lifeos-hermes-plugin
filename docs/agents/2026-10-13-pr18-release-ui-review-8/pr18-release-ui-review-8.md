Date: 2026-10-13
Role: Independent focused program-publication reviewer
Question: Does preserving an unchanged admitted file keep journal, restore, and refusal guarantees while preventing service metadata invalidation?
Model: gpt-6.1-sol, high reasoning effort

Reviewed head: 307753c599a665dd11f94c239cfe89aa4dc0816d
Comparison base: e5a6ccf132dbed65adfc5305f9a080dfcb28dd2d
Exact inspected source hashes: reviewed-file-identities.json

## Result

This bounded review is clear. I found no concrete defect in the two-line unchanged-file skip or its journal and recovery interaction. All 31 existing program and actual temporary-service controls pass.

The change preserves only file entries whose admitted before and after fingerprints are equal. It does not waive service metadata checks, overwrite later edits, skip validation, change the reviewed entry list, or alter directory publication.

## Publication ordering

ProgramTransaction.apply loads the recorded entries and calls check_prepared before recording applying or skipping an entry. That check compares every source, staged incoming copy, and current target with its admitted fingerprint. An unchanged entry therefore remains validated even though its file publication is unnecessary.

A file fingerprint includes its type, mode, and content digest. A changed mode or changed bytes does not satisfy the new equality condition. Such files continue through the existing publication path. Directory entries also continue through their original retain-and-publish path even when their fingerprints happen to be equal.

The skip leaves the original file's inode and modification time intact. It does not replace the file with an identical temporary file. This avoids invalidating systemd's retained definition metadata merely to publish the same admitted bytes and mode.

The per-artifact publication checkpoint is not called for a skipped file because no artifact is published. The transaction still records applied after it processes the complete entry list. The enclosing programs-published checkpoint is unchanged.

## Journal, restore, and refusal semantics

Preparation still records the unchanged entry and stages its incoming and before copies. The admitted entry digest and program journal schema are unchanged. The code does not remove an entry or alter its recorded before/after expectations.

check_applied still checks every current target and retained before copy. A later edit to the preserved file therefore fails the same applied consistency check. Source or staged-copy changes before apply also remain failures through check_prepared.

resume already skips a target that matches its admitted after fingerprint. The apply correction now preserves an already equal file on the first publication path as well. The recovery checks still refuse target states outside the admitted before/after values and still validate retained copies.

restore checks recovery before mutation and skips a target that already equals its admitted before fingerprint. For an unchanged file, before and after are equal, so it remains intact during restore. Changed entries still restore their original retained bytes. No data deletion or reset is added.

The change does not relax NeedDaemonReload, definition identity, owner permissions, service scope, child-process draining, or restart selection. Service checks still require the manager's reviewed current metadata.

## Regression coverage

The new program test uses one unchanged file and one changed file in the same real ProgramTransaction. It verifies unchanged inode and modification time after apply, publishes the changed target, runs check_applied, restores the transaction, preserves the unchanged inode, and restores the changed target's prior bytes.

The new actual service test enables an isolated synthetic dashboard unit under default.target. It drains the first-install dashboard role, applies a transaction containing the same admitted definition, then quiesces and resumes the real service. The first-install service journal returns active without accepting stale manager properties.

Enabling the fixture matters to the measured failure context. The primary's earlier linked inactive fixture did not retain the same manager state as the enabled guest dashboard. The supplied note records that distinction. I ran the current enabled-fixture regression, not a new before-fix experiment or a guest recovery test.

## Controls run

The exact command runs test_release_programs and test_profile_services. All 31 tests pass in 19.911 seconds: 16 program controls and 15 actual temporary-service controls. There are no skips, failures, or errors. The run uses -B and treats ResourceWarning as an error.

The service fixtures use temporary UUID-named user units and actual parent/child writers. Their cleanup stops and removes those test units. They do not alter production service definitions or a guest. Recorded existing service receipts are saved under services/.

Unittest writes its normal verbose output to python.stderr. python.stdout is empty. There are no unexpected diagnostics or ResourceWarning reports.

## Scope limits

This review covers ProgramTransaction.apply preserving unchanged files, its existing journal/recovery callers, and the two regressions. It does not repeat full integration or native Hermes qualification. The earlier 658/716 results are supplied context for the preceding candidate, not tests I reran here.

The final sealed package must still repeat the actual guest interruption and recovery acceptance, including preservation of the later synthetic user file. Successful current installation, update, browser behavior, and release qualification remain separate evidence gates.

I performed no additional experiments, edited no product source, changed no guest or production configuration, called no memory/journal tools, committed no change, and pushed no branch.

## Raw data

- followup.diff: exact e5a6-to-3077 source, regression, and measured-note diff.
- reviewed-file-identities.json: exact inspected head and source hashes.
- command.json: exact arguments, selected environment, outcome, and elapsed time.
- python.stdout/python.stderr: full 31-control output.
- services/: actual service-control receipts emitted by the existing tests.
