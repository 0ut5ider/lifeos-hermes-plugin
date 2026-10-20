# PR 40 fixes, phase 2

- Date: 2026-10-17
- Role: implementation engineer (subagent), branch `feature/minimal-install-review`, commits only, no push, no remote host
- Question: implement round 1 fix plan items Standards 1, 2, 3, 5, 6, the Smells row, the design text amendments (C3, C4, C6, A4, A8, A9, B1, phase 1 additions), and the CHANGELOG check.
- Model: Claude Opus 5.5 (`claude-opus-5-5`)
- Raw data: `raw/baseline/` (full run before any change), `raw/<item>-before|red/` and `raw/<item>-after|green/` per refactor, `raw/final/` (final run, `summary.txt`, `node-cjs.txt`, `node-check.txt`, `list.txt`), `raw/*-at-5dd731c0.txt` (pre-existing failures reproduced at the phase 1 head).

Base: `5dd731c0` (phase 1 head). 22 commits, oldest first:

| Commit | Subject |
| --- | --- |
| `703452b3` | docs(cli): describe the managed preparation |
| `272a990c` | fix(scripts): describe two release scripts in help |
| `19df1267` | fix(dashboard): skip a late compatibility result |
| `8c18ee2b` | docs: map the in-place modules and builders |
| `7af8a31f` | refactor(programs): read journal entries publicly |
| `7fc7272c` | refactor(worker): record a rollback configuration |
| `8657b6fa` | refactor(manager): read process records in one place |
| `2c7238ad` | refactor(worker): derive created units from UNITS |
| `76b4965c` | test(preparation): admit the host before download |
| `2e2f7aa1` | refactor(plan): use the staged files directly |
| `fcd99762` | refactor(worker): name the drained services check |
| `bce5d0ae` | refactor(release): hash files and trees one way |
| `52693db6` | refactor(release): name the runtime directory once |
| `e0b86c6a` | refactor(compatibility): build each reason once |
| `51c80537` | refactor(cli): share the end of both preparations |
| `c1e2538e` | refactor(review): drop the constant update hold flag |
| `41587e02` | refactor(services): derive roles from the units |
| `df6514df` | refactor(manager): make shared helpers public |
| `dc53953c` | docs(code): mark the private Hermes APIs in use |
| `e10a0d00` | refactor(in-place): share unit and launcher checks |
| `e03f5f77` | docs(design): match the in-place design to the code |
| `1cc14cc6` | docs(changelog): list the review fixes for 0.8.0 |

## Per item

### 1. Standards 1: `_prepare_managed_package` docstring

`cli._prepare_managed_package` docstring is now "Prepare a format 1 release that publishes a complete managed runtime beside the profile." The function stays (design section 11). Commit `703452b3`.

### 2. Standards 2 and 3: guides

- `CONTRIBUTING.md`: the patch-copy paragraph says the copies are byte-identical and `tests/test_patch_bundle.py` checks it (verified: that test compares every declared patch in both directories; `cmp` of all files in `patches/` and `lifeos_hook_bridge/patches/` shows no difference). "Release changes" gains the `build_host_compatibility.py` and `build_integration_release.py` commands and a paragraph on each plus `local_release_server.py`; the existing builder is now named "the managed-runtime builder".
- `docs/codebase.md`: patch-copy sentence fixed; bridge `registration.py` row; a new in-place stage table (all 14 manager modules plus `host-compatibility.json` and `stock_hermes.py`); builder paragraph; five test rows for the in-place tests.
- `docs/clean-install.md` line 5 also claimed the copies differ. I rewrote it as a "Patch copies" note that keeps the history pointer to the TODO item.
- `docs/README.md`: the in-place row now also links the design.
- All relative links resolve (checked with a script). No em dashes.
- Commit `8c18ee2b`. No tests (documentation).

### 3. Standards 5 and 6

- `dashboard/dist/index.js`: `checkCompatibility(isActive)` skips both state updates when the page is gone; the effect passes `function () { return active; }`, like `poll`. The "Check again" button calls `check()` without the event. New Node test `a compatibility result that arrives after the page closes changes no state` failed first (`raw/s5-red.txt`), passes now (`raw/s5-green.txt`). Commit `19df1267`.
- `scripts/build_host_compatibility.py` and `scripts/local_release_server.py` pass explicit `argparse` descriptions; `--help` checked by hand. Commit `272a990c`.

### 4. Smells

