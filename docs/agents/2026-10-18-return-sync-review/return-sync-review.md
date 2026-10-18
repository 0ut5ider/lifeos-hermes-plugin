# Review of 2118971a: synchronize dependencies on provider return

- Date: 2026-10-18
- Role: code reviewer
- Model: Claude Opus 5.5 (claude-opus-5-5)
- Question: Does commit 2118971a (`fix(memory): synchronize dependencies on provider return`) fix the root cause where the restarted gateway runs a Hermes source-update completion under the update lock and the return's fresh-agent probe fails? Check crash re-entry, environment, file location, managed installs, failure state, and tests.

## Test runs (frozen environment, `~/agent-scratch/t.sh`)

| Pattern | Result | Raw |
|---|---|---|
| test_memory_transition.py | 6 tests OK | raw/rv8-a.txt |
| test_inplace_worker.py | 27 tests OK | raw/rv8-b.txt |
| test_memory_workflow*.py | 5 tests OK | raw/rv8-c.txt |
| test_memory_return*.py | 9 tests OK | raw/rv8-d.txt |
| test_memory_removal_workflow.py | 5 tests OK | raw/rv8-e.txt |

## 1. Root-cause fit

Hermes v0.21.7 `hermes_cli/venv_sync.py prepare_launch` (line 403) enters the completion branch only when `not owed_to_cli and (not current or pending.is_file())`, where `current = pm.venv_is_current(project_root=root)` and `pending` is `<install state>/source-completion-pending`.

- `pm.install.venv_is_current` computes `package.expected_stamp(enabled, **_member_inputs(None))`, so the stamp depends on the plugin members discovered from the profile's `config.yaml`. Disabling `lifeos` and `lifeos-hook-bridge` changes the stamp, so the venv is not current after the return publishes the configuration. That matches the live finding.
- `dependency_plan.synchronize` calls `pm.client.sync_venv(explicit=True, project_root=source)` with `plugins=None`. `pm.install.sync_venv` discovers the same members from the same config (HERMES_HOME=profile), commits the generation, and records the new stamp with `facts.record_state("venv", stamp, ...)`. The next launch's `venv_is_current` compares against that recorded stamp, so it returns true.
- `sync_venv` does not arm `source-completion-pending` (only `_sync_source_dependencies(arm=True)` in the completion path does). On a host without a leftover marker, the launcher skips the completion branch. With `current` true and the store interpreter unchanged, it also does not re-exec.
- Product builds and launchers are owed only through the pending marker or a non-current venv. The return changes neither the checkout nor its commit, so nothing else is owed.
- Residual (not caused by this commit): if an earlier update or install left a `source-completion-pending` marker, an unsupervised launch (the probe) still runs the tail. That is a different cause from the observed failure and the installer's own synchronize has the same exposure.
- Evidence beyond reading: the in-place installer already uses this exact synchronize before it starts services, and the E2E runs did not show the gateway completion after install.

Verdict on 1: fits the root cause.

## 2. Crash and re-entry

- In `apply`, every non-terminal state ('ready', 'draining', 'publishing', 'configured', 'restarting') runs the full sequence: drain or quiesce, `operation.apply`, `_enabled`, `verify_stopped`, `synchronize()`, then 'restarting' and `resume`. So a resumed apply always synchronizes before restart. A crash during `resume` (state 'restarting') re-quiesces and synchronizes again.
- `sync_venv` is idempotent: when the recorded stamp already matches, `_commit_selection` runs with `current=True` and builds nothing.
- Same label twice: `synchronize_source` unlinks `<label>.json` first; `run_stage` opens `.stdout` and `.stderr` with `'wb'` (truncate). `dependency_plan.main` opens the output with `O_EXCL`, which is safe because of the unlink. A second run with the same label works.
- Early-return states 'verification_required' and 'verified' do not synchronize, which is correct (services already restarted after a synchronize).
- Rollback runs `synchronize()` after `operation.rollback` and `_enabled`, before `resume`. Its label 'dependency-return-rollback' does not collide with the apply label. A rollback from 'ready' or an unstarted 'draining' returns before the lock block and does not synchronize, which is correct because nothing was published.

