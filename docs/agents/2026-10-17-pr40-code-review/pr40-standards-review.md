# PR 40 standards review

- Date: 2026-10-17
- Role: standards reviewer
- Question: Where does PR 40 ("0.8.0 rc1", branch `feature/minimal-install-review`, `origin/main...HEAD`, origin/main = 06ea5746) break this repository's documented standards, and which baseline smells does it show?
- Model: Claude Opus 5.5 (claude-opus-5-5)
- Scope: `lifeos_hook_bridge/`, `optional/lifeos_release_manager/` (including `dashboard/`), `scripts/`, `tests/`. I left out `docs/agents/**`, `docs/verification/**`, and `host-compatibility.json`.
- Standards read: `CONTRIBUTING.md`, `docs/codebase.md`, `~/.claude/skills/coding-rules/SKILL.md`, `references/javascript.md`.
- Raw data: `pr40-standards-code.diff` (the `-U0` code diff I reviewed), `pr40-standards-diffstat.txt`.

## Checks that passed

- ABOUTME headers: all 29 new code files have the two-line `ABOUTME:` header. All modified `.py`/`.js`/`.cjs` files keep theirs.
- Version declarations: `VERSION`, both `plugin.yaml` files, and both dashboard `manifest.json` files all read `0.8.0-rc.1` (CONTRIBUTING "Release changes").
- Patch copies: `hermes-update-hold.patch` is byte-identical in `patches/` and `lifeos_hook_bridge/patches/`. The PR also fixes the old lifecycle-patch mismatch. Both copies are now identical (on main they were not).
- Mocks: tests mostly use real temporary Git repositories, real files, and real subprocesses. The few `mock.patch` uses are component-level (`_systemctl`, a stub `hermes_cli` module), not end-to-end. That is allowed.

## (a) Breaches of documented standards

### Hard

