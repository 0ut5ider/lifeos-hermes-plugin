# Memory workflow closure review

Date: 2026-10-15

Role: Independent read-only reviewer.

Question: Do the fixes close the four orchestration findings, and do the new manager workflows preserve recovery and job authority?

Model: gpt-6.1-sol, high reasoning effort.

Reviewed commit: `4a7f070b`, feature/memory-portability.

Disposition: The four previous findings are closed in the tested scope. Four additional measured findings remain in the new manager workflow paths.

## Previous findings and measured responses

| Previous objection | Current response | Independent result |
| --- | --- | --- |
| An early draining intent has no service journal. | Return admits the exact reviewed initial service state again, or cancels before any drain. | The real process-exit control passes. |
| Disabling an enabled runtime-linked Pulse unit removes its fragment link. | Preparation refuses enabled external linked units. Regular installed user unit files remain supported. | The unsupported-layout control refuses before profile or service mutation. The supplied regular-installed-unit test also passes. |
| Cancellation leaves an activation binding that prevents another review. | Preparation archives the terminal binding before admitting a replacement. | The cancelled activation retry control passes. |
| A required native reference can change after final activation admission. | Activation holds a native publication transaction through the ownership writes. Return also holds its native transaction through publication. | The actual native correction boundary control passes. |

The copied prior-finding controls pass all four tests in 18.794 seconds. The current activation, transition, fresh-agent probe, and authenticated HTTP tests pass all 11 tests in 31.144 seconds. The dashboard component suite passes all 24 tests. These results do not cover a successful installed manager workflow in the disposable guest.

## New findings

### 1. P1: Recovering a failed activation job can return another completed job's provider

Location: `optional/lifeos_release_manager/memory_workflow.py:197` through line 206, particularly the unconditional activation recovery at line 206.

The manager authorizes recovery for one workflow identifier. The activation primitive uses one profile-wide binding and setup journal. The executor does not verify that this job owns that journal before it calls `activation.recover`.

Measured sequence:

1. Prepare the first activation job through the actual child worker.
2. Apply the first activation job through the actual child worker. Native ownership becomes enabled.
3. Queue another activation job with the stale selection. Its preparation fails before it replaces the first binding.
4. Recover the second failed job with a fresh native transition grant.
5. Observe that recovery returns the first configured provider to built-in memory.

The first job still reports `configured`. The second job reports `returned`. Ownership is now false. The HMAC authorization correctly identifies the second job, but the action changes the first job's global setup. This is an operation authority error, even though both jobs have the same authenticated owner.

Evidence: `activation-cross-job-recovery.json`, `review-workflow-cross-job.stderr`, and `workflow_probes.py`, ActivationJobReview.

Required correction: Bind the profile-wide activation journal to the exact workflow that creates it. A failure before that job owns a setup must not recover an earlier setup. The job identifier must distinguish two operations that select the same import snapshot and plan.

### 2. P2: An exit between queue creation and admission permanently blocks the queue

Location: `optional/lifeos_release_manager/memory_workflow.py:107` through line 108, and the permitted-state checks at lines 120 through 130.

Queue creation publishes `queued` under the installation lock. It releases the lock before it calls `admit`. A process exit in that interval leaves an operation without a launch or admission. Queue admission treats `queued` as active. Neither recovery nor rollback admits `queued`. The dashboard also offers no action for this state.

The probe exits an actual process with code 73 after the queued status publication. Both recovery and rollback refuse with `The memory workflow state does not admit this action`. A new queue request refuses with `Complete or recover the pending memory workflow first`.

Evidence: `queued-before-admission.json`, `review-workflow-boundaries-exact.stderr`, and `workflow_probes.py`, WorkflowReview.test_exit_before_admission_is_recoverable.

Required correction: Admit cancellation or preparation retry for a queued job that has no active worker. Preserve the exact request and owner binding. Test the process-exit window before admission publication.

### 3. P2: Interrupted return preparation reports cancellation while it retains a blocking transition

Location: `optional/lifeos_release_manager/memory_workflow.py:209` through line 218, especially the fallback cancellation at line 213.

The executor creates the MemoryReturn plan, creates the profile-wide MemoryTransition plan, and then publishes `review.json`. If the worker exits after the transition plan is durable but before `review.json`, recovery sees the fallback `preparation` review. It reports `cancelled` without recovering either inner journal.