## 3. Environment and file location

- `host_synchronizer` sets HOME (account home), HERMES_HOME (profile), XDG_RUNTIME_DIR, DBUS_SESSION_BUS_ADDRESS, PYTHONDONTWRITEBYTECODE, and `synchronize_source` sets PYTHONPATH=source. This matches `release_plan.service_environment` except the Bun PATH prefix. `pm` venv sync does not use Bun (grep of `pm/*.py` finds only "bundle"), so the missing Bun entry does not matter for this call.
- `Path(__file__).with_name('dependency_plan.py')`: the release and in-place flows copy `optional/lifeos_release_manager` to `job/worker` (cli.py:172, inplace_preparation.py:353) and `release_worker.py` runs from there, so for `synchronize(job, request, ...)` the path is the same file as the old `job/'worker/dependency_plan.py'`. `inplace_preparation.py:252` already uses this pattern.
- Memory workflow: for a provider return, `memory_workflow.launch` runs `memory_workflow_worker.py` beside `memory_workflow.py` in the installed manager plugin directory, which carries all of `manager_files` including `dependency_plan.py`. Only the removal branch uses the retained `removal/recovery-manager` copy, and `host_synchronizer` is not called on that branch. The retained copy also comes from `manager_files`, so it would contain the file anyway.

## 4. Managed installations

`load_record(profile)` returns None when no host record exists, so `host_synchronizer` returns None and `apply`/`rollback` skip the call. Behavior is unchanged. `HostSynchronizerTests.test_only_an_in_place_host_synchronizes_its_dependencies` covers this.

## 5. Failure

- If synchronize fails, `apply` raises with state 'configured', the return configuration published, Pulse disabled, and the gateway and dashboard stopped. The worker records the failure and writes 'interrupted'.
- Re-entry from 'configured' (Recover, action 'recover' takes the same `else` branch with the synchronizer) quiesces, re-applies, and synchronizes again. A transient failure recovers.
- A persistent forward-sync failure keeps Recover failing. Rollback is still an exit: a failed `sync_venv` commits nothing, so the recorded stamp still matches the original plugin set, and the rollback synchronize after restoring the configuration is a no-op. Services then resume.
- Tradeoff (non-blocking): before this commit, a sync failure degraded Hermes to the previous dependencies but the services ran (`hermes_bootstrap.py` "Degrade, never brick the CLI"). Now a sync failure leaves the dashboard stopped until Recover or rollback through the retained standalone recovery path (docs/memory-portability.md:49). This is the same state class as other mid-apply failures, so it is consistent with the design.
- Message: "The Hermes dependencies cannot synchronize for dependency-return" names the internal label rather than the operation, and does not say that services stay stopped or what to do. Readable, but weak. `subprocess.TimeoutExpired` from `run_stage` (1800 s) is not translated and surfaces raw. Non-blocking.
- `host_synchronizer` is evaluated eagerly, before `apply`, so a `HostRecordRejected` (tampered record) also blocks a verify-only Recover from 'verification_required'. That is an edge case with a clear error. Non-blocking.

## 6. Tests

- `test_dependencies_synchronize_after_publication_and_before_services_restart` checks the ordering for apply and rollback against the real fixture services (config published, both roles inactive at the call). Good.
- `HostSynchronizerTests` covers the None path and the failure message with `run_stage` mocked.
- Gap: no test drives `memory_workflow.execute` for apply, recover, or rollback, so nothing proves the manager passes the synchronizer, uses the right label, or that the `.inplace_worker` import resolves in the workflow worker's namespace. No test covers the non-None `host_synchronizer` path (environment contents, `record['source']`). No test covers a resumed apply (from 'configured' or 'restarting') calling synchronize. These are low risk given the code reads clearly, but the wiring is what the live fix depends on, so a container rerun of a provider return is the real verification.

## Standards

- ABOUTME headers are present in the touched modules. No em dashes in the diff. Names are clear. The test comment explains why, not history. The CHANGELOG line uses "Before, ..." which is a changelog, so history is appropriate there.
- `host_synchronizer` docstring explains the reason, not history. Fine.

## Blocking findings

None.

VERDICT: CLEAN
