# Selection recovery and profile authorization

Date: 2026-10-07. Branch: `feature/selection-recovery-fixes`. Base: merged PR3, `31ce16c994eb002eed1da05010aa41e53ed3fed7`.

The post-merge review finds two defects. A process can die after publishing a target mount but before recording its completion. Recovery then restores the previous selection without restoring its mounted files. The dashboard can also launch another profile's recovery job after authorizing only its current profile's owner.

## Corrections

The selection transaction records mount intent before publication. Rollback recovers a pending target mount before changing the selected home. It records that recovery so a retry does not recover the wrong mount after the previous home takes effect. It restores the previous mount and checks the selection and memory root before restarting services. Native Mount verifies the published files and Hermes configuration. Conflicting later edits prevent restoration and service restart.

The dashboard filters jobs by physical profile and checks the binding again before launch. It passes the verified account to the worker. The worker checks the request profile, recovery journal profile, and current owner before service access. Refused workers preserve the job status. Pending jobs still serialize shared account services, and their profile owner must complete or recover them.

## Results

| Check | Result | Output |
| --- | --- | --- |
| Original failures before the fixes | Five expected failures, five passes, three passing subtests | [red-tests.txt](red-tests.txt) |
| Selection, profile isolation, installation locks, fresh-store components, update, backup, and evidence tests | 164 passes, six fixture skips, 86 passing subtests | [neighbor-regression.txt](neighbor-regression.txt) |
| Native Mount, Hermes configuration, and authenticated dashboard regression | 59 passes, no skips, 44 passing subtests | [native-dashboard-tests.txt](native-dashboard-tests.txt) |
| Prepared fresh-store controls and native TaskGovernance update control | 27 passes, no skips, 12 passing subtests | [native-fresh-controls.txt](native-fresh-controls.txt) |
| Native selection with process death during publication and after commit | One pass, two passing subtests, no skips | [native-selection-tests.txt](native-selection-tests.txt) |
| Final selection and profile checks, including refusal after root or setting changes | 24 passes, seven passing subtests, no skips | [final-selection-tests.txt](final-selection-tests.txt) |
| Hook evidence integrity and development completion | Pass | [evidence-check.txt](evidence-check.txt) |

The configured native controls include all six cases that skip in the neighboring run. Some tests run in both commands; the table does not count distinct tests across commands. No final test run has a failure. Starlette emits its installed `BlockingPortal` deprecation warning in three runs. The retained output shows the warning.

The new native test uses a separate file because the evidence ledger records the original mount test's hash. Its first move omitted the fixture environment attribute. [native-fixture-correction.txt](native-fixture-correction.txt) retains that failure. The corrected fixture passes both cases. The original mount test remains byte-identical, and the evidence checker passes without changing historical artifact hashes.

## Reproduction scope

`test_installation_selection.py` uses physical files and actual child-process termination. Its expanded tests exercise real inner mount journal publication and restoration. They cover death during target restoration, death during the previous mount, ordinary mount exceptions after publication, and refusal after a later owner edit.

`test_selection_native_mount.py` executes real Bun Mount and Hermes configuration checks. It uses separate synthetic native installations with different constitution text. It kills the child during actual publication or after native commit but before the outer completion stamp. Recovery restores the exact prior native prompt, selected root, and memory configuration, with a committed previous mount.

`test_selection_profile_isolation.py` uses two named profiles with distinct owners. It runs real dashboard lookup, owner checks, locks, and launch construction. A local `systemd-run` recorder captures the command. Actual worker processes refuse a mismatched request profile, a mismatched journal profile, and a revoked owner before accessing the local service recorder.

Service callbacks in the crash controls are synthetic. These tests do not start real gateway, dashboard, or Pulse services. They use no personal records or external credentials. They do not repeat the complete 2,235-test sweep or final installed-host release acceptance. They do not reopen jobs already marked `rolled_back` by older code.

## Commands

Run from the repository root. The prepared source paths below identify the local fixture inputs used by this verification.

```bash
export PATH=/home/outsider/.bun/bin:$PATH
export PYTHONPATH=tests:.:/home/outsider/.cache/lifeos-step1-20261007/prepared-review-final/hermes
export TMPDIR=/home/outsider/.cache/lhc6
export LIFEOS_MEMORY_SOURCE=/home/outsider/.cache/lifeos-step1-20261007/prepared-review-final/lifeos/LifeOS/install
export LIFEOS_HERMES_SOURCE=/home/outsider/.cache/lifeos-step1-20261007/prepared-review-final/hermes
selection_python=/home/outsider/.cache/lifeos-plugin-memory/memory-plugin-test-env/bin/python

"$selection_python" -m pytest -q -rs \
  tests/test_installation_selection.py tests/test_selection_profile_isolation.py \
  tests/test_lifeos_installation.py tests/test_fresh_store_status.py \
  tests/test_fresh_store_dashboard.py tests/test_fresh_store_worker.py \
  tests/test_fresh_store.py tests/test_fresh_store_paths.py \
  tests/test_installation_lock.py tests/test_installation_lease.py \
  tests/test_update_transaction.py tests/test_update_worker.py \
  tests/test_version_drift_baseline.py tests/test_step1_acceptance.py \
  tests/test_hook_evidence.py tests/test_profile_backup.py tests/test_profile_backup_recovery.py

"$selection_python" -m pytest -q -rs \
  tests/test_memory_admin_dashboard.py tests/test_mount_transaction.py

export LIFEOS_FRESH_SOURCE=/home/outsider/.cache/lifeos-step1-20261007/installer-review-final
export LIFEOS_TASK_HOOK_PATH=$LIFEOS_MEMORY_SOURCE/hooks/TaskGovernance.hook.ts
"$selection_python" -m pytest -q -rs \
  tests/test_fresh_store.py tests/test_fresh_store_dashboard.py tests/test_fresh_store_worker.py \
  tests/test_update_transaction.py::UpdateTransactionTests::test_capability_record_applies_and_restores_with_native_hook_files

"$selection_python" -m pytest -q tests/test_selection_native_mount.py
"$selection_python" -m pytest -q tests/test_installation_selection.py tests/test_selection_profile_isolation.py
"$selection_python" scripts/check_hook_evidence.py --require-complete
```

The pre-fix command runs only `test_installation_selection.py` and `test_selection_profile_isolation.py` before implementation. Its five failures establish the actual mismatches rather than a missing fixture.

No server, service, model-tier setting, or memory store changes during this verification. The fixes remain staged for the next release.
