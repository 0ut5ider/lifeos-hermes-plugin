# PR 40 spec review

- Date: 2026-10-17
- Role: spec reviewer (read-only; no tracked file changed, nothing committed)
- Question: does the diff `origin/main (06ea5746)...feature/minimal-install-review` (55 commits, PR 40 "0.8.0 rc1") implement what `docs/in-place-installation-plan.md` and `docs/in-place-installation-design.md` ask for? Report (a) missing or partial requirements, (b) scope creep, (c) requirements that look implemented but wrong.
- Model: Claude Fable 5.1

Raw data in `spec-raw/`: `spec-review-unit-tests.txt` (13 new-module test files, 129 tests, all pass, 1 skipped), `spec-review-diffstat.txt`, `spec-review-commits.txt`, `spec-review-manifest-summary.json`.

Method: read both spec documents in full, read every new module in `optional/lifeos_release_manager/` and the bridge changes, read the diff of the changed modules, and ran the new modules' unit tests with a Hermes-capable interpreter (`frozen-test-environment` python, Hermes source on `PYTHONPATH` with its `tests` package excluded, because it shadows this repository's `tests` namespace package). I did not rely on the verification README's claims; where I could not verify a claim from code, I say so.

## Summary

The core contract is implemented: read-only compatibility admission with specific refusals, pinned LifeOS fetch, verified integration package, staged host patches with retained originals, a journaled `ProgramTransaction` over the host files, Hermes update lock plus update hold, `/proc` consumer scan, environment synchronization through `pm.client.sync_venv`, patched-mode registration receipt, in-place removal from the originals, and the managed-to-in-place transition. Unit tests for the new modules pass.

Gaps are mostly in the verification and review layers, not in the transaction: no unit tests for `inplace_plan.py` or `inplace_worker.py`, no capability probe or enabled-state record after restart, drift reporting lives only in the manager's check and not in the bridge, and the review payload shows counts where the spec asks for files and configuration keys. One over-strict refusal can block removal (missing hold file). One ordering deviation (download before compatibility check). Several small design/code mismatches that the design document should absorb or the code should follow.

## (a) Requirements missing or partial

### A1. No unit tests for `inplace_plan.py` and `inplace_worker.py` (design section 12)

Spec: "Unit tests for every new module, with disposable real Git repositories and real files." (design, line 164)

Code: `tests/` has `test_inplace_preparation.py`, `test_inplace_removal.py`, `test_inplace_services.py`, `test_host_*.py`, `test_consumer_scan.py`, `test_dependency_plan.py`, `test_integration_package.py`. There is no `test_inplace_plan.py` and no `test_inplace_worker.py`. `grep -rn "inplace_worker|inplace_plan" tests/*.py` finds only indirect references in `test_inplace_preparation.py` (7) and `test_inplace_removal.py` (1). `inplace_worker.py` (378 lines: `_run`, `_rollback`, `verify_registration`, `check_inventory`, `clear_bytecode`, `_consumers_stopped`) and `inplace_plan.py` (181 lines: `inspect_inplace`, `host_entries`, `transition_launchers`) are covered only by the container runs.

### A2. No post-restart capability probe and no new-PID check (design section 7)

Spec: "After restart, the worker requires a new main PID with a start time after publication for each restarted unit. It runs `hermes lifeos-version` and a host capability probe in fresh processes. The probe checks that `VALID_HOOKS` contains the patched hooks and that `REQUIRED_MIDDLEWARE_API_VERSION == 1`." (design, line 125)

Code: `inplace_worker.py:100-129` (`verify_registration`, `check_receipt`) requires a `patched` receipt from the gateway's current `MainPID` only. `release_plan.py:140-156` (`verify_runtime`) runs `config check` and `lifeos-version`. No process probes `VALID_HOOKS` or `REQUIRED_MIDDLEWARE_API_VERSION`; `grep -rn REQUIRED_MIDDLEWARE_API_VERSION optional/` finds nothing. The receipt's `patched` mode implies `PATCHED_HOOKS <= VALID_HOOKS` inside the gateway (`lifeos_hook_bridge/__init__.py:57`), so the hook half is covered indirectly for the gateway. The middleware version is not checked anywhere in the worker. The dashboard and Pulse units get no receipt or PID check; `profile_services.py:resume` (line 317 onward) requires `ActiveState == active` and `MainPID != 0` only, with no start-time comparison. Partial.