The stronger probe uses real isolated service fixtures and exits an actual child process with code 73 when `MemoryTransition.prepare_return` returns. Recovery succeeds and reports `cancelled`. The profile-wide transition remains `ready`. Another transition prepare refuses with `Complete or recover the existing provider transition first`. This blocks later return operations, including those with a new export.

A second probe covers an ordinary preparation refusal after the inner MemoryReturn plan is durable. Recovery reports cancellation while the inner plan remains `ready`. Reusing the reviewed export then refuses with `Use the existing return review or prepare a new export`.

Evidence: `outer-plan-before-job-review.json`, `review-workflow-outer-plan-crash.stderr`, `failed-return-prepare.json`, and `review-workflow-boundaries-exact.stderr`.

Required correction: Publish enough recovery binding before each inner preparation can create state. On recovery, inspect and recover the inner journals owned by this job. Do not infer that preparation made no changes solely because the final workflow review is absent. Preserve archived plans and later profile edits.

### 4. P2: A stale poll restores private prompt text after authentication refusal

Location: `optional/lifeos_release_manager/dashboard/dist/index.js:13` through line 35, particularly both successful calls to `setOperations`.

The manual refresh and periodic poll do not share a response generation. Each request can publish operations independently. An authentication refusal clears operations, but an earlier request can resolve afterward and restore its private reviewed prompt and action controls.

The component probe starts the actual component's initial poll, then starts a manual refresh. It rejects the second request with an authentication error and confirms that state is clear. It then resolves the earlier poll. The private synthetic prompt appears again.

Evidence: `private-state-ordering.json`, `private-state-probe.stdout`, and `private_state_probe.cjs`.

Required correction: Invalidate pending responses after authentication refusal or session change. Use one response generation for the polling, refresh, and action paths. The component must not accept an earlier response after it clears private state.

## Method and boundaries

The review changes no product files. The review creates only reports, source copies, and reproduction artifacts. It calls no memory or journal tools, accesses no remote host, and reads no personal data.

Python tests use the repository runner, actual private owner grants, the qualified native memory implementation, and fresh child processes. Service tests use real user-systemd units under the existing service-manager fixture lock. The two manager tests that need service admission stage a private bridge copy and change only its UNITS constant to the fixture's unique service names. They do not change workflow or transition logic. This is explicit fixture wiring, not qualification of the default installed service names.

The launch callback in manager boundary tests captures the admitted launch. Tests invoke the actual worker in a fresh child process afterward. This preserves deterministic failure boundaries and does not claim that the systemd-run transport is accepted. The browser probe is a component test with deferred SDK responses. It does not claim real browser or network acceptance.

The original 11-test baseline, 4 prior-finding controls, and 24 component tests pass. The new regression probes fail intentionally for the measured findings. The first version of the failed-return probe expected a complete successful retry despite absent default fixture services. The retained exact probe corrects this assertion and checks the inner-plan refusal directly. The outer-plan crash probe independently verifies the stronger global recovery failure with actual service fixtures.

The primary agent receives each measured finding while work continues. This report applies to the captured commit. It does not certify fixes made after this review.

## Source and raw evidence

`source-hashes.json` records SHA-256 values for all 17 captured product and test files. `source/` contains their exact `git show 4a7f070b:<path>` bytes. Raw runner receipts include each command, return code, qualified source location, and duration. Original runner output also remains in the verification directory.

Key source identities:

| File | SHA-256 |
| --- | --- |
| memory_workflow.py | 2fb4f6448a6dd676b9ab044246a2afe8de6568ad9d53241626dd44b4450d594c |
| memory_workflow_worker.py | b3da55bf73697f63448a9c108bfa7410912ddcda4f7582c337e3c171b9d56dc6 |
| manager dashboard/plugin_api.py | fa923cc348d7c95e291a370c15ef140e9b1f388b8be0f4fbb2a98b1fd01ee31e |
| manager dashboard/dist/index.js | 1f92f21ac9b9bf480a0355e2f7d60ff0062934d60ba121a4b419b8985f0dcd17 |
| memory_activation.py | fe05ad5a6ed188049768d9fd7ccf0a947c2728b0a6abb0e5d97f26e9f9c2e66e |
| memory_transition.py | 4e301e592636850e7392d2509502cae399e57fe8f35e71e48cc873b5237ac2f0 |
| memory_administration.py | da5e625f94c4a3e8619a7c2531eea4c6f6c53d3aec060b34c0d840f447fc75c1 |
| memory_transition_probe.py | 8db6698ff11e15cf8b2084631b0070788417735f1ee3d2098347586cb3938e33 |
