# Selection review corrections

Date: 2026-10-07. Branch: `feature/selection-recovery-fixes`. Reviewed starting point: `e9337a29848379b44a3fe8ba224d62adc1286d62`, PR #4.

The follow-up review at `e7c10d02f2e4385bcea76e9dc0880aabb962c3f3` finds two adjacent failures. The [compensation retry corrections](../2026-10-07-selection-retry-fixes/README.md) address later edits after recovery checkpoints and failed-launch admission. The counts below describe this initial correction gate.

The focused review reproduces three failures. Recovery overwrites a later owner edit when the target mount commits before the outer completion stamp. A running dashboard refuses valid owner recovery after the worker publishes a different root. Concurrent profiles can both admit a selection job in the same operating system account.

## Corrections

Selection compensation checks completed target mount files against their recorded fingerprints. Committed files must match the published state. Recovered files must match the restored state. Later edits stop rollback before selection restoration or service restart. Explicit mounting keeps its existing behavior and accepts current files as its starting state.

The dashboard and worker use the same selection authority check. The check binds the request and journal to the invoking physical profile and checks its current owner. Recovery checks the request target and the roots recorded in the journal. The selected root and memory configuration root must belong to that interrupted selection. This permits valid recovery when the running dashboard retains its startup root. It does not change the ordinary memory API root guard.

Dashboard selection admission and recovery admission hold an account lock. Selection admission retains the lock across the pending-job scan, request publication, and launch. Detached workers wait for the same account lock before accessing services and retain it through the selection transaction. Each path takes the profile lock before the account lock. The lock uses the existing private file-lock implementation with a separate scope at `<account>/.local/state/lifeos-hook-bridge/selection-coordination`.

## Results

| Check | Result | Output |
| --- | --- | --- |
| New regressions before implementation | Expected failures reproduce owner-edit loss, stale-root rejection, duplicate admission, and missing worker exclusion | [red-tests.txt](red-tests.txt) |
| Final selection, owner/profile refusal, account admission, worker exclusion, native process-death, and evidence checks | 48 passes, 11 passing subtests, no skips | [focused-tests.txt](focused-tests.txt) |
| Neighboring installation, fresh-store, lock, update, backup, and evidence tests | 153 passes, 86 passing subtests, no skips | [neighbor-tests.txt](neighbor-tests.txt) |
| Native Mount, authenticated dashboard, and memory preferences | 68 passes, 49 passing subtests, no skips | [native-dashboard-tests.txt](native-dashboard-tests.txt) |
| Complete hook evidence check | Pass | [evidence-check.txt](evidence-check.txt) |

The evidence tests run in both the focused and neighboring commands. The table does not count distinct tests across commands. All final commands exit with code zero. Starlette emits its installed `BlockingPortal` deprecation warning in the neighboring and native dashboard runs. The retained logs show the warning.

The initial red run also collects ten existing profile fixture tests through an imported test class. The final test module imports the fixture module instead, so it does not duplicate those tests. A subtest and its subsequent preservation assertion both fail for the owner-edit case. The raw red count therefore does not count distinct defects.

Adding recovery journals to the shared profile fixture initially leaves transaction directories present before tests create a real transaction. [fixture-correction.txt](fixture-correction.txt) retains these four fixture failures. The helper now permits jobs without a transaction directory. The corrected focused run passes.

The authenticated dashboard fixture uses the account home itself as the profile. The first account lock therefore collides with its held profile lock. [The diagnostic](dashboard-selection-diagnostic.txt) and [lock-path trace](lock-path-trace.txt) record the two refused selection cases. The correction gives account coordination a separate lock scope. [The initial native run](native-dashboard-before-lock-path-fix.txt) retains the failures.

The historical evidence ledger records the pre-fix mount module hash. Changing that module makes the checker report a changed artifact, as [the initial check](evidence-before-source-snapshot.txt) shows. [The retained source](mount-transaction-before-fixes.py) is byte-identical to that module at `e9337a2`, with SHA-256 `a1f8fb6c4ac728284e85dd05960fe35d1ebfaa747ee3f878fe0580af0a0d7857`. The ledger points to this snapshot with the same hash. Historical results keep their original source identity; the new tests verify the current implementation. No historical result or expected hash changes.

The Git tracking check initially rejects the new snapshot before it enters the index. [The retained output](evidence-tracking-before-stage.txt) records that prerequisite failure. The snapshot is staged before the final evidence test run. The original `tests/test_mount_transaction.py` remains unchanged.

## Scope

The owner-edit regression executes real Bun mounting and Hermes configuration checks. The child exits after the actual target mount commits and before the outer completion stamp. A later SOUL edit survives two refused recovery attempts. The target selection and memory root remain selected. No service start callback runs.

The dashboard regression terminates a real child after root publication. The running dashboard then constructs the recovery launch for the valid owner. Other checks refuse revoked ownership, a different journal profile, and roots outside the interrupted journal. The detached worker also refuses unrelated roots before service access.

The concurrency regression runs two real processes with supported named profiles and distinct current owners. It retains real profile and account file locks. A barrier models both processes reaching admission together. Before the fix, both scans return no pending job and both processes queue a request. After the fix, exactly one request queues and the other returns HTTP 409. A separate actual worker waits for a held account lock before constructing its service controller.

The launch transport is a local recorder. Service callbacks in crash and worker controls are synthetic. These are component and native integration checks. They do not start live gateway, dashboard, or Pulse services. They do not establish live service interleaving or complete installed-host release acceptance. The complete 2,235-test release sweep is not repeated.

No dependency, server, model-tier setting, production configuration, or personal memory store changes during these checks. The changes remain staged for release.

## Commands

Run from the repository root with the prepared native fixtures:

```bash
export PATH=/home/outsider/.bun/bin:$PATH
export PYTHONPATH=tests:.:/home/outsider/.cache/lifeos-step1-20261007/prepared-review-final/hermes
export TMPDIR=/home/outsider/.cache/lhc6
export LIFEOS_MEMORY_SOURCE=/home/outsider/.cache/lifeos-step1-20261007/prepared-review-final/lifeos/LifeOS/install
export LIFEOS_HERMES_SOURCE=/home/outsider/.cache/lifeos-step1-20261007/prepared-review-final/hermes
export LIFEOS_FRESH_SOURCE=/home/outsider/.cache/lifeos-step1-20261007/installer-review-final
export LIFEOS_TASK_HOOK_PATH=$LIFEOS_MEMORY_SOURCE/hooks/TaskGovernance.hook.ts
selection_python=/home/outsider/.cache/lifeos-plugin-memory/memory-plugin-test-env/bin/python

"$selection_python" -m pytest -q \
  tests/test_installation_selection.py tests/test_selection_profile_isolation.py \
  tests/test_selection_recovery_admission.py tests/test_selection_native_mount.py

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

Longer checks run in a detached process. [check-status.json](check-status.json) records the return code of each detached command. The `.done` marker records completion on disk.