Each refactor ran the affected test files before and after; characterization tests were added first where the changed path had no coverage.

| Smell | Change | Tests | Commit |
| --- | --- | --- | --- |
| `programs._load()['entries']` | `ProgramTransaction.entries()`; callers in `inplace_worker`, `release_worker` (2), `removal_publication` (2), `removal_ownership`, `removal_preparation`, `check_plan`, two tests | New `test_entries_lists_the_reviewed_targets_and_refuses_a_substituted_journal` (red: `AttributeError`, `raw/programs-red/`) | `7af8a31f` |
| `current` rebinding in `_run` | New `host_configuration.record_restored(profile)`; the restore branch calls it | New `test_a_rolled_back_configuration_becomes_the_installed_value_of_each_recorded_path` (red: `ImportError`) | `7fc7272c` |
| Start-time parsing, process-list message | `consumer_scan.stat_fields`, `start_time`, `parent`, `process_names`; `inplace_services.ancestors` and `release_operation.process_stamp` use `stat_fields`; plan, worker, removal preparation use `process_names`. The bridge keeps `registration._start_time` with a one-line comment (it runs without the manager) | New `ProcessIdentityTests` (2 tests) | `8657b6fa` |
| `CREATED_UNITS`, unused `release_update` default | `CREATED_UNITS = {role: UNITS[role] for role in OFFERABLE}`; `_run(..., release_update)` required | New `CreatedUnitsTests` pins the value | `2c7238ad` |
| Identity-copy `patched` | `host_entries` reads `selected['staged']` (checked: `desired_host_files` does not mutate it) | `test_inplace_plan` covers first install and update | `2e2f7aa1` |
| Services bound and journal present | `inplace_worker._journaled(services)` in `adopt_units`, `_quiesce`, `_resume`, `_run` | New rollback test without a drain journal (passes before and after) | `fcd99762` |
| SHA-256 file hashing, tree hash | `release_stage.sha` in `host_patches`, `integration_package`, both builders; `integration_package.source_paths` for `file_map`, `inplace_worker._tree_digest`, `build_integration_release._archive`. `dependency_plan._digest` stays with a comment: the host interpreter runs that file as a standalone script | New `FileMapTests` and `PluginDigestTests` (bytecode ignored, link and file changes detected); `test_integration_release_build` checks archive reproducibility; the shipped-manifest rebuild test passes | `bce5d0ae` |
| `XDG_RUNTIME_DIR`, `REPOSITORY`, bridge name | `release_stage.user_runtime_directory()` in `cli`, `release_plan`, `inplace_removal`, `inplace_preparation`; `local_release_server` imports `REPOSITORY` from `release_catalog` (manual check of `payloads()` routes in `raw/local_release_server-manual-check.txt`); `_bridge_enabled` uses `dependency_plan.BRIDGE` | New `UserRuntimeDirectoryTests` | `52693db6` |
| Duplicated reason blocks in `inspect_host` | `_git_unavailable`, `_tree_reasons`, `_dependency_reasons`, `_present` | 4 new tests pin order, text, and paths of every reason on both paths and each `git_unavailable` exit (passed before the change, `raw/inspect-before/`) | `e0b86c6a` |
| Shared tail of the two `_prepare_*` | `cli._ready_operation` | New `PreparedOperationTests` (ready, refused) through `_prepare_inplace_operation` | `51c80537` |
| Constant `update_hold: True` | Removed from `plugin_api.inplace_review`; the UI always shows the hold sentence for an in-place review | Node fixtures updated; dashboard test asserts the key is absent (red first, `raw/hold-red/`) | `c1e2538e` |
| `roles`/`units` clump | See below | | `41587e02` |
| Cross-module private helpers | `parse_json`, `owner_directory`, `validate_entry`, `validate_relative_path`, `stage_environment`, `initialize_native`, `restore_native_mount`, `revoke_authorization`, `program_plan`, `parse_configuration`, `workflow_job`, `write_workflow_state`, `run_transition_probe`, `check_consumers`; every caller, including `plugin_api`'s `commands._json` (found by a separate attribute search) and 5 test files | Full removal, release, in-place, dashboard sets | `df6514df` |
| Private upstream APIs | Comment at each of the 11 imports of `hermes_cli._launchers` and `pm.workspace._generate_pyproject` (bridge and manager). Verified both exist in stock v0.21.7 | n/a | `dc53953c` |
| Unit-loaded check, launcher check | `inplace_services._loaded`; `inplace_removal.runtime` uses `host_launcher` and keeps its message; removed unused imports in the in-place modules | Strengthened `test_runtime_requires_the_host_source_launcher` (non-executable, link, missing source) | `e10a0d00` |

