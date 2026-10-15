# Memory workflow final review

Date: 2026-10-15

Role: Independent read-only reviewer.

Question: Do the operation bindings and recovery changes close the previous findings, including adjacent publication boundaries?

Model: gpt-6.1-sol, high reasoning effort.

Reviewed commit: `13ce7b1e`, feature/memory-portability.

Disposition: The previous four manager findings are closed at their measured boundaries. Two remaining P2 findings affect earlier document publication boundaries. Both have real process-exit reproductions.

## Previous objections and measured responses

| Previous objection | Current response | Independent result |
| --- | --- | --- |
| Recovery of a failed activation job rolls back another configured activation. | Activation bindings and return plans include operation_id. Preparation recovery checks exact operation ownership. | The actual child-worker control passes. The first job keeps native ownership. |
| A queued job cannot recover after an exit before admission. | Queued operations admit authenticated recovery and rollback. Previous grants are revoked. | The original queued-state process-exit control passes. |
| An interrupted return prepare retains inner and outer state after reporting cancellation. | Recovery archives only the current job's ready plans. The same reviewed export can prepare again. | Both original preparation controls pass with archive retention and actual successful re-review. |
| An earlier poll restores private prompt text after a later authentication refusal. | Poll, refresh, and action requests share a useRef sequence. Cleanup invalidates pending responses. | The original deferred-response component control passes. |

The four copied Python controls pass in 18.376 seconds. The copied private-state control and current component tests pass all 25 tests. A new positive return control also passes: cancelling a second failed return job preserves the first job's exact ready plan, active provider, and job state.

The earlier orchestration findings remain addressed by the captured source: guarded early service-drain recovery, refusal of unsupported enabled linked Pulse units, terminal activation binding archival, and native publication barriers. This round focuses on the manager changes and adjacent journal boundaries.

## Remaining findings

### 1. P2: An exit between the request and status publications disables workflow status and admission

Location: `optional/lifeos_release_manager/memory_workflow.py:104` through line 107. Status reads every job's status file at line 87.

Queue creation publishes request.json and status.json separately. A process exit after request.json is durable leaves a valid private operation directory without status.json. The status endpoint raises FileNotFoundError for that directory. Every later queue call also fails because it calls status before admitting a new job.

The new queued-state recovery permission cannot resolve this earlier state. Both status and admit require the missing status file. The dashboard cannot identify the job through its normal operation list.

The probe exits an actual child process with code 73 immediately after request.json publication. The request file exists. The status file does not exist. Status and a new queue both raise FileNotFoundError.

Evidence: `queue_request.json`, `review-final-document-boundaries.stderr`, and `write_boundaries.py`, test_queue_request_before_status_can_recover.

Required correction: Publish a complete recoverable job bootstrap atomically, or define an authenticated recovery state for incomplete bootstrap directories. A missing document must not disable the entire list. Preserve owner and request validation for any recovered job. Cover an exit after directory creation as well as after request publication.

### 2. P2: Return preparation still has unrecoverable states before its operation documents

Locations:

- `lifeos_hook_bridge/memory_return.py:102` through line 118, which creates return state, copies files, publishes plan.json, and then publishes operation.json.
- `lifeos_hook_bridge/memory_transition.py:162`, which publishes plan.json before operation.json.
- `optional/lifeos_release_manager/memory_workflow.py:193` through line 212, which depends on complete plans and operation documents for cancellation.

The operation_id binding is present in each completed plan. It does not exist early enough to recover every durable preparation state.

Three real child-process exits demonstrate the problem:

1. Exit after the first private before-image copy but before the inner return plan. Recovery reports cancelled because owns_operation sees no plan. The partial return directory remains. Re-preparation refuses with `Use the existing return review or prepare a new export`.
2. Exit after the inner return plan publication but before its operation.json. Recovery identifies ownership, then fails while loading the missing operation document. A second recovery also fails. The job remains interrupted.
3. Exit after the outer transition plan publication but before its operation.json. Recovery again fails twice. The profile-wide transition plan remains, so future return preparation cannot progress.

All exits occur before any profile configuration publication. The safe resolution can therefore cancel or archive the private preparation, but it must prove operation ownership without assuming a completed plan or operation document.

Evidence: `inner_copy.json`, `inner_plan.json`, `outer_plan.json`, `review-final-document-boundaries.stderr`, and `write_boundaries.py`.

Required correction: Make the private preparation bootstrap operation-owned and recoverable before its first copy. Publish complete preparation state atomically where practical. Recovery must retain partial artifacts and distinguish this job from an earlier job. Test exits after the first copy, after each plan, and before each operation document. A reported cancellation must leave either a reusable export or a usable bound recovery operation.

## Additional control

`test_second_return_cancellation_preserves_first_ready_transition` uses two actual manager jobs and real isolated user services. The first job reaches ready. The second job fails because the first job already owns the return preparation. Recovery cancels only the second job. The first transition plan remains byte-for-byte identical, the first job remains ready, and native ownership remains enabled.

Evidence: `cross-job-return-control.json` and `review-final-cross-return-control.stderr`. This control passes in 7.029 seconds.

## Method and limits

The review changes no product files. It creates reports, source copies, and test artifacts only. It reads no personal data, accesses no remote hosts, and calls no memory or journal tools.

The Python reproductions use the actual worker logic, actual private owner grants, qualified native memory, and fresh child processes. Process exits use os._exit(73), so normal exception cleanup cannot hide incomplete state. Every service mutation uses the existing fixture lock. Tests that require service admission stage a private bridge copy and change only the fixed service mapping to unique actual fixture units. They do not change workflow or transition logic.

The browser test is an SDK component test with controlled response ordering. It is not a browser acceptance claim. The captured source and passing controls do not qualify the systemd-run transport, an installed default service layout, actual stock runtime construction, or complete LifeOS removal. Those acceptance steps remain pending.

The four new negative tests fail intentionally for the measured publication findings. The previous controls and positive cross-job return control pass. The primary broader test run is independent and is not claimed as this review's result.

## Source and raw evidence

`source-hashes.json` identifies all 17 captured source and test files. The `source/` directory contains their exact bytes from commit 13ce7b1e. The runner receipts record commands, exit codes, durations, and qualified native and Hermes source locations. Raw stdout and stderr remain beside the report and in the verification directory.

Key SHA-256 values:

| File | SHA-256 |
| --- | --- |
| memory_workflow.py | 7036c6ce6c6a5d03e8585d73a46a0872dab4b1c1434379e0bfcb5ba457b2390f |
| memory_return.py | bc118895291276115289f5e98d0f952ccc233719c27570b77ba2fd8e02280649 |
| memory_transition.py | af038f6a39554767ca57b27921a2d9edf10bc75e6887b2eb7f57e378073d1c3d |
| memory_activation.py | 01cf74d8cb0d12d8e0b72e2db081e338b05eff413f1c8461af5f694ffb097bfe |
| manager dashboard/dist/index.js | c68ed4e923eaeb21aa93ee38ba22e5cb7875a48ab8b5b1446c5b701ec2174680 |
