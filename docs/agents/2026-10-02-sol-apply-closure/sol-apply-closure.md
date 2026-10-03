# Verification of the apply interruption correction

Date: 2026-10-02

Role: Independent reviewer of the final apply interruption correction

Question: Does the journal ordering correction close the apply stop interruption gap, while retaining the verified restore and memory corrections?

Model: GPT-6.1-Sol, high reasoning effort

Reviewed revision: `eed9bdb745ac56824a4b3e2a3ba08d09e8839cfe`

Parent revision: `30906ed68586556e57eb381f6e4889732a9caec9`

Repository: `/home/outsider/Projects/Hermes_agent/LifeOS_plugin`

## Conclusion

The apply interruption finding is closed. No actionable finding remains in these bounded correction paths.

A real process kill during the apply stop callback leaves a durable `stopped` journal. The dashboard admits authenticated recovery for that state. Direct recovery finishes `rolled_back` and retains the original program, profile, user data, and baseline.

The standalone restore and source-label closure probe also passes at this revision. Accept this correction. The primary reviewer's full release gate remains a separate required check.

## Source assessment

The runtime change moves the existing journal write before the service-stop callback. `lifeos_hook_bridge/update_transaction.py:232` saves the mount snapshot. Lines 234 and 235 publish the `stopped` state. Line 236 calls `stop`.

This ordering gives recovery the required mount snapshot before publishing a recoverable state. The journal is durable before the callback can stop the service. The existing directory synchronization from the previous correction still applies. No new recovery state or authorization path is required.

The reviewer read the complete `30906ed..eed9bdb` diff and the added real process-kill regression. [The correction diff](raw/correction.patch) and [the numbered source excerpt](raw/apply-journal-source.txt) preserve the reviewed change.

## Independent apply closure probe

The probe uses a disposable fixture from `UpdateTransactionTests.fixture`. It starts the actual `apply_update` in a child process. The stop callback writes a synthetic stopped-service marker and sends `SIGKILL` to that child.

The probe reads the durable journal and calls the actual `recover_update`. It compares the profile files, user data, and baseline with their original bytes. It checks the original owned program hook.

Observed results from [the full output](raw/apply-closure.txt):

```text
child_exit: -9
stdout: empty
stderr: empty
service_boundary_stopped: true
crashed_state: stopped
recovered_state: rolled_back
recovery_events: [stop, start, verify]
program_hook: owned-v1
user_data_unchanged: true
profile_unchanged: true
baseline_unchanged: true
```

All probe assertions pass. This closes the exact interval that previously left a `prepared` journal and refused recovery.

## Authenticated dashboard recovery admission

A separate native owner fixture uses the actual Hermes password-session middleware and authentication routes. Its job has a `stopped` manifest and a dead applying worker status. The probe calls the actual dashboard recovery route through the application test client.

The probe substitutes only systemd liveness and detached worker launch. It checks the fresh authorization with the actual memory administration validator and the recovery action binding.

Observed results:

```text
dashboard_state: interrupted
transaction_state: stopped
POST /installation/update/recover: HTTP 200
response.state: recovering
recovery_launch_count: 1
recover_bound_authorization_valid: true
```

This verifies authenticated admission and grant creation. It does not run a real systemd worker. The direct filesystem recovery probe verifies the recovery operation separately. These results are not live end-to-end service evidence.

## Retained restore and source-label closures

The reviewer reran the previous standalone closure probe at `eed9bdb`. It uses public native sources and real Bun.

The restore scenario still leaves `restore_stopping` after a real killed child. Recovery calls only `start` and `verify`, retains the selected version and later memory and profile edits, and leaves the baseline unchanged. A later restore still refuses changed user data.

The source scenarios still exclude private filenames, private titles, and normalized forgotten filenames from adoption and already registered canonical, Knowledge, and owner search responses. Memory ownership and external sharing remain disabled in the owner fixture.

The control cases still preserve canonical refusal for a forgotten dynamic title and admission of an operational `Research` directory. The safe-body search control does not return the forgotten title.

[The rerun output](raw/prior-closures.txt) contains all synthetic observations. [The preserved probe source](raw/prior-closures-probe.py) contains the assertions. The command manifest records the original probe path used for this rerun.

## Results and commands

| Check | Result | Evidence |
| --- | --- | --- |
| Independent apply crash, direct recovery, and authenticated dashboard admission probe | Exit 0; all assertions pass | [apply probe](raw/apply-closure.txt) |
| Previous standalone restore and source-label closure probe | Exit 0; all assertions pass | [prior closures](raw/prior-closures.txt) |
| Added `test_apply_stop_crash_has_a_recoverable_durable_journal` regression | One test passes; no skips; exit 0 | [regression](raw/regression.txt) |
| `git diff --check 30906ed..eed9bdb` | Exit 0; no diagnostics | [diff check](raw/diff-check.json) |

Run the bounded runner from the repository:

```sh
/home/outsider/.cache/lifeos-plugin-memory/memory-plugin-test-env/bin/python docs/agents/2026-10-02-sol-apply-closure/raw/run-bounded.py
```

[The command and revision manifest](raw/commands-revision.json) records exact commands, exit codes, reviewed identity, and environment. The reviewer did not repeat the earlier 73-case selection or run the complete suite. The primary reviewer is preparing the full gate at this revision.

Synthetic home: `/home/outsider/.cache/lifeos-plugin-memory/sol-review-followup-home`. Temporary fixtures stay inside its `tmp` directory. Its `.cache` directory exists. Fixture directories are outside the public documentation tree. The runner uses the same pinned public Hermes and LifeOS sources as the previous review.

## Limits and side effects

This review covers the final apply journal change and the prior standalone closure scenarios. It does not extend to new architecture work, full hook parity, production service recovery, real model requests, or external-client delivery.

The process kills are real. The filesystem operations and native source calls are real. Service callbacks, systemd liveness, and detached worker launch are isolated boundaries. No real service was stopped.

The reviewer did not change runtime code or tests, access production or shared memory, use real credentials, call journal tools, change branches, use another agent, or modify GitHub. All new files are review evidence and probes. No external system needs rollback.
