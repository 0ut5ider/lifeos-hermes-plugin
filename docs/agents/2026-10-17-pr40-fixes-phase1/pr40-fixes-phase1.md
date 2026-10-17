# PR 40 fixes, phase 1

- Date: 2026-10-17
- Role: implementation engineer (subagent), branch `feature/minimal-install-review`, commits only, no push
- Question: implement the round 1 fix plan rows Spec A1 (with Standards 4), A2, A3, A4, A5, A6, A7, A8, C1, C2, C5, and confirm C7.
- Model: Claude Opus 5.5 (`claude-opus-5-5`)
- Raw data: `raw/` (red and green runs per item), `raw/final/` (final run per test file, `summary.txt`, `node-cjs.txt`), `raw/c2-regression-test_release_accounts-first-run.txt`.

Base commit: `90d1bf7f`. Commits added (oldest first):

| Commit | Subject |
| --- | --- |
| `0a328d42` | fix(removal): tolerate a missing update hold |
| `f9bc5172` | fix(preparation): check compatibility first |
| `5f1f8a2c` | feat(compatibility): qualify interpreter, capabilities |
| `42e3b4c3` | feat(compatibility): probe host capabilities |
| `6ed9e263` | feat(worker): verify the host after restart |
| `7275da91` | fix(compatibility): report a damaged host record |
| `f7d302bf` | feat(bridge): report host drift in lifeos-version |
| `798fd606` | feat(review): list host files, keys, and conflicts |
| `4dc879e5` | test(worker): cover rollback, registration, consumers |
| `747884d0` | test(release): cover the builder and refusal text |
| `e967166e` | style(compatibility): describe a damaged record plainly |
| `5dd731c0` | test(release): move the account check boundary |

## Per finding

### C1: removal tolerates a missing update hold

- Changed: `optional/lifeos_release_manager/inplace_removal.py` `host_plan`. The host record is still required (`Removal requires the LifeOS host record`). An absent hold produces no plan entry. A hold that is not a regular file, or that belongs to another integration, still refuses.
- Test: `tests/test_inplace_removal.py` `test_missing_hold_does_not_block_removal` failed first with `ReleaseRejected: Removal requires the LifeOS host record and its Hermes update hold` (`raw/c1-red.txt`), then passed. `test_missing_host_record_still_refuses_removal` passed before and after (characterization).
- Commit: `0a328d42`.

### C2: compatibility check before the download

- Changed: `inplace_preparation.prepare_inplace` runs `check(profile)` and refuses before `download_integration`.
- Test: `tests/test_inplace_preparation.py` `test_compatibility_refusal_comes_before_any_download` failed first with `AssertionError: Preparation downloads before the compatibility check` (`raw/c2-red.txt`), then passed.
- Regression found in the final run: `tests/test_release_accounts.py` `test_cli_preparation_records_account_and_preserves_native_selection` failed with 2 errors, because it used the download as its stop point (`raw/c2-regression-test_release_accounts-first-run.txt`). I changed the test to expect the compatibility refusal; it still asserts the owner account and the unchanged native selection, and its catalog still raises if a download happens. Commit `5dd731c0`. Adrian may want to look at this test change, because it is a changed assertion, not a new one.
- Commit: `f9bc5172`.

### C5: damaged host record gives a specific `host_drift` reason

- Changed: `host_compatibility.check` catches `HostRecordRejected`, inspects the host without a record, and returns `state: host_drift`, `compatible: false`, `installed: false`, with a first reason `invalid_host_record` whose message is the defect plus the record path (for example `The LifeOS host record requires a bounded owner file: /home/x/.hermes/lifeos-host.json.`). `STATES` maps `invalid_host_record` to `host_drift`. `host_record.load_record` now re-raises its own `HostRecordRejected` instead of rewrapping it as "unreadable", so the specific defect survives.
- Tests: `tests/test_host_compatibility.py` `test_damaged_record_is_drift_that_names_the_record` (bad JSON, group-writable, extra key, 3 MB) failed first with `HostRecordRejected` (`raw/c5-red.txt`). `tests/test_release_dashboard.py` `test_malformed_host_record_is_reported_as_drift_with_its_reason` failed first with `409 != 200` against the real dashboard router (`raw/c5-dashboard-red.txt`). Both pass. The CLI `compatibility` command calls the same `check`, so it prints the result and exits 1; I did not add a separate CLI test.
- Commits: `7275da91`, `e967166e` (comment wording).