### A3. Enabled state is not recorded (design sections 7 and 14)

Spec: "It records and restores each unit's enabled and active state." (design, line 123); review resolution "bind only existing roles; record enabled state" (line 183). Plan: "It must preserve each service's prior enabled and running state." (plan, line 67)

Code: `profile_services.py:_admission` (around line 232) records `active` and `definition` only; `PROPERTIES` (line 25) has no `UnitFileState`. `grep -n "UnitFileState|is-enabled" lifeos_hook_bridge/profile_services.py` finds nothing. Preservation holds by construction for existing units (stop and start do not change enablement), and created units are enabled and disabled explicitly (`inplace_worker.py:87-97`). The recording the design promised is absent, so a unit that was disabled-but-running before the operation is restarted but not re-recorded. Partial, low risk.

### A4. Bridge-side drift reporting is not implemented (design section 9)

Spec: "The bridge compares the host identity with `lifeos-host.json` at registration and in `hermes lifeos-version`. It also reports when the bridge is no longer enabled or `memory.provider` no longer names it ... A difference produces the state `host_drift`." (design, line 143)

Code: the only `host_drift` and `bridge_disabled` producers are in the manager, `host_compatibility.py:329-353` (`_installed_reasons`), surfaced by the dashboard compatibility section and `hermes lifeos-release compatibility`. `grep -rn "lifeos-host|host_drift" lifeos_hook_bridge/` finds nothing. `lifeos_hook_bridge/__init__.py` writes a receipt (`registration.py`) but does not compare the host with the record. The `memory.provider` check is absent everywhere. Partial: drift is detectable when the owner opens the releases page or runs the command, not at registration or in `lifeos-version`.

### A5. Review payload shows counts, not files or configuration keys (plan line 19; design section 4.1 step 9)

Spec: "The owner reviews the files, configuration keys, dependency additions, and required service interruption." (plan, line 19). "The review payload shows the Hermes version and commit, the 96 host files, the Python packages to add, the configuration keys, and the services that restart." (design, line 62). For updates: "Each action must show which components and host patches change." (plan, line 73)

Code: `dashboard/plugin_api.py:201-213` (`inplace_review`) returns `modified` and `added` counts, `packages`, `services`, and `tested_scope`. No file list and no configuration keys. For an update, the counts describe the new entry, not the difference from the installed record (`desired_host_files`, `inplace_preparation.py:139-150`, computes that difference but it is not exposed). The dashboard (`dist/index.js`, `inPlaceReview`) renders the same counts. Partial.

### A6. The page states the tested scope but reports no known conflicts (plan line 51)

Spec: "The page must state the tested scope and report known conflicts." (plan, line 51)

Code: `dashboard/plugin_api.py:196-198` `TESTED_SCOPE` is a static sentence with the label substituted. There is no known-conflict list and no mechanism to carry one in the manifest or certificate. Partial.

### A7. Manifest declares no interpreter or capability checks (plan line 30 and 45)

Spec: "Each release must declare the exact upstream revisions, supported layouts, source identities, dependency requirements, patch identities, and capability checks it qualifies." (plan, line 30). "It must check the Git revision, qualified source hashes, interpreter, installed dependency versions, and required host capabilities." (plan, line 45)

Code: `host-compatibility.json` has `format`, `hermes[{label, commit, patches, files}]`, `dependencies`; `load_manifest` (`host_compatibility.py:110-133`) rejects any other key. The interpreter is reported in `detected` (`inspect_host`, line 361) but nothing qualifies it; no capability checks are declared or run (see A2). Partial.

### A8. Inventory does not cover toolsets, MCP servers, model, or provider keys as inventory items (design section 8; plan line 47 and 69)

Spec: "the worker records an inventory: enabled plugins and their directories, configured toolsets and MCP servers, the model and provider keys, and the selected environment's package set." (design, line 139). "Verify preserved tools, plugin registrations, model configuration, and memory authority." (plan, line 69)