**`roles` derived from `units`.** `ProfileServices.__init__` now sets `roles = tuple(units)` when `roles is None` and `units is not None`, after the dict check and before the roles validation. That is exactly the expression every caller computed, so an empty or unknown role still refuses with "distinct known roles". The five call sites (`removal_publication`, `removal_workflow`, `removal_preparation`, `memory_transition`, `ownership_setup`) and the two `roles=tuple(self.units)` sites now pass only `units`. The journal format is unchanged. New test `test_units_without_roles_bind_exactly_the_roles_they_name` failed first (`raw/roles-red.txt`). `test_profile_services` (22, real units), the memory transition, ownership, return, and removal suites pass.

**Owner-file safe open: left.** The four copies differ in checks: `host_record.load_record` requires regular file, owner uid, no group/other write, and at most 2 MB; `check_originals` requires regular, owner, no group/other write, no size bound; `host_compatibility._file_digest` requires only a regular file and maps errors to `None`/`'unreadable'`; `host_patches._read_original` requires only a regular file and returns the bytes and mode. The shared part is three lines (`os.open` with `O_NOFOLLOW|O_NONBLOCK`, `fstat`, `S_ISREG`); a helper would not remove the per-site checks or error mapping.

### Pre-existing failure fixed: `test_release_preparation`

`test_release_preparation` had 3 failures at `5dd731c0` (`raw/test_release_preparation-at-5dd731c0.txt`). I bisected by hand: it passes at `90d1bf7f` and fails at `f9bc5172` (phase 1 C2, compatibility before download). Phase 1 did not run this file. The three tests use the download as the point where they assert the held lease and the `preparing` state. I added `admitted_host()`, which replaces `inplace_preparation.check` with `{'state': 'compatible'}`, so the original download assertions run again. No assertion was removed. Commit `76b4965c`. Adrian may want to look at this, as with the phase 1 test change.

### 5. Design text

`docs/in-place-installation-design.md`: status line; section 2 (`lifeos` block without `patches`, file map binds the patches; the manifest entry fields `python`, `capabilities`, `known_conflicts`); 4.1 step 1 (check before download, `unsupported_interpreter`, `invalid_host_record`), step 7 (preview lifetime and probe), step 9 (`inplace-review.json` and review contents); 4.2 step 7 (memory provider); 4.3 (launchers unchanged outside the transition); 7 (enabled state in the plan, journal unchanged; per-unit start time and `UnitFileState`; probe details); 8 (record contents, `.lifeos-host/configuration.json`, inventory scope, `check_preserved` roots, memory authority); 9 (the three drift reports; registration writes only the receipt; no drift report compares `memory.provider`); 10 (service launcher repoint, R2-1 open for the owner); 11 (module and script lists); 13 (single-profile admission and idle foreign profiles); new section 15 maps each finding to its section. Counts are unchanged: the shipped manifest still has 96 targets, 27 added, 69 modified, 11 patch groups. No em dashes. Commit `e03f5f77`.

### 6. CHANGELOG

Unreleased gained the owner-visible phase 1 items that were missing: check before download, interpreter and damaged-record refusals, review contents, restart checks, `hermes lifeos-version` host block, removal without the hold. Phase 2 has no owner-visible behaviour change except the hold sentence (always shown, as before in practice). Commit `1cc14cc6`.

## Final test run

Command from the task, one file at a time; outputs in `raw/final/`. 75 Python files, 749 tests.

| Result | Files |
| --- | --- |
| OK | 72 files, including every file the task named: test_inplace_plan 14, test_inplace_worker 24, test_inplace_preparation 22, test_inplace_removal 12, test_inplace_services 8, test_host_compatibility 42, test_host_capabilities 9, test_host_record 6, test_bridge_registration 6, test_profile_services 22 (71 s, real units), test_release_accounts 8, test_memory_workflow_failures 5, test_removal_configuration 8, test_integration_package 7, test_release_programs 24, test_memory_transition 5, test_memory_transition_probe 3, test_memory_removal_workflow 4. Skips are the existing ones (release_dashboard 1, release_operation 2, release_fresh 5, fresh_store_dashboard 1, fresh_store_worker 2) |
| FAILED, pre-existing | `test_removal_consumers` (1 error), `test_removal_coordinator` (1 failure), `test_installation_lease` (1 error) |
| Node | `node --test tests/*.cjs`: 68 pass, 0 fail; `node --check` of both bundles: exit 0 |