### C7: confirm only

Confirmed. Stock v0.21.7 `pm/client.py:208-209` (read from `stock-hermes.tgz`) declares `sync_venv(..., evict_incompatible_plugins: bool = False)` and passes the value through on both the direct and the request path. `optional/lifeos_release_manager/dependency_plan.py:71` calls `pm.client.sync_venv(explicit=True, project_root=Path(source))` and does not pass `True`. No code change.

### A7: interpreter and capabilities in the compatibility manifest

- Changed:
  - `host_compatibility.py`: `_qualified_entry` validates manifest entries. Required keys: `label`, `commit`, `patches`, `files`, `python` (major.minor string), `capabilities` (`{hooks: [distinct names], middleware_api: int >= 1}`); optional `known_conflicts` (up to 20 distinct sentences of at most 300 characters, no control characters). `_entry` still validates the four identity keys, so `host_record` and the `lifeos-host.json` schema are unchanged. `inspect_host(..., python=None)` refuses a running interpreter other than `entry['python']` with code `unsupported_interpreter` (state `unsupported_version`) and a message that names both versions, on the fresh and the recorded path.
  - `scripts/build_host_compatibility.py`: `bridge_capabilities()` returns `sorted(PATCHED_HOOKS)` and `MIDDLEWARE_API = 1`. `build_entry(..., capabilities, known_conflicts=None)` reads the interpreter from `pm/lock.json` `packages.python.version` in the stock archive (`3.14.7+20260901` gives `3.14`) and refuses an archive without it. `--known-conflict` (repeatable) emits `known_conflicts`.
  - `optional/lifeos_release_manager/host-compatibility.json` regenerated with the script from the qualified stock archive: adds `"python": "3.14"` and the five hooks with `middleware_api: 1`. No known conflicts are declared.
  - Manifest hash binding: `scripts/build_integration_release.py` computes `host_compatibility_sha256` from the packaged file at build time, and `integration_package.validate_integration` compares it with the certificate. No stored hash exists in the repository, so nothing else changes. A release must be rebuilt for the new manifest.
- Tests (all failed first, `raw/a7-red.txt`, 39 errors: the old validator rejected the new keys and the builder had no `bridge_capabilities`): `test_host_compatibility.py` `test_interpreter_other_than_the_qualified_one_is_refused`, `test_accepts_known_conflicts`, `test_refuses_malformed_qualification`; `test_host_compatibility_manifest.py` `test_entry_declares_the_pinned_interpreter_and_the_capabilities`, `test_entry_records_known_conflicts_when_given`, `test_archive_without_an_interpreter_pin_is_refused`, `test_bridge_capabilities_name_the_patched_hooks`, `test_declares_the_bridge_capabilities`. The shipped-manifest rebuild test ran against `LIFEOS_STOCK_HERMES_ARCHIVE` and passes (13 tests, no skip). Fixtures in `test_host_patches.py` and `test_inplace_removal.py` gained the two keys.
- Preparation probe: `prepare_inplace` runs the capability probe (A2 below) with the host interpreter against `job/hermes-preview` after `build_preview`. That call site is not unit tested; see "Not tested".
- Commits: `5f1f8a2c`, `42e3b4c3`.

### A2: post-restart new PID and capability probe