Code: `inplace_worker.py:161-183` (`inventory_snapshot`, `check_inventory`) records other plugins' directory digests, enabled names, and locked packages. Toolsets, MCP servers, model, and providers are protected instead by `host_configuration.py:43-48` (`check_preserved`, `PROTECTED_ROOTS`) which refuses any change under those `config.yaml` roots between before and after. That meets the intent for `config.yaml` but is not an inventory, and the review does not show a planned difference for those items. Memory authority is not checked by the in-place worker after restart. Partial; acceptable mechanism, different from the design text.

### A9. Shared-checkout detection is profile-directory based only (plan line 42)

Spec: "Shared checkout or active consumer that cannot be coordinated: refuse; explain the consumer or profile boundary." (plan, line 42)

Code: `host_compatibility.py:198-210` (`_shared`) refuses when `HERMES_HOME` is itself under `profiles/` or when `<hermes_home>/profiles/` has subdirectories. A second `HERMES_HOME` elsewhere that points at the same checkout is detected only if it has a running process (`consumer_scan.py`). Partial by design; the first supported layout is single-profile, so this is acceptable, but the page cannot name an idle foreign profile.

### A10. Acceptance step 5 and design section 12 remain open (acknowledged)

Spec: "Test the GitHub URL and actual dashboard buttons on disposable existing installations" (plan, line 90); "A disposable Proxmox container: the GitHub plugin URL, the dashboard buttons" (design, line 166); "A rehearsal of the development transition on a clone." (design, line 167)

Status: the plan itself (line 91) and `TODO.md` record these as untested. Not a code gap, but the release gate is not met.

## (b) Behaviour in the diff that was not asked for

### B1. Service launchers outside `~/.local/bin` are repointed during the transition

Design section 10 says "The transition plan points the account launchers at the stock installation" and section 4.3 says the account launchers and service definitions are not changed outside the transition. `inplace_plan.py:164-181` (`transition_launchers`, `services=` loop) and `inplace_preparation.py:70-93` (`managed_service_launchers`) additionally publish a stock forwarder into every launcher that the managed job's `plan.json` lists outside `~/.local/bin`, which on the development host is `~/workspace/hermes-agent/.hermes/bin/hermes`, a file owned by another Hermes checkout. The earlier review's R2-1 (should-fix) is still open: that checkout's own Hermes rewrites the file. This is beyond the design and should either be refused at preparation (the owner repoints two `ExecStart` lines once) or written into section 10.

### B2. Failure diagnostics: `worker-failure.json` message, `probe-output.txt`, `PROBE_CODE`, probe error type

`release_worker.py:record_failure` (adds `message` for `ReleaseRejected`), `memory_workflow.py:224-258` (probe output capture and `probe_failure`), `memory_transition_probe.py:98-102` (error class name in the message). Neither spec document asks for these; `CHANGELOG.md` lists them. They fix e2e defects 4 and 5 and are low risk, but they are new owner-visible files and a wider refusal text surface.

### B3. `removal_configuration.environment` block-boundary fix and `TRANSITION_TIMEOUT`

`removal_configuration.py:79-82` and `profile_services.py:30-33`. Both fix defects found during qualification (e2e defects 3 and 1) in modules the plan touches. In scope as bug fixes; noted because the design does not mention either.

### B4. `patches/hermes-session-lifecycle.patch` synchronized with the canonical copy

The plan asked for this ("Resolve the development patch-copy difference", line 59), so it is in scope. Noted here only because the 98-line diff in `patches/` is easy to mistake for a behaviour change; it is a copy of `lifeos_hook_bridge/patches/hermes-session-lifecycle.patch`.

## (c) Implemented but looks wrong or deviates

### C1. Removal refuses when the update hold file is missing

Spec: removal "must remove only unchanged files owned by the integration ... If the owner changes a patch target later, removal must stop and explain the conflict." (plan, line 75). Design section 8: removal "removes the hold".

Code: `inplace_removal.py:135-140` (`host_plan`) requires both `lifeos-host.json` and `<source>/.git/hermes-update-holds/lifeos.json` to exist as regular files, else `ReleaseRejected('Removal requires the LifeOS host record and its Hermes update hold')`. The hold is not a patch target and its absence does not affect source restoration. If the owner deleted the hold directory, or `.git` was re-created, removal is blocked with no repair path other than hand-recreating the hold. The spec wants removal to stop on patch-target conflicts; a missing integration-owned file should be tolerated (publish `None` over an absent target) or at least explained with a repair step. Low likelihood, high annoyance.

