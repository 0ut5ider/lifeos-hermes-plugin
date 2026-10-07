# Selection compensation retry corrections

Date: 2026-10-07. Branch: `feature/selection-recovery-fixes`. Starting point: `e7c10d02f2e4385bcea76e9dc0880aabb962c3f3`, PR #4.

The [targeted review](../../agents/2026-10-07-pr4-recovery-lock-review/pr4-recovery-lock-review.md) finds two adjacent failures after the first review corrections. The primary agent independently reproduces both before changing the implementation.

The first failure loses a later SOUL edit after compensation records its target recovery checkpoint or commits the previous native mount. Retrying skips validation and remounts the previous installation. The second failure leaves a failed launcher pending without a transaction journal. New selection and recovery both refuse that job.

## Changes

Every compensation attempt validates or recovers the active native mount before it restores the previous setting and memory root. The native journal must belong to the target or previous installation from the selection journal. The target recovery checkpoint records progress. It cannot bypass validation on retry. Completed mount fingerprints must still match before compensation can remount or restart services.

The active journal can belong to the target after target recovery, or to the previous installation after a previous mount commits. Compensation checks either valid root. Return to the default installation retains the account workspace even after the explicit selection setting is cleared. Ordinary explicit mounting continues to use current profile files as its starting state.

The dashboard queries the unit's `ActiveState` and `Job` in one `systemctl show` call. A successful query must confirm an inactive or failed unit with an empty `Job` before the dashboard infers worker completion. With no transaction journal, the observed selection status becomes failed and permits another selection. With an unfinished journal, the observed status remains interrupted and requires recovery. The query does not rewrite the stored queued status.

Active or transitioning units, queued systemd jobs, failed queries, missing properties, missing controllers, and controller timeouts retain pending admission. The systemd [property printer](https://github.com/systemd/systemd/blob/main/src/systemctl/systemctl-show.c) prints an empty `Job` for no queued job. The local [absent-unit query](systemctl-absent-unit.txt) confirms that format with the installed [systemctl version](systemctl-version.txt). That query is read-only and starts no services.

## Verification

| Gate | Result | Raw record |
| --- | --- | --- |
| Initial native retry and failed-launch regressions before the correction | Expected failures | [red-tests.txt](red-tests.txt) |
| Transitioning or unavailable unit-state regressions before the status guard | Expected failures | [unit-state-red-tests.txt](unit-state-red-tests.txt) |
| Queued systemd job and failed query regressions before checking both properties | Two expected failures | [unit-job-red-tests.txt](unit-job-red-tests.txt) |
| Final selection, native retry, profile authority, admission, and evidence checks | 65 tests and 20 subtests pass, no skips | [focused-tests.txt](focused-tests.txt) |
| Neighboring installation, fresh-store, lock, update, backup, and evidence checks | 153 tests and 86 subtests pass, no skips | [neighbor-tests.txt](neighbor-tests.txt) |
| Native mount, authenticated dashboard, and memory preferences | 68 tests and 49 subtests pass, no skips | [native-dashboard-tests.txt](native-dashboard-tests.txt) |
| Complete hook evidence ledger | Pass | [evidence-check.txt](evidence-check.txt) |

The neighboring and native dashboard runs each report the installed Starlette `BlockingPortal` deprecation warning. The commands overlap in their evidence tests. Their counts are separate gates, not a distinct combined total. [check-status.json](check-status.json) and [.done](.done) record subprocess exit status.

The neighboring gate runs after the native compensation changes. The final focused and native dashboard gates run again after the status guard changes. Raw failure logs retain pytest's whitespace.

## Scope and limits

The retry tests run actual Bun mounting, Hermes configuration validation, and child process exits. They stop a selection after the target native commit. They then stop compensation after the target checkpoint, after clearing the previous setting, or after the previous native commit. Later edits survive two refused retries in each case. Service start and verification callbacks do not run. Matching cases without later edits restore the exact previous SOUL bytes.

The launch and status tests use real local launcher and controller processes. A launcher exits 23, the dashboard observes a confirmed stopped unit, and the next selection obtains a new job. Other tests retain pending admission for a live worker, a transitioning worker, a queued start job, partial or failed queries, an absent controller, and an actual 15-second controller timeout. A stopped worker with an unfinished transaction journal still requires recovery.

These tests use synthetic stores and local service records. They do not start live gateway, dashboard, or Pulse services and do not establish complete installed-host release acceptance. No server is deployed or reconfigured. Model tiers and memory ownership remain unchanged.

The first correction's archived mount source remains byte-identical to `e9337a29848379b44a3fe8ba224d62adc1286d62`, with SHA-256 `a1f8fb6c4ac728284e85dd05960fe35d1ebfaa747ee3f878fe0580af0a0d7857`. This correction does not change the historical ledger or the original `test_mount_transaction.py`.

## Commands

The commands use the prepared Hermes and LifeOS dependency trees from the prior release checks:

```sh
export PATH=/home/outsider/.bun/bin:$PATH
export PYTHONPATH=tests:.:/home/outsider/.cache/lifeos-step1-20261007/prepared-review-final/hermes
export TMPDIR=/home/outsider/.cache/lhc6
export LIFEOS_MEMORY_SOURCE=/home/outsider/.cache/lifeos-step1-20261007/prepared-review-final/lifeos/LifeOS/install
export LIFEOS_HERMES_SOURCE=/home/outsider/.cache/lifeos-step1-20261007/prepared-review-final/hermes
export LIFEOS_FRESH_SOURCE=/home/outsider/.cache/lifeos-step1-20261007/installer-review-final
export LIFEOS_TASK_HOOK_PATH=$LIFEOS_MEMORY_SOURCE/hooks/TaskGovernance.hook.ts
selection_python=/home/outsider/.cache/lifeos-plugin-memory/memory-plugin-test-env/bin/python

"$selection_python" -m pytest -q -rs \
  tests/test_installation_selection.py tests/test_selection_profile_isolation.py \
  tests/test_selection_retry.py tests/test_selection_recovery_admission.py \
  tests/test_selection_native_mount.py tests/test_hook_evidence.py tests/test_step1_acceptance.py

"$selection_python" -m pytest -q -rs \
  tests/test_lifeos_installation.py tests/test_fresh_store_status.py \
  tests/test_fresh_store_dashboard.py tests/test_fresh_store_worker.py \
  tests/test_fresh_store.py tests/test_fresh_store_paths.py \
  tests/test_installation_lock.py tests/test_installation_lease.py tests/test_program_lock.py \
  tests/test_update_transaction.py tests/test_update_worker.py \
  tests/test_version_drift_baseline.py tests/test_step1_acceptance.py \
  tests/test_hook_evidence.py tests/test_profile_backup.py tests/test_profile_backup_recovery.py

"$selection_python" -m pytest -q -rs \
  tests/test_memory_admin_dashboard.py tests/test_mount_transaction.py tests/test_memory_preferences.py

"$selection_python" scripts/check_hook_evidence.py --require-complete
```

Adrian's review should focus on the recovery boundary before every remount, legitimate previous-root journal binding, and pending admission for uncertain workers.