- Changed:
  - New module `optional/lifeos_release_manager/host_capabilities.py`, `probe_capabilities(python, source, entry, *, environment=None)`. It runs `python -I -B -c PROBE <source>` with `PYTHONPATH`, `PYTHONHOME`, and `VIRTUAL_ENV` removed. It requires `entry['python']`, every `entry['capabilities']['hooks']` in `hermes_cli.plugins.VALID_HOOKS`, and `hermes_cli.middleware.REQUIRED_MIDDLEWARE_API_VERSION == entry['capabilities']['middleware_api']`. Every failure raises `ReleaseRejected`. The same function runs at preparation (preview) and after restart (installed source).
  - `inplace_worker.py`: `boot_ticks()` (CLOCK_BOOTTIME in `/proc` clock ticks), `_show`, `check_restarted(units, drained)` (active, MainPID, start time strictly after the drain), `verify_restart(...)`. `_run` records `drained = boot_ticks()` right after `_consumers_stopped`, takes `services.resume()['services_started']`, and after `verify_registration` calls `verify_restart` with `host_python(source)`. Created gateway or dashboard units are checked too.
- Tests: `tests/test_host_capabilities.py` (9 tests: small real modules, inherited `PYTHONPATH` ignored, no bytecode written, the patched Hermes of the test environment passes, the stock v0.21.7 archive is refused with `patched plugin hooks: augment_tool_result, ...`). Failed first with `ModuleNotFoundError` (`raw/a2-probe-red.txt`). `tests/test_inplace_worker.py` `RestartTests` and `VerifyRestartTests` use real runtime-linked user units with synthetic names; they failed first with `AttributeError` (`raw/a2-worker-red.txt`).
- Commits: `42e3b4c3`, `6ed9e263`.

### A3: enabled state recorded and verified

- Changed: `inplace_services.inventory` reads `UnitFileState` and returns `enabled: {role: state}` for bound roles. `inplace_plan.inspect_inplace` stores `services.enabled` in the plan. `inplace_worker.check_enabled({unit: state})` refuses a changed `UnitFileState` after restart (inside `verify_restart`). The `ProfileServices` journal schema is unchanged.
- Tests: `tests/test_inplace_services.py` `test_inventory_records_whether_each_bound_unit_is_enabled` failed first with `KeyError: 'enabled'`, then on the fixture (the synthetic unit had no `[Install]` section, so `enable --runtime` did nothing; I added one) (`raw/a3-red.txt`), then passed. `tests/test_inplace_worker.py` `test_unchanged_enablement_passes_and_a_changed_one_is_refused` and `VerifyRestartTests.test_changed_enablement_is_refused`.
- Commit: `6ed9e263`.

### A8: memory provider after restart

- Changed: `host_configuration.check_memory_provider(before, after, *, owned)` in the `check_preserved` style. `verify_restart` reads `config.yaml` after the restart and calls it with `owned=selected['fresh']`.
- Tests: `tests/test_host_configuration.py` `test_memory_provider_must_not_change_unless_the_operation_owns_it` failed first with `ImportError` (`raw/a8-red.txt`); `VerifyRestartTests.test_changed_memory_provider_is_refused_unless_fresh`.
- Commit: `6ed9e263`.

### A4: `hermes lifeos-version` reports host drift