### C2. Preparation downloads the release before it checks compatibility

Spec: design section 4.1 step 1 "Run the compatibility check against the running Hermes. Require `compatible` ... " then step 2 "Download and verify the certificate and the integration archive."

Code: `inplace_preparation.py:218-222`: `download_integration` runs on line 218, `check(profile)` on line 219, the refusal on line 222. An unsupported host still downloads the archive into the job directory before it is refused. No active change results (plan line 24 holds), but the order is reversed and the refusal arrives later than the design promises.

### C3. The preview tree is kept until apply and is required at apply

Spec: design section 4.1 step 7 "It never becomes a launcher target, and preparation deletes it after the checks."

Code: `inplace_preparation.py:265` builds `job/hermes-preview`; `request['runtime']['source']` points at it (line 294); `inplace_plan.py:58-59` refuses apply unless `runtime_source_fingerprint(job/'hermes-preview')` is unchanged; `release_worker.py:_program_plan` runs the `program-configuration` stage with `source=preview`; `inplace_worker.py:204-208` (`remove_preview`) deletes it only after `applied` or `rolled_back`. The preview is never a launcher target (`service_environment`, `release_plan.py:121-124`, drops `PYTHONPATH` for format 2), so the safety property holds, but the design text is wrong about its lifetime and a full copy of the tracked Hermes tree sits in the job directory between review and apply.

### C4. `INTEGRATION.json` `lifeos` block has no `patches` field

Spec: design section 2 "`lifeos`: `{upstream, commit, tree_sha256, patches}`".

Code: `scripts/build_integration_release.py:72-74` writes `{upstream, commit, tree_sha256}`; `release_catalog.py:735` requires exactly that set. The design should drop `patches` or the builder should add it. Cosmetic.

### C5. `check()` surfaces a malformed host record as a generic 409

Spec: "It must refuse an unsupported installation with a specific reason" (plan, line 5).

Code: `host_compatibility.py:437-444` (`check`) calls `load_record`, which raises `HostRecordRejected` on a malformed, oversized, or wrongly-owned record. `dashboard/plugin_api.py:123-129` catches `ValueError` and returns "The Hermes compatibility check is unavailable". The CLI command (`cli.py:337-341`) lets it propagate. A damaged `lifeos-host.json` should produce a `host_drift`-class reason naming the record, not an "unavailable" message.

### C6. Before-values of configuration keys live in a separate file, not in the host record

Spec: design section 8 "The record also holds the before-values of the configuration keys LifeOS changes, and the inventory below."

Code: `host_configuration.py:17` `RECORD = '.lifeos-host/configuration.json'`; `host_record.py:31-57` `validate_record` rejects any extra key in `lifeos-host.json`. Removal (`inplace_removal.py:122-124`, `recorded_configuration`) reads the separate file and `host_plan` treats it as owned. Works; the design text is wrong about where the values live. Cosmetic.

### C7. `sync_venv(explicit=True, project_root=...)` eviction behaviour not verified here

Spec: design section 5 "with the host interpreter, plugin discovery from the configuration, and no plugin eviction."

Code: `dependency_plan.py:68-72`. I did not read Hermes `pm/client.py` and cannot confirm from this repository that `explicit=True` disables eviction. The design cites `pm/install.py:769-855`; the e2e run on 110 kept `weather-test` installed, which is consistent. Flagging as unverified by me, not as wrong.

## Checked and found consistent with the spec

