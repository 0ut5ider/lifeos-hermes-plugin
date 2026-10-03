# Follow-up verification of review corrections

Date: 2026-10-02

Role: Independent reviewer of corrections to two reproduced findings

Question: Does commit `30906ed` close the restore interruption and source-label findings without a meaningful introduced regression?

Model: GPT-6.1-Sol, high reasoning effort

Reviewed revision: `30906ed68586556e57eb381f6e4889732a9caec9`

Correction base: `85c09023235fb358af18516b67bd5d012b2578ab`

Original pull request base: `648fe30a5c5f40551c9a3d73f0d80f527dbd7412`

## Conclusion

Both original findings are closed in the tested paths. No actionable regression survives review of the correction diff.

A separate apply interruption defect remains. The primary reviewer explicitly requested this adjacent check during the follow-up. The defect exists at the original pull request base. Commit `30906ed` does not introduce it. It prevents supported recovery after process death during the apply stop interval.

Accept the corrections to the two original findings. Correct the pre-existing apply interruption defect before claiming complete process-death recovery for supported update actions. This bounded review does not replace the full release gate that the primary reviewer is running.

## Verified closure: durable restore stop intent

`lifeos_hook_bridge/update_transaction.py:315` writes `restore_stopping` before `stop` at line 318. `_write_json` now synchronizes the parent directory after replacing the manifest. The worker, dashboard admission, and authenticated recovery path recognize the new state.

The standalone probe kills a real child process inside its synthetic service-stop callback. The durable state is `restore_stopping`. Recovery calls only `start` and `verify`. It retains the selected program, later memory, later profile edits, and the baseline. It does not create a selected-version archive or consume the prior version. A later restore still checks current data and refuses changed user data.

Observed output from [the closure probe](raw/probe-closures.txt):

```text
child_exit: -9
service_boundary_stopped: true
durable_crash_state: restore_stopping
recovered_state: applied
recovery_events: [start, verify]
selected_hook: owned-v2
memory: Synthetic later memory
profile: Synthetic later profile
baseline_unchanged: true
prior_still_exists: true
selected_archive_created: false
later_restore: User data changed after update; automatic restore refused
```

A second probe kills recovery after `recover_update` writes `applied`, before the worker can write its final status. The job status still says `recovering`. The dashboard checks the dead-worker boundary and returns `applied`, as required. The selected program and later memory and profile remain intact. [The journal-window output](raw/probe-journal-windows.txt) preserves this result.

The focused tests also pass the case where restart fails after post-stop validation refuses a profile change. That case retains a recoverable `restore_stopping` journal.

## Verified closure: excluded source labels

`lifeos_hook_bridge/memory_adoption.py:112` validates full source projections, including actual paths and frontmatter. It checks normalized dynamic filename labels before accepting candidates. Exclusion summaries do not repeat the excluded label.

`lifeos_hook_bridge/memory_canonical.py:54` validates current declared content and paths. It filters normalized dynamic labels before returning files and records. `lifeos_hook_bridge/memory_access.py:652` applies source projection validation to already registered search rows. This covers registrations created before the correction.

The native probes use real Bun and public native source. They bind the owner account with memory ownership and sharing disabled. The following cases pass:

| Case | Adoption preview | Existing registration canonical response | Owner Knowledge | Explicit owner search |
| --- | --- | --- | --- | --- |
| Private filename | No candidates and no marker | No records | No notes | No results |
| Private frontmatter title | No candidates and no marker | No records | No notes | No results |
| Forgotten filename with underscores | No candidates and no marker | No records | No notes | No results |
| Forgotten dynamic title | Existing behavior retained | Refuses with `MemoryUnavailable` | Refuses | Safe body remains searchable without returning the title |
| Forgotten word `research`, operational domain directory | One candidate | One record | One note | One result |

The forgotten-title case is a control for the existing canonical refusal. Its search result returns the safe body and safe source filename. It does not return the forgotten title. The correction does not advertise that adoption rejects all retired frontmatter titles.

[The full closure output](raw/probe-closures.txt) contains the synthetic responses. No probe demonstrates a model request, external-client delivery, or an authenticated browser session.

## Additional finding: pre-existing apply interruption gap

### P1: Write durable apply stop intent before the stop callback

Location: `lifeos_hook_bridge/update_transaction.py:234`. Related locations: `update_transaction.py:235`, `update_transaction.py:350`, `lifeos_hook_bridge/dashboard/plugin_api.py:535`, and `plugin_api.py:641`.