`test_release_worker*.py` does not exist in this repository; I ran `test_release_operation`, `test_release_configuration`, and `test_release_fresh`, which cover `release_worker`.

The three failures are the same at the phase 1 head `5dd731c0` (`raw/removal-consumers-at-5dd731c0.txt`, `raw/test_installation_lease-at-5dd731c0.txt`) and are environmental:

```
test_removal_consumers: PermissionError: [Errno 13] Permission denied: '/proc/2145/exe'
test_removal_coordinator: {'admitted': False, 'reason': 'The account process boundary cannot be verified',
  'diagnostics': {'refused_process': 'sshd-session', 'refused_groups': ['/user.slice/user-1000.slice/session-4.scope'], ...}}
test_installation_lease: MemoryUnavailable: Ownership activation requires an available current Hermes model route
```

PID 2145 is an `sshd-session` process of this account whose `exe` link is unreadable, so the removal process scan refuses (correctly). The lease test needs a configured Hermes model route. I did not change either.

`test_child_research_auth` was not run; its tracked JSON is unmodified. `git status` shows no tracked changes. The temporary worktree `~/agent-scratch/pr40-phase2-base` is removed.

## Smells left, and why

- Format 1/format 2 branches: accepted in the fix plan (design section 11).
- Owner-file safe open: the four copies differ in checks (above).
- `inplace_worker.verify_registration` parses `systemctl show` by hand: `_show` raises on a non-zero exit with another message, while `verify_registration` treats it as "the gateway does not run". Changing it changes a refusal text.
- Long `_run` and `inspect_inplace`: the plan says split where tests need seams; no test in this phase needed one.
- `scripts/build_managed_release.file_map` duplicates `integration_package.file_map`: managed path, removed after the transition.
- `inplace_worker.OWNED_PLUGINS` and `removal_configuration.PLUGINS` hold the same three names; not flagged by the review, left.
- Pre-existing unused imports in `tests/test_release_fresh.py` (`json`) and `tests/test_release_manager_cli.py` (`subprocess`): not mine, left.

## Not tested

- `inplace_worker._run` as a whole is still untested (needs a full prepared job). Its changed lines are the `record_restored` call, `_journaled`, `programs.entries()`, `process_names`, and the renamed imports; each callee is tested, the call sites are not.
- `cli._prepare_managed_package` has no caller and no test; it now ends in `_ready_operation`.
- `scripts/local_release_server.py`: only a manual call of `payloads()`.
- The `checkCompatibility` guard after a "Check again" click followed by unmount is not guarded (the click path passes no `isActive`), same as other click handlers.
- The renamed private helpers break the historical probe scripts under `docs/agents/2026-10-1[2-5]-*` that import the old names (`_restore_mount`, `_program_plan`, `_probe`, `_consumers`). Those are dated records for older commits; I did not edit them.

## For Adrian's review

1. Riskiest: the `ProfileServices` roles derivation (`41587e02`). The removal call sites load the **installed** bridge (`profile/plugins/lifeos-hook-bridge`). With the same release on both sides, behaviour is identical. Two cross-version effects: (a) an installed bridge without the derivation (an unreleased 0.8.0-rc.1 build, for example on a qualification container) now refuses an in-place removal with "distinct fixed service bindings", because the manager no longer passes `roles`; it fails closed. (b) Before this change, those sites passed `roles=None` even for a managed host, which a 0.7.x bridge (no `roles` parameter) would reject with a `TypeError`; now they pass only `units`. I found (b) by reading code and did not test it.
2. The private-helper rename (`df6514df`) touches 20 manager files and 5 tests. I checked imports, module attribute use (`commands._json` in the dashboard API), and `mock.patch` strings.
3. `test_release_preparation` fix replaces the compatibility check with a stub in three tests.
4. Decisions I made: public names listed above; `record_restored` lives in `host_configuration`; `source_paths` lives in `integration_package`; `user_runtime_directory` in `release_stage`; `clean-install.md` and `docs/README.md` edits beyond the two named lines.
5. No changes outside Git. This report and `raw/` are not committed.