- Compatibility admission table (plan lines 34 to 43): every row has a producing code path in `host_compatibility.py` (`_layout`, `_shared`, `_working_tree`, `_targets`, `_dependencies`, `_installed_reasons`), and `inspect_inplace` plus `staged_files` refuse changes after preparation (row 43).
- Source resolution from the running interpreter (plan line 45): `running_source()` uses `hermes_cli.__file__`; `transition_source` handles the managed case.
- Pinned LifeOS fetch (plan line 59): `install_source.prepare_lifeos` now fetches the exact commit with `git fetch --depth 1 <commit>` and checks `expected_tree`; `latest_revision` removed.
- No replacement runtime or stock archive download (plan line 61): `download_integration` fetches only the certificate and the integration archive; removal uses the restored host (`inplace_removal.runtime`).
- Durable transaction, hashes, modes, originals (plan line 65): `ProgramTransaction` with `fingerprint` (mode included), `host_entries` retains originals under `.lifeos-host/originals/`, `host_record.check_originals` verifies them against the manifest stock hashes.
- Update lock and update hold (plan line 71, design section 6): `inplace_worker.run` acquires `UpdateLock`; the hold is a program plan entry so rollback and removal remove it; `hermes-update-hold.patch` fails closed on an unreadable hold and reads `<git common dir>` (linked worktree test included).
- Consumer scan and refusal (design section 7): `consumer_scan.source_consumers` reads cmdline, environ, exe, cwd; `inplace_services.inventory` classifies bound, offered, blocking; `_consumers_stopped` refuses leftovers after the drain.
- Rollback order (design section 4.2): `_rollback` runs mount, programs, dependencies, services; a dependency restore failure is recorded, not fatal.
- Dependency admission (plan line 49, design section 5): throwaway `uv lock` against the selected lock, refusal on any changed or removed package, lock hash recorded at review and rechecked at apply and after synchronization.
- Removal restores originals, deletes added files, restores recorded keys, refuses a changed target (plan line 75): `host_plan` and `host_configuration.restore`; the `.env` owner lines are kept.
- Memory return before software removal (plan line 77): unchanged chain, `profile_units` plumbed through `MemoryTransition` and `OwnershipSetup`.
- Format 1 refusal by the new manager and format 2 refusal by the old manager (design section 2): `download_integration` requires format 2; the 0.7.3 `download` requires `hermes-dashboard.tgz`.
- Bootstrap has no Python dependencies beyond Hermes's own (design section 3): `host_compatibility` imports `ruamel.yaml`, which Hermes ships.

## What deserves Adrian's attention

In dependency order, then by verification difficulty and blast radius:

1. A1: add unit tests for `inplace_plan.py` and `inplace_worker.py` before the release gate; they are the modules that publish and roll back the host.
2. B1 / R2-1: decide whether the transition refuses service launchers outside `~/.local/bin` or the design documents the trap.
3. C1: make removal tolerate a missing hold file.
4. A2: add the fresh-process capability probe (`VALID_HOOKS`, `REQUIRED_MIDDLEWARE_API_VERSION`) or amend the design.
5. A5 / A6: expand the review payload (file list, configuration keys, update difference, known conflicts) or amend the design.
6. A4: either implement bridge-side drift reporting or move section 9 to "page and command only".
7. C2, C3, C4, C6: small code or design-text corrections.
8. A3, A7, A8, A9, C5: record as accepted limits or follow-ups.

Tests I ran: the 13 new-module test files, 129 tests, all pass with 1 skip (`spec-raw/spec-review-unit-tests.txt`). I did not run the container flows or `test_profile_services.py` (drives real user units).

## Round 2

- Date: 2026-10-17. Branch head `5d357559` (coordinator named `9f1749d3`; `5d357559` adds only `docs(install): record the regression on the fixes`). `origin/main` unchanged at `06ea5746`.
- Role: spec reviewer (read-only). Model: Claude Fable 5.1.
- Inputs: `round1-fix-plan.md`, `pr40-fixes-phase1.md`, `pr40-fixes-phase2.md`, the amended design, `git diff 90d1bf7f..HEAD` (36 commits, code diff 2670 lines), and the code at HEAD.
- Raw data: `spec-raw/spec-review-round2-unit-tests.txt`, `spec-raw/spec-review-round2-commits.txt`.

### Tests I ran