`apply_update` records `prepared`, snapshots the mount files, and then calls `stop`. It writes `stopped` only after that callback returns. Process death after a successful stop leaves `prepared` in the durable manifest.

The dashboard reports the dead applying worker as `interrupted`. Recovery refuses because `prepared` is outside its recoverable states. Restore also refuses. Direct `recover_update` rejects the snapshot. The gateway remains stopped at the synthetic boundary, and the supported controls cannot resume it.

This ordering is present at `648fe30a5c5f40551c9a3d73f0d80f527dbd7412`. The saved [original source excerpt](raw/apply-pr-base.txt) and [current source excerpt](raw/apply-current.txt) show the same sequence. This is not a failed restore correction or a regression introduced by `30906ed`.

#### Concrete reproduction

1. Create a disposable update fixture from `UpdateTransactionTests.fixture`.
2. Call the actual `apply_update` in a child process.
3. Write a synthetic stopped-service marker in the stop callback.
4. Kill the child with `SIGKILL` before the callback returns.
5. Query actual dashboard status and recovery functions with the systemd liveness boundary set to inactive.

Run from the repository with the safe environment in [the command manifest](raw/commands-revision.json):

```sh
/home/outsider/.cache/lifeos-plugin-memory/memory-plugin-test-env/bin/python docs/agents/2026-10-02-sol-review-fix-followup/raw/probe-journal-windows.py
```

Observed output from [the complete probe output](raw/probe-journal-windows.txt):

```text
child_exit: -9
stopped_marker: true
transaction_state: prepared
dashboard.state: interrupted
dashboard.transaction_state: prepared
restore: HTTP 409, There is no applied LifeOS update to restore
recover: HTTP 409, There is no interrupted LifeOS swap to recover
direct_recovery: Update snapshot does not need interrupted recovery
hook: owned-v1
```

The probe uses a real killed process and actual filesystem transactions. Its service callback and systemd liveness response are synthetic. It does not stop a live gateway or establish live end-to-end recovery.

Minimal suggested fix: write durable apply-stop intent before calling `stop`. Give that state a no-swap recovery path that restarts the current installation. Preserve later data and profile edits. Add worker and dashboard state handling and a process-death regression for the stop interval. Do not treat every prepared snapshot as recoverable without identifying whether its stop intent was published.

## Test results and evidence

The reviewer reran these selections at the exact reviewed revision:

| Selection | Result | Output |
| --- | --- | --- |
| `test_update_transaction`, `test_update_worker`, `test_memory_admin_dashboard`, `test_memory_source_labels`, `test_memory_canonical` | 73 passed; no failures or skips; exit 0 | [focused tests](raw/focused.txt) |
| Dashboard and memory dashboard Node tests | 12 passed; no failures or skips; exit 0 | [dashboard tests](raw/dashboard.txt) |
| Standalone restore and source-label closure probe | All assertions passed; exit 0 | [closure probe](raw/probe-closures.txt) |
| Completed-recovery and adjacent apply journal probe | All assertions passed; exit 0 | [journal probe](raw/probe-journal-windows.txt) |
| `git diff --check 85c0902..30906ed` | Exit 0; no diagnostics | [diff check](raw/diff-check.json) |

[The command manifest](raw/commands-revision.json) records exact commands, revision identities, environment, and exit codes. [The correction diff](raw/fix-diff.patch) records reviewed source and test changes.

Fixture home: `/home/outsider/.cache/lifeos-plugin-memory/sol-review-followup-home`. Its `tmp` directory holds temporary fixtures. Its `.cache` directory exists. Bun resolves to the real installed executable. Fixtures remain outside the public report folder and contain synthetic data only.

## Review limits and side effects

This was a bounded follow-up. The reviewer read the correction diff, the new source-label tests, and the added transaction, worker, and dashboard cases. The reviewer traced their current callers. The reviewer did not rerun the full suite or repeat the wider architecture review.

Model and systemd boundaries are isolated. The review does not prove live delivery, production recovery, or paired side-effect equivalence for all 74 hooks. The primary reviewer is responsible for the full existing gate and independent verification.

The reviewer did not edit implementation or tests, change branches, access live servers, use credentials, access shared memory or journal tools, or modify GitHub. New files are review reports and probes. Temporary fixture data uses a separate synthetic home. No external system needs rollback.
