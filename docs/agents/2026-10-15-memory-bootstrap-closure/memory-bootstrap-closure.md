# Memory bootstrap closure review

Date: 2026-10-15

Role: Independent read-only reviewer.

Question: Does atomic publication of complete preparation directories close the two remaining bootstrap findings without changing operation authority?

Model: gpt-6.1-sol, high reasoning effort.

Reviewed commit: `a0a95671`, feature/memory-portability.

Disposition: CLEAR for the two bootstrap findings and the adjacent boundaries tested here. No new measured actionable issue remains in this focused review.

This is a bounded code and fixture result. It does not certify complete removal, installed end-to-end acceptance, real systemd-run transport, model-backed recall, or a release deployment.

## Previous objections and responses

| Previous objection | Current response | Independent result |
| --- | --- | --- |
| An incomplete job without status.json disables status and admission. | Queue constructs request and queued status under .lifeos-portability-preparations. It renames the complete directory into the active list. | Directory-before-request and request-before-status crashes leave inactive artifacts. Status and new admission continue. |
| Inner return copies can exist without a plan or operation document. | Return constructs an operation-owned private .return-preparing directory. It publishes all copies, the plan, and ready operation before activating the directory. | First-copy and plan-before-operation crashes no longer block recovery or export reuse. |
| The outer transition plan can exist without its operation document. | Transition constructs the complete plan and ready operation in an inactive preparation directory before rename. | The plan-before-operation crash no longer leaves a blocking active transition. |
| A partial preparation could become active after a rename boundary. | The active path receives a complete directory. The implementation syncs its parent after rename. | Three actual process-exit controls after rename and before parent sync recover correctly. |

The original tests are retained unchanged in original_write_boundaries.py. Their trace predicates name the former active write paths. Running those unchanged predicates against the new implementation would miss the intended preparation writes. The adapted_bootstrap_controls.py tests explicitly recognize both the original paths and the new inactive preparation paths. They preserve the original behavior assertions and add a directory-before-request case.

## Independent results

| Run | Executions | Result |
| --- | --- | --- |
| Adapted bootstrap controls, MemoryReturn, MemoryTransition, authenticated dashboard controls | 18 | PASS |
| Complete queue, inner return, and outer transition rename, before parent sync | 3 | PASS |
| Equivalent complete-publication controls after parent sync | 3 | PASS |
| Inactive artifact privacy, retention, and active-plan isolation | 1 | PASS |

The 18-test run completes in 43.409 seconds. The before-sync run completes in 8.806 seconds. The inactive artifact control completes in 2.714 seconds. Runner JSON receipts record complete wall time and the exact commands.

## Rename and recovery boundaries

The before-sync controls exit actual child processes with os._exit(73) when execution enters the parent-directory sync function after a successful rename. The three cases cover queue activation, inner return activation, and outer transition activation.

Each recovery uses a fresh owner-bound transition grant and the actual worker. Recovery returns cancelled. Completed inner and outer private plans move to their history directories. The same reviewed export can prepare again. The queue case lists the complete queued job and admits recovery even though preparation never starts.

The after-sync controls cover the next boundary before the preparation returns to its caller. The first run uses the code retained as post_sync_controls.py. The before-sync run uses rename_controls.py. These are separate injection boundaries, even though each run has the same three case names.

These are process-crash tests. They do not simulate power loss or prove storage hardware flush behavior. Source inspection confirms that the queue syncs both directory parents after its cross-directory rename. Inner return and outer transition sync their shared parent after activation.

## Inactive artifacts and operation authority

The inactive artifact control exits after the first inner before-image copy. The retained preparation contains the owner and operation identifier before any copies. The control verifies private permissions on the retained tree. Cancellation does not delete those artifacts.

The control then prepares the same reviewed export successfully. It changes only the retained inactive before-image. The active return plan remains byte-for-byte identical, and the active plan and copies still validate. The inactive preparation therefore remains retained evidence and cannot select the active memory files.

The adapted suite includes the cross-job return control from the prior review. A second failed return job cancels without changing the first job's exact ready plan, job state, or native ownership. Current operation_id validation remains in the source. The atomic publication changes do not remove those bindings.

The existing dashboard controls continue to refuse anonymous sessions, another account, foreign origins, client-selected paths, and invalid operation signatures. Existing return tests continue to refuse later profile edits and retain native facts during rollback.

## Method and limits

The review changes no product files, accesses no remote hosts, reads no personal records, and calls no memory or journal tools. All artifacts are synthetic fixture outputs or repository source.

Tests use qualified native LifeOS tools, actual private authorization files, actual worker code, and fresh child processes. Tests with service admission use actual user-systemd fixtures under the existing service-manager lock. A private bridge copy changes only its service mapping to unique fixture units. No service manager or memory API is replaced with a fake implementation.

The launch callback records admission, after which the test starts the actual worker in a child process. This verifies the workflow and recovery implementation but does not claim transport acceptance. Full installed default-service acceptance and complete removal remain pending.

Inactive preparation directories remain on disk by design. This review verifies safe retention and reuse. It does not introduce or qualify an automatic cleanup policy.

## Source and raw evidence

source-hashes.json records the exact five reviewed product files from commit a0a95671. source/ preserves their bytes. test-source-hashes.json records the retained original, adapted, and additional controls. Each runner label has raw stdout, stderr, a JSON receipt, and a completion marker in this directory.

| File | SHA-256 |
| --- | --- |
| memory_workflow.py | 249210796891ef5215ab3361e63b418ac8b4f11ea1043f6a0ce436f3fd7208d6 |
| memory_return.py | 6e893b1fa3a1c09b16c432fbd6caf94807c9009a9145a1d774c32f5055b02825 |
| memory_transition.py | 543e1c24269787f92e23296b2838f160858b297bd3343ba72ef3d13c03e22b77 |
| memory_activation.py | 01cf74d8cb0d12d8e0b72e2db081e338b05eff413f1c8461af5f694ffb097bfe |
| memory_workflow_worker.py | b3da55bf73697f63448a9c108bfa7410912ddcda4f7582c337e3c171b9d56dc6 |