16 test files with the frozen test interpreter and the Hermes source on the import path (same harness as round 1): `test_inplace_plan` 14, `test_inplace_worker` 24 (real synthetic user units), `test_host_capabilities` 9 (1 skip), `test_host_compatibility` 42, `test_host_compatibility_manifest` 13 (1 skip), `test_inplace_removal` 12, `test_inplace_preparation` 22, `test_inplace_services` 8, `test_host_configuration` 6, `test_release_dashboard` 8 (1 skip), `test_integration_release_build` 3, `test_release_programs` 24, `test_release_preparation` 15: all OK. Three files report one error each (`test_release_version`, `test_release_manager_cli`, `test_release_accounts`): `ModuleNotFoundError` for a sibling test module (`test_release_stage`, `test_memory_owner_job_command`). I reproduced the same three errors at the round 1 base `90d1bf7f` in a temporary worktree, so they come from my harness (`tests/` is not on `sys.path` when the module is run as `tests.<name>`), not from the fixes. The phase reports ran them green with the project command.

### Round 1 findings

| Finding | Status | Evidence at HEAD |
| --- | --- | --- |
| A1 tests for plan and worker | Resolved | `tests/test_inplace_plan.py` (14), `tests/test_inplace_worker.py` (24): rollback order over a real `ProgramTransaction`, `verify_registration` with a real receipt, `_consumers_stopped` with real processes, `check_restarted`, `check_enabled`, `verify_restart`, `verify_runtime`. `_run` as a whole is still exercised only by the container runs; the coordinator's regression (transition and restore on 114, update on 112) covers the new post-restart path. |
| A2 capability probe, new PID | Resolved | `host_capabilities.py:30-57` (`-I -B`, `python`, hooks, middleware API); `inplace_worker.py:132-179` (`boot_ticks`, `check_restarted` start time strictly after the drain, `verify_restart`), called at `inplace_worker.py:370` and `413`; preparation probe at `inplace_preparation.py:266-267`. Design section 7 amended. |
| A3 enabled state | Resolved | `inplace_services.py:19,57` reads `UnitFileState`; `inplace_plan.py:116` stores it; `inplace_worker.py:159-163` refuses a change. Recorded in the plan, not the shared journal: design section 7 says so, and the plan (line 67) only requires preservation. |
| A4 drift in the bridge | Accepted, amended | `release_version.py:101-116` `host_status`, exposed in `status()` line 147; `release_plan.py:157-161` refuses `host_drift` after publication. Registration writes only the receipt (design section 9). The plan (line 71) requires edits to "remain detectable drift", not detection at registration. The amendment does not contradict the plan. |
| A5 review files and keys | Resolved | `inplace_plan.py:154-174` (`review_changes`, `update_difference`); `plugin_api.py:185-205` returns `files.modified`, `files.added`, `configuration`, `update`. |
| A6 known conflicts | Resolved | `host_compatibility.py:124-135` (`known_conflicts` optional, validated); `plugin_api.py:200`; none declared in the shipped manifest, which is a true statement for v0.21.7. |
| A7 interpreter and capabilities in the manifest | Resolved | manifest entry has `python: "3.14"` and `capabilities` (5 hooks, `middleware_api: 1`); `_interpreter` at `host_compatibility.py:351-356` refuses with `unsupported_interpreter`. |
| A8 inventory and memory authority | Resolved and amended | `host_configuration.py:51-57` `check_memory_provider`, called in `verify_restart`; design section 8 names `check_preserved` roots as the inventory for toolsets, MCP servers, model, providers. The plan (line 47, 69) does not prescribe the mechanism. |
| A9 idle foreign profile | Accepted | Design section 13 records the limit. The plan (line 42) names "active consumer"; an idle profile is not one. |
| A10 GitHub URL and buttons | Open by owner | Plan line 91, `TODO.md`, design section 12. Needs a published prerelease. |
| B1 workspace service launchers | Open by owner (R2-1) | Design section 10 now documents the repoint and the trap. The plan does not forbid it. |
| B2 to B4 | No change needed | In-scope fixes. |
| C1 missing hold blocks removal | Resolved | `inplace_removal.py:140-148`: absent hold produces no entry; a non-regular file or another holder still refuses. |
| C2 download before check | Resolved | `inplace_preparation.py:217` `check(profile)` precedes `download_integration` at line 221. |
| C3 preview lifetime | Accepted, amended | Design section 4.1 step 7 describes the code. |
| C4 `lifeos.patches` | Accepted, amended | Design section 2. |
| C5 damaged record | Resolved | `host_compatibility.py:492-507` returns `invalid_host_record` with the defect and the record path, state `host_drift`. |
| C6 configuration record file | Accepted, amended | Design section 8. |
| C7 eviction | Verified by phase 1 | Stock `pm/client.py` default `evict_incompatible_plugins=False`; `dependency_plan.py` does not pass `True`. |

