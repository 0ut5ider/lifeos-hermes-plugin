# Removal coordinator review

Date: 2026-10-15

Role: Independent read-only safety reviewer.

Question: Does the exact coordinator exemption preserve unit, process, receipt, definition, drop-in, and foreign-consumer boundaries?

Model: gpt-6.1-sol, high reasoning effort.

Reviewed commit: `bb7d30072d8d78492b89b7cba85a43f4c9c217e1`, with base `aa2f089e`, on `feature/memory-portability`.

Disposition: CLEAR within the coordinator exemption scope. The 17 supplied current controls pass. Four additional actual-unit boundary probes pass. No measured actionable defect is established.

The installed complete preparer, browser workflow, authenticated detached recovery, reboot, and model-turn acceptance remain primary-agent work. This report does not certify those workflows. It preserves the separate exact runtime and link clearance from the previous reviews.

## Reviewed boundary

The coordinator selection first validates the fixed private workflow through `_job`. It requires a removal selection and an exact unit name derived from that workflow identifier and the launched eight-character suffix. A missing launch receipt returns no exemption.

The running unit must have the current process as MainPID, use the current unified cgroup, identify itself as transient, and expose the fixed transient fragment path. Its cgroup must end with the exact admitted unit name. The fragment requires a regular protected owner artifact and receives a content fingerprint.

The caller adds only this verified coordinator's fragment and trusted drop-ins to the known definition set. It adds only that coordinator group to the admitted process groups. Generic cached execution parsing omits only the exact verified coordinator name. The definition inventory still encounters its files and the caller verifies the full coordinator binding again after both consumer scans.

The exemption does not apply to arbitrary transient services, another workflow identifier, a forged unit receipt, or another process in the same group.

## Caller and authorization assessment

Both prepare-time consumer checks pass the exact current workflow. The pre-selection apply-time consumer check also passes that workflow. Direct consumer checks without a workflow retain their old admission behavior.

The manager's existing worker path validates the owner transition grant and request binding before invoking removal preparation or application. The coordinator helper does not create another owner authority path. It narrows a consumer-inventory exception inside that already admitted workflow.

The fixed workflow request and launch receipt remain private profile artifacts. The unit-name grammar excludes caller-selected unit names and command arguments. The exact MainPID and cgroup checks prevent another process from borrowing the coordinator label.

The current manager controls continue to reject another owner and another workflow, retain owner recovery after active configuration deletion, and keep preparation separate from application. The reviewed change does not alter the exact stock runtime selection or its executable link coverage.

## Definition and drop-in assessment

The fragment fingerprint refuses unsupported file types and shared writes. Its physical parent boundary rejects a symlinked fragment directory, and a fragment symlink does not qualify as a regular program artifact.

Drop-in reads require a trusted root or current-account owner, a regular file, no shared write permission, and a bounded size. They compare file identity before and after the read. Their retained coordinator binding includes both metadata and SHA-256. Drop-in contents must not select the reviewed profile, native programs, or Bun command.

The second coordinator inspection compares resolved physical drop-in paths as well as file metadata and content. This detects a later symlink retarget even when its replacement contents match. The fragment's content fingerprint detects later bytes even when the original timestamp returns.

A standard root-owned non-consuming drop-in remains supported. The caller does not need to exempt every service that uses the same global drop-in. The generic known-definition shortcut still requires that service to have its own known fragment, which prevents an empty-fragment service from borrowing only a shared drop-in.

## Measured controls

The supplied suite passes 17 tests. It uses real user units and establishes:

- The exact running detached coordinator is admitted.
- A foreign profile consumer remains refused.
- A forged coordinator receipt remains refused.
- A later drop-in content change remains refused when the timestamp returns to its original value.
- Existing foreign Bun, native-program, and hook consumers remain refused.
- Existing provider-return, software-plan, and retained-owner workflow checks remain green.

The reviewer adds four probes in `coordinator_probes.py`. Every probe starts its own actual detached transient unit under the existing serialized service fixture.

1. **Missing launch receipt:** The worker removes its synthetic launch receipt before inspection. It receives no coordinator exemption and the consumer inspection refuses it. For this inline Python command, refusal occurs in the generic cached-property parser because its execution text has literal newlines. This is a safe refusal, not a claim that this unsupported input receives a dedicated diagnostic.
2. **Later fragment content:** The probe changes the actual owned transient fragment after the first coordinator inspection and restores the original timestamp. The final binding comparison refuses the changed coordinator.
3. **Later drop-in symlink target:** The probe replaces its owned drop-in with a link to another private file after the first inspection. The second resolved-path binding differs, and the caller refuses it.
4. **Child identity:** A real forked child in the same coordinator cgroup performs the check while the parent remains MainPID. The child cannot claim the parent's coordinator exemption.

The three identity-change probes receive the intended specific coordinator refusal. All four confirm their fault actually occurs, rather than passing because setup did not reach the boundary.

The safe receipts are `no_receipt.json`, `fragment_bytes.json`, `dropin_symlink.json`, and `child_pid.json`. They contain admission outcomes and synthetic diagnostic text. They contain no credentials or personal records.

## Tests and raw evidence

`review-removal-coordinator-current` passes 17 tests in 36.184 test seconds, with runner wall time 36.340 seconds. `review-removal-coordinator-boundaries` passes four tests in 5.739 test seconds, with runner wall time 5.883 seconds.

Both runner commands, stdout, stderr, receipts, and completion markers remain in this directory. No tests fail or skip. Expected refusals are caught and asserted by the tests. All service mutations use the existing `service_manager_fixture` lock. Fixtures remove their owned drop-ins and units during cleanup, and detached coordinator units use collection after exit.

`source-hashes.json` records 13 exact source and test hashes from the reviewed commit. `source/` retains their corresponding bytes. Later documentation-only checkpoint changes do not alter the captured reviewed product files.

The reviewer changes no product files, makes no commits, stages nothing, and pushes nothing. The review accesses no remote hosts, personal records, memory tools, or journal tools. Every changed definition, receipt, profile, and process belongs to an isolated synthetic fixture.