1. **History comment.** `optional/lifeos_release_manager/cli.py:143`
   `"""Prepare a format 1 complete-runtime release. Commands no longer call this preparation."""`
   Rule: coding-rules SKILL.md, "Code comments": "Never write comments about what used to be there, what changed, or when". The comment also confirms that `_prepare_managed_package` is dead code: `grep` finds no caller. Either delete it (that needs Adrian's approval under "Never throw away ... an implementation") or describe what it does without the history.

2. **Guides now contradict the code.** The PR makes the two lifecycle patch copies identical and marks the TODO done. But two guides still say they differ:
   - `CONTRIBUTING.md:55`: "The documentation audit finds one existing mismatch between the two lifecycle patch copies..."
   - `docs/codebase.md:31`: "Their lifecycle patch bytes currently differ"
   Rule: CONTRIBUTING "Make a bounded change": "Keep source, patch copies, declarations, and relevant guides consistent."

3. **The codebase map is missing the new modules.** `docs/codebase.md` was not edited. Its "Complete release flow" table and its test table do not name `host_compatibility`, `host_record`, `host_patches`, `host_configuration`, `inplace_plan`, `inplace_preparation`, `inplace_worker`, `inplace_services`, `inplace_removal`, `integration_package`, `consumer_scan`, `dependency_plan`, or `lifeos_hook_bridge/registration.py`. They also leave out the new `scripts/build_integration_release.py`. The new builder is not in CONTRIBUTING's "Release changes" either, which still documents only `build_managed_release.py`. Same rule as item 2. The user-level AGENTS.md README rule points the same way.

4. **New behavior has no tests.** Rule: CONTRIBUTING "Add regression tests for behavior changes"; coding-rules "Tests cover all functionality." `grep` over `tests/` finds no test for:
   - `inplace_worker.run` / `_run`: the in-place apply, recover, restore, and rollback state machine. Only `check_inventory` and `check_receipt` are tested.
   - `inplace_worker.verify_registration`, `clear_bytecode`, `inventory_snapshot`, `_consumers_stopped`, `_rollback`.
   - `cli._preparation_error`: the new owner-facing failure text.
   - `scripts/build_integration_release.py`, which builds the release archive (reproducible tar, manifest).
   - `scripts/local_release_server.py`. This is a qualification tool, so a gap here matters less.
   Installed qualification evidence may cover `_run`. CONTRIBUTING says component, native, and installed evidence are separate layers, so the component tests still have this gap.

### Judgement calls

5. **Floating promise.** `dashboard/dist/index.js`, effect body: `checkCompatibility();` is neither awaited nor returned. `references/javascript.md` says "Await or return every promise." That reference is keyed on `package.json`, and this repo has none. The call also matches the existing `poll();` beside it. Unlike `poll`, though, `checkCompatibility` does not check the `active` flag, so it can call setState after the component unmounts.

6. **`argparse.ArgumentParser(description=__doc__)`** in `scripts/build_host_compatibility.py` and `scripts/local_release_server.py`. These files use ABOUTME comments and have no module docstring, so `__doc__` is `None` and `--help` shows no description. Rule: match surrounding style. `build_integration_release.py` passes an explicit string.

## (b) Baseline smells (all judgement calls)

### Repeated Switches / Shotgun Surgery: request format
`request.get('format') == 2` appears 6 times in `release_worker.py`, 2 times in `release_plan.py`, and once each in `cli.py` and `dashboard/plugin_api.py`. The removal side branches on the same thing under three other spellings: `'host' in plan` (removal_workflow, removal_publication), `runtime.get('kind')!='host'` / `=='host'` (memory_workflow, removal_preparation), and `if inplace` (removal_preparation, about 6 branches). Adding a third operation kind would mean editing all of these places. One per-format strategy object, or one dispatch map, chosen once in `release_worker`/`release_plan`, would gather the branches into one place.

### Data Clumps: `units` and `roles`
`roles=None if units is None else tuple(units)` is repeated in `memory_transition.py`, `ownership_setup.py`, `removal_preparation.py`, `removal_publication.py`, and `removal_workflow.py`. Two more call sites pass `roles=tuple(self.units)`. `ProfileServices` could derive `roles` from `units` when only `units` is given.

### Duplicated Code
- Process start time, `/proc/<pid>/stat` field 19: `lifeos_hook_bridge/registration.py:_start_time` and `consumer_scan.py:start_time` are identical. `inplace_services.ancestors` parses the same file again. The two plugins are separate, so a copy in each may be deliberate. Inside the manager, it should exist once.
- Opening an owner file safely (`os.open(... O_NOFOLLOW|O_NONBLOCK)` + `fstat` + `S_ISREG` + uid/mode check): `host_record.load_record`, `host_record.check_originals`, `host_compatibility._file_digest`, `host_patches._read_original`.
- SHA-256 helpers: `_digest` in `dependency_plan.py`, `host_patches.py`, and `scripts/build_host_compatibility.py`; inline `hashlib.sha256(...).hexdigest()` in `integration_package.py` and `build_integration_release.py`; and `release_stage.sha` already exists and is used in other places.
- Tree hashing that skips `__pycache__`/`.pyc`: `integration_package.file_map`, `inplace_worker._tree_digest`, `build_integration_release._archive`.
- `host_compatibility.inspect_host` / `_installed_reasons`: the modified/untracked/hidden reason blocks, the `dependency_conflict` block, and the `git_unavailable` reason are each written twice or three times. `reasons.extend([shared] if shared else [])` appears 3 times.
- `cli._prepare_managed_package` and `_prepare_inplace_operation` share the same tail: `prepare_plan`, the status check, and the return dict with its `next` string.
- The "loaded with a FragmentPath" unit check is in both `inplace_services.inventory` and `profile_units`. `inplace_worker.verify_registration` parses `systemctl show` output again by hand.
- `CREATED_UNITS` in `inplace_worker.py` is a subset of `inplace_services.UNITS`.
- Launcher validation (`.hermes/bin/hermes`, is_symlink/is_file/X_OK) appears in both `inplace_preparation.host_launcher` and `inplace_removal.runtime`.
- `'XDG_RUNTIME_DIR': '/run/user/' + str(os.getuid())` appears in both `inplace_preparation.resolve_dependencies` and `inplace_removal.synchronize`.
- `REPOSITORY = '0ut5ider/lifeos-hermes-plugin'` appears in both `scripts/local_release_server.py` and `release_catalog.py`. The `'lifeos-hook-bridge'` literal in `host_compatibility._bridge_enabled` duplicates `dependency_plan.BRIDGE`.
- The process-list message `item['command'] + ' (' + str(item['pid']) + ')'` is built 3 times (inplace_plan, inplace_worker, removal_preparation).
- `services is not None and services.status()['state'] != 'none'` appears in `_quiesce`, `_resume`, `adopt_units`, and `_run`.

### Feature Envy / reaching into private members
- `programs._load()['entries']` (the private method of `ProgramTransaction`) is called from `inplace_worker._run` (twice) and `removal_publication._host_files`.
- Private helpers are imported across modules: `_entry` and `_relative_path` (host_record from host_compatibility), `_json` and `_environment` (inplace_preparation), and `_fresh_native`, `_restore_mount`, `_revoke`, `_program_plan` (inplace_worker from release_worker). If other modules use these helpers, they should be public.
- Private upstream APIs are used: `pm.workspace._generate_pyproject` (dependency_plan) and `hermes_cli._launchers` (inplace_removal). The pinned upstream contains this risk, but nothing marks these call sites as depending on internals.

### Mysterious Name
- `inplace_worker._run`, rollback branch: `current = (profile / 'config.yaml').read_bytes()` rebinds the parameter `current`, which holds the bridge module, to configuration bytes. The code works, but it misleads the reader.
- `inplace_plan.host_entries`: `patched = {relative: value for relative, value in selected['staged'].items()}` is an identity copy with a name that does not match its contents (it holds both stock and patched).

### Speculative Generality
- `cli._prepare_managed_package` has no caller (see item 1).
- `_run(..., release_update=lambda: None)`: the only caller always passes the argument.
- `dashboard/plugin_api.inplace_review` returns `'update_hold': True` as a constant, and the UI branches on it.

### Long function (outside the baseline list)
`inplace_worker._run` (about 130 lines) and `inplace_plan.inspect_inplace` (about 90 lines) each mix several concerns. Splitting them also makes item 4 easier to test.

## Not flagged
- "new" in `hermes_cli/new_hook.py` fixtures, in "its new user service replaces it" (UI), and in `test_new_entry_targets_receive_their_patched_files`. In each case "new" names a domain fact, not code history.
- Function-local imports. The surrounding release-manager code uses this pattern widely.
- Compact one-line style in `removal_*.py` and `memory_workflow.py`. The edits match the file style.

## Round 2

- Date: 2026-10-17. Role: standards reviewer. Model: Claude Opus 5.5 (claude-opus-5-5).
- Question: Are the round 1 findings resolved at 9f1749d3, and did the fix commits (`git log 90d1bf7f..HEAD`, 36 commits) add new findings?
- Inputs read: `round1-fix-plan.md`, `pr40-fixes-phase1.md`, `pr40-fixes-phase2.md`, and the code diff `90d1bf7f..HEAD`. I copied the diff to `~/agent-scratch/pr40-standards/r2.diff`; it is not committed.
- I did not rerun the test suites. I relied on the phase reports for test results and spot-checked the code.

### Round 1 findings

| # | Finding | Status |
| --- | --- | --- |
| 1 | History docstring in `cli._prepare_managed_package` | Resolved. The docstring now describes the function. Keeping the function is accepted: design section 11 keeps the managed path until the transition, and deletion needs owner approval. |
| 2 | Guides said the lifecycle patch copies differ | Resolved. `CONTRIBUTING.md:55` and `docs/codebase.md` now say the copies are byte-identical and that `test_patch_bundle.py` checks it. |
| 3 | Codebase map was missing the new modules and builders | Resolved. `docs/codebase.md` has an in-place stage table and test rows. `CONTRIBUTING.md` "Release changes" names both new builders and `local_release_server.py`. |
| 4 | New behavior has no tests | **Not resolved (partial).** `_rollback`, `verify_registration`, `clear_bytecode`, `inventory_snapshot`, `_consumers_stopped`, `_preparation_error`, the integration builder, and the release server now have tests. `inplace_worker._run` still has none, and the fix plan said to test "`_run` paths". The fix commits changed `_run`: they added the `drained = boot_ticks()` timestamp, `services.resume()['services_started']`, the `verify_restart` call, `record_restored`, and a required `release_update`. The phase 1 report says the container runs that exercised `_run` predate these commits. So no layer of evidence (component, native, or installed) covers the current `_run` wiring. This breaches CONTRIBUTING "Add regression tests for behavior changes" and the layer rule ("Report which layer ran"). Remedy: either rerun installed or container qualification at the current head, or add a test of the apply path through `_run` that uses real units, as `VerifyRestartTests` already does. |
| 5 | `checkCompatibility` floating promise and missing `active` guard | Resolved. `checkCompatibility(isActive)` checks the guard before each state update. A Node test covers it. A "Check again" click that is followed by an unmount is still unguarded, which matches the other click handlers. |
| 6 | `argparse(description=__doc__)` | Resolved. Both scripts pass an explicit description. |
| Smell | Format 1/format 2 switch | Accepted; the reason holds. Design section 11 removes format 1, so a strategy object would serve one remaining branch. |
| Smell | `units`/`roles` clump | Resolved. `ProfileServices` derives `roles` from `units`. No `roles=None if units...` call site remains. |
| Smell | Duplicates: start time, SHA-256 helpers, tree hashing, reason blocks, `_prepare_*` tail, `CREATED_UNITS`, `XDG_RUNTIME_DIR`, process-list message, services-status check, launcher check, bridge name | Resolved. Accepted copies with reasons that hold: `registration._start_time` (the bridge runs without the manager), `dependency_plan._digest` (it runs as a standalone script under the host interpreter), and `local_release_server.REPOSITORY` (the script is copied standalone; `test_local_release_server.py` pins it to `release_catalog.REPOSITORY`, and the copied script runs with `-I`). |
| Smell | Owner-file safe open (4 copies) | Accepted; the reason holds. Only three lines are shared, and the checks and error mapping differ at each site. |
| Smell | Feature Envy: `programs._load()` and private helpers used across modules | Resolved. `ProgramTransaction.entries()` and public helper names replace them. |
| Smell | Private upstream APIs | Accepted. Every call site has a comment that names the pinned Hermes v0.21.7. |
| Smell | `current` rebinding, identity copy `patched` | Resolved (`record_restored`; `selected['staged']` is used directly). |
| Smell | Speculative: `release_update` default, constant `update_hold` | Resolved. `_prepare_managed_package` is accepted, as in item 1. |
| Smell | `verify_registration` parses `systemctl show` by hand | Accepted. It treats a non-zero exit as "the gateway does not run", which differs from `_show`. |
| Smell | Long `_run`, `inspect_inplace` | Accepted as a judgement call. They were not split, but no standard requires a split. |

### New findings from the fix commits

N1. **Duplicated Code (judgement call).** The fix commits add `inplace_worker._show(unit, *properties)`, which repeats `inplace_services._properties(unit)`. Both run `systemctl --user show`, refuse a failure with `ReleaseRejected`, and parse `key=value` lines. The differences are a fixed property list and a stderr check. The manager now has three parsers for `systemctl show`. `_properties` could call `_show(unit, 'LoadState', ...)`, or the two could share one helper.

Not counted:
- `lifeos_hook_bridge/release_version.py` adds `host_status`, `_host_record`, and `_digest`. These partly repeat `host_record.validate_record` and `host_compatibility._file_digest`. The bridge does not import the manager, which is the same accepted reason as `registration._start_time`. The bridge validator is looser, since it checks only `source` and `files.*.patched`. That is enough for a drift report, and it fails closed to `host_drift`.
- `verify_restart` has 9 parameters (a long parameter list). This is a judgement call and not on the baseline list.
- `inplace_worker.OWNED_PLUGINS` duplicates `removal_configuration.PLUGINS`. This came from the original PR, not from the fix commits; I missed it in round 1. The phase 2 report records it.
- New files have their ABOUTME headers. The fix commits add no history words in comments. `git diff --check` finds whitespace only in `docs/agents/**` evidence patches.

VERDICT: NOT CLEAN (2 open findings)

## Round 3

- Date: 2026-10-17. Role: standards reviewer. Model: Claude Opus 5.5 (claude-opus-5-5).
- Question: Are round 2 item 4 and N1 resolved at c5ed49b3, and do the commits since 5d357559 add any new standards finding?
- Commits reviewed: 39da38e4, cc799e17, 150ff808, b9add026, 112fd02d, 071ebf20, 7d76fc6c, c5ed49b3.

### Round 2 open findings

| # | Status |
| --- | --- |
| 4: `inplace_worker._run` untested at the current head | **Resolved.** `docs/verification/2026-10-17-inplace-e2e/README.md` ("Final regression on `7d76fc6c`") records installed runs on real containers with user systemd: the transition and its restore on 114, and in-place updates on 112 and 110. Each run ends with a patched registration receipt from the stock checkout. I checked that `git diff 7d76fc6c..HEAD` changes only that README, so the qualified build has the same code as HEAD. All code commits since round 2 (39da38e4, b9add026, and the reverted pair) come before 7d76fc6c. These runs exercise the `_run` wiring end to end. CONTRIBUTING treats installed evidence as its own layer, and component tests cover the parts. I did not rerun the containers myself. |
| N1: duplicate `systemctl show` parsers | **Resolved.** `inplace_services.show(unit, *properties)` is now the single parser. `_properties` and the worker checks both call it, and `show` keeps the stricter stderr check. `OWNED_PLUGINS` now imports `removal_configuration.PLUGINS`. `verify_registration` still parses the output by hand, which round 2 accepted. |

### Commits since 5d357559

- cc799e17 and 150ff808 are reverted by 112fd02d and 071ebf20. `git diff cc799e17~1 071ebf20` leaves only the b9add026 change, so the reverts leave nothing behind.
- b9add026 (`ProfileServices._load`): when the journal names another role set, a completed (`active`) journal now counts as absent, and any other state still refuses. The comment describes current behavior. Two tests with real units cover both branches. It is the smallest change that does the job. No finding.
- 7d76fc6c and c5ed49b3 change only the docs: the TODO entry, the design limit, and the evidence. 7d76fc6c records the reinstall limit in TODO.md, as CONTRIBUTING requires for unfinished product work.

No new findings.

VERDICT: CLEAN