### New behaviour from the fixes (`90d1bf7f..HEAD`)

(a) Missing: none against the plan.

(b) Unrequested: `verify_runtime` now refuses `host_drift` from the fresh `lifeos-version` run (`release_plan.py:157-161`). Design section 9 records it. It strengthens the plan's "verify the new processes import the patched source" (line 69); not a finding.

(c) Wrong: none found. Three observations, none a defect against the plan:

- `check()` compares the entry's `python` with the interpreter that runs the check (`host_compatibility.py:443`). In a managed-to-in-place transition that is the managed runtime's Python, not the stock checkout's environment. The preparation probe (`inplace_preparation.py:266-267`) checks the real host interpreter, so a mismatch is refused before any change; only the page result could differ from the probe. Both are 3.14 today.
- `check_restarted` compares `/proc` start ticks with `CLOCK_BOOTTIME` ticks (10 ms resolution). A unit that restarts within the same tick as the drain stamp would be refused; publication and synchronization take seconds, and the container regression passed.
- Pre-existing, not from the fixes: a fresh installation lists `pulse` in `created` (`inplace_plan.py:106-107`) and publishes its unit file, but `_start_created` and `check_restarted` cover only `CREATED_UNITS` (gateway, dashboard). I did not verify whether Pulse is meant to start at installation or at memory activation, so I record it as unverified rather than as a finding.

### Open items recorded in the documents

A10 (prerelease publication and the GitHub URL and dashboard-button tests) and R2-1 (workspace launcher repoint) are owner decisions recorded in the plan, the design, and `TODO.md`. They are not findings against the code.

VERDICT: CLEAN

## Round 3

- Date: 2026-10-17. Head `c5ed49b3`; scope `5d357559..HEAD` (8 commits). Role: spec reviewer (read-only). Model: Claude Fable 5.1.
- Raw data: `spec-raw/spec-review-round3-unit-tests.txt` (`test_profile_services` 24 with real user units, `test_inplace_services` 8, `test_inplace_worker` 24, `test_inplace_preparation` 22: all OK).

### Per commit

- `39da38e4`: `inplace_services.show` replaces the worker's `_show` and the manager's `_properties` body; the worker imports `removal_configuration.PLUGINS` as `OWNED_PLUGINS`. Behaviour unchanged except that `show` now also refuses on stderr output, the stricter of the two earlier helpers. No spec effect.
- `b9add026`: `profile_services.py:129-139`. A journal whose role set differs from the bound units is treated as absent only when its `state` is `active` (a completed operation); any interrupted state still refuses. The journal format is unchanged (design section 7). The plan's service requirements (line 67: stop, drain, preserve enabled and running state) are unaffected, because an `active` journal has nothing left to recover. The two new tests cover both branches.
- `cc799e17`, `150ff808`, `071ebf20`, `112fd02d`: `git diff 5d357559..HEAD` touches none of `cli.py`, `release_preparation.py`, or `removal_workflow.py`, so the reinstall attempt is fully withdrawn.
- `7d76fc6c`: design section 4.3 (Pulse unit written, not enabled or started, as the managed release did) matches `inplace_plan.py:106-107` and `inplace_worker.py:87-91`, and closes my round 2 observation. The new section 8 paragraph records that installing again after a verified removal is refused (`inplace_plan.py:95-97` for the native destination; the removal selection check in the memory workflow). The plan (lines 75 to 79) requires removal to restore the host and keep personal data; it does not require a reinstall path, so the limit does not contradict the plan. `TODO.md` carries the owner decision. Nit: the `TODO.md` link anchor is `#9-drift-reporting`, but the paragraph sits at the end of section 8.
- `c5ed49b3`: documentation of the final regression; nothing to check against the spec.

### New findings

(a) none. (b) none. (c) none.

Open by owner, unchanged: A10 (prerelease and dashboard-button tests), R2-1 (workspace service launchers), and the new reinstall-after-removal decision.

VERDICT: CLEAN