- Changed: `lifeos_hook_bridge/release_version.py` `host_status(profile)`; `status()` adds `host`. Without a record: `None`. With a record: `{state: installed|host_drift, source, changed: [paths]}`; each recorded file is opened with `O_NOFOLLOW` and hashed, so an edit, a deletion, or a symbolic link is drift. A malformed, group-writable, or path-escaping record gives `{state: host_drift, reason: '<defect>: <path>.'}`. The bridge does not import the manager. `release_plan.verify_runtime` (the worker's fresh `lifeos-version` run after publication) refuses `host_drift`.
- Tests: `tests/test_release_version.py` `HostDriftTests` (4 tests) failed first with `KeyError: 'host'` (`raw/a4-red.txt`). `tests/test_inplace_worker.py` `VerifyRuntimeTests.test_host_drift_is_refused_with_the_changed_paths` failed first with `ReleaseRejected not raised` (`raw/a4-runtime-red.txt`); it runs a real launcher script.
- Commit: `f7d302bf`.

### A5 and A6: review lists files, keys, update difference, known conflicts

- Changed:
  - `inplace_plan.update_difference(record, entry)` returns `{added, changed, restored}` or `None` for a first installation. `inplace_plan.review_changes(job, entry, record, current, generated)` publishes `job/inplace-review.json` with every `changed_paths` key between the current and the generated `config.yaml` (dotted, nothing excluded) and the update difference.
  - `release_worker._program_plan` calls `review_changes` for format 2 right after it writes `generated/config.yaml`.
  - `dashboard/plugin_api.inplace_review(job, selected, value, plan)` reads `inplace-review.json` with `read_private` and returns `hermes.files.{modified, added}` (the counts stay), `configuration`, `update`, and `known_conflicts` from the entry.
  - `dashboard/dist/index.js` `inPlaceReview`: collapsed `<details>` lists for changed files, added files, configuration keys, and each non-empty update list; a sentence with the update counts; a caution block for known conflicts, or "Known conflicts: none reported for Hermes <label>."
- Tests: `tests/test_inplace_plan.py` `ReviewTests` (2 tests) failed first with `ImportError` (`raw/a1-plan-first.txt`). `tests/test_release_dashboard.py` `InplaceReviewTests` failed first with `TypeError` (`raw/a5-api-red.txt`). `tests/test_release_ui.cjs`: the extended review test and the new update-review test failed first (2 failing, observed in the terminal; I did not save that run to a file) and pass now; the final Node run is in `raw/final/node-cjs.txt` (67 pass).
- Commit: `798fd606`.

### A1 (with Standards 4): unit tests for the plan and the worker

- `tests/test_inplace_plan.py` (14 tests). A real job is built from this repository's bridge and manager, a disposable Git checkout, a real `INTEGRATION.json` and certificate, staged files, and a preview. Covers `inspect_inplace` refusals: changed package, archive, runtime path, preview, new host commit, host edit, host record created after preparation, changed dependency lock, changed staged patched and original files. The unchanged job passes every host check and stops at the LifeOS candidate check, which needs a real LifeOS tree. `host_entries` for a first installation (patched files, retained originals, record, hold) and an update (dropped targets return to originals or absence).
- `tests/test_inplace_worker.py` (21 tests): `_rollback` order with a real `ProgramTransaction` over real files (stop services, mount, programs, `daemon-reload`, dependencies, resume), the recorded dependency-restore failure, `clear_bytecode`, `inventory_snapshot` with `check_inventory`, `_consumers_stopped` with detached real processes (a reviewed dashboard is stopped; a remaining `chat` process refuses after the 15 s wait), `verify_registration` with a synthetic unit that writes a real receipt through the copied bridge's `registration.py`, `check_restarted`, `check_enabled`, `verify_restart`, `verify_runtime`. `_systemctl`, `synchronize`, and the `ProfileServices` object are replaced only in the rollback test.
- Seam: `verify_registration` takes `unit=` (default `hermes-gateway.service`) so the test can use a synthetic unit.
- `tests/test_release_manager_cli.py` `PreparationErrorTests` (3 tests) for `cli._preparation_error`.
- `tests/test_integration_release_build.py` (3 tests): two builds from a disposable Git copy of this repository give identical records and archive bytes; members sorted with mtime 0 and uid/gid 0, no bytecode; `INTEGRATION.json` fields; a dirty tree is refused. Only `install_source.prepare_lifeos` (the LifeOS network fetch) is replaced.
- These are characterization tests of existing code, so most passed on first run. The ones that went red are listed under their items above.
- Commits: `798fd606` (plan tests), `4dc879e5`, `747884d0`.

## Final test run

Command as given in the task, one file at a time (`raw/final/summary.txt`, full outputs beside it):

| File | Tests | Result |
| --- | --- | --- |
| test_inplace_preparation | 22 | OK |
| test_inplace_removal | 12 | OK |
| test_inplace_services | 8 | OK |
| test_inplace_plan | 14 | OK |
| test_inplace_worker | 21 | OK |
| test_host_compatibility | 38 | OK |
| test_host_compatibility_manifest | 13 | OK |
| test_host_capabilities | 9 | OK |
| test_host_configuration | 5 | OK |
| test_host_record | 6 | OK |
| test_host_patches | 7 | OK |
| test_host_catalog_hooks | 1 | OK |
| test_host_command_policy | 1 | OK (1 skipped, existing) |
| test_bridge_registration | 6 | OK |
| test_release_accounts | 8 | OK after the test update; first run 2 errors (see C2) |
| test_memory_workflow_failures | 5 | OK |
| test_removal_configuration | 8 | OK |
| test_integration_package | 6 | OK |
| test_integration_release_build | 3 | OK |
| test_release_version | 12 | OK |
| test_release_dashboard | 8 | OK (1 skipped, existing: needs an actual prepared fresh operation) |
| test_release_manager_cli | 12 | OK |
| test_release_stage | 16 | OK |
| test_release_catalog | 10 | OK |
| test_mount_transaction | 28 | OK |
| test_release_configuration | 9 | OK |
| test_release_operation | 18 | OK (2 skipped, existing) |
| test_release_fresh | 5 | OK (5 skipped, existing) |
| test_profile_services | 21 | OK (79 s, real user units) |
| Node `tests/*.cjs` | 67 | pass |

`test_child_research_auth` was not run, and its tracked JSON file is unmodified. No synthetic user units were left in `/run/user/<uid>/systemd/user/`.

## Not done, and not tested

- Not tested: the call sites inside `inplace_worker._run` (the `drained` timestamp, `services.resume()` result, the `verify_restart` call) and the whole `_run` apply, recover, and restore state machine. `_run` needs a full prepared job with a real LifeOS tree, native initialization, and the mount. Only the container runs cover it, and the container runs predate these commits.
- Not tested: the preparation call of `probe_capabilities` in `prepare_inplace`, and the `review_changes` call in `release_worker._program_plan`. Both functions are tested; their call sites are not.
- Not tested: `verify_registration`'s 90 s "no receipt" timeout path.
- Not done: the docs, design text, `CONTRIBUTING.md`, and smell refactors, as instructed. The design sections 4.1, 7, 8, and 9 do not yet mention `inplace-review.json`, `unsupported_interpreter`, `invalid_host_record`, the `host` block of `lifeos-version`, or the manifest's `python`, `capabilities`, and `known_conflicts`.
- Not done: no release rebuild. The shipped manifest changed, so any candidate archive must be rebuilt and recertified.
- Not committed: this report and `raw/`. The primary agent decides whether to commit them.

## For Adrian's review

1. Riskiest: `check_restarted` compares `/proc/<pid>/stat` start ticks with `CLOCK_BOOTTIME` ticks read right after the drain. A unit restarted within the same 10 ms tick would be refused. In practice publication and dependency synchronization take seconds, but this has not run on a real host.
2. The interpreter check uses the running interpreter's major.minor. In a managed-to-in-place transition the dashboard runs the managed runtime's Python (3.14.7 on development and daily per `docs/verification/2026-10-17-host-compatibility/`), not the stock checkout's environment. Both are 3.14 today, so the transition is not refused, but the detector checks the managed Python there. The preparation probe checks the real host interpreter.
3. Decisions I made: `unsupported_interpreter` maps to the existing state `unsupported_version` (no new page state); `known_conflicts` is a list of plain sentences; configuration keys are listed as dotted paths without values (values can hold secrets); `verify_runtime` now refuses `host_drift` (an addition beyond the bridge reporting).
4. A job prepared by an earlier rc manager has no `inplace-review.json`; the current dashboard review of such a job returns the generic 409. I did not add a fallback (that would be backward compatibility, which needs your approval).
5. Changed assertion: `test_release_accounts` stop point (C2). No test was deleted.
6. No changes outside Git.
