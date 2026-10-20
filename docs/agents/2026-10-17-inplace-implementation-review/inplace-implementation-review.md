# In-place installation implementation review

Date: 2026-10-17. Role: independent code reviewer. Model: Claude Fable 5.1 (claude-fable-5-1).

Question: review the diff `0517bd8c..95b6db43` on `feature/minimal-install-review` (paths `optional`, `lifeos_hook_bridge`, `scripts`, `patches`, `tests`) for correctness bugs, safety gaps, and violations of `docs/in-place-installation-plan.md` and `docs/in-place-installation-design.md` (including section 14). Stock Hermes v0.21.7 at `/home/outsider/agent-scratch/hostcompat/hermes-agent` was the reference for assumptions about the host.

Conventions. `REPO` is `/home/outsider/Projects/Hermes_agent/LifeOS_plugin`, `HERMES` is the stock checkout above. "Verified" means I read the code, ran it, or read a recorded result. "Inferred" means I reason from code I read but did not execute. I changed no repository file except this report. `removal_*.py` was not reviewed, as instructed.

## 0. Summary

The transaction core is sound: per-file before/after fingerprints, the re-check at admission and again in the worker, the seed-lock and configuration hashes, the fail-closed update hold, and the start-time-validated process identities all hold up. The 18 unit suites I ran pass (section 4).

Two problems are blocking:

1. **Forward recovery of an interrupted first installation is refused at every checkpoint after host publication begins** (`inplace_plan.py:59-67`). The uncommitted crash-matrix result `docs/verification/2026-10-17-inplace-e2e/crash-results/artifact-published-60.txt` already shows the consequence: `recovery_required`, gateway inactive, 46 modified and 12 untracked files in the checkout, and the `hermes lifeos-release` command gone. This is exactly the "crash leaves no recoverable state" case the plan forbids.
2. **A failure before the service drain publishes its journal makes rollback and every later recovery raise inside `_rollback`** (`inplace_worker.py:168-169`), so a non-fresh operation can get stuck in `recovery_required` with nothing changed on disk and no way out through the UI. The same shape exists in the managed worker, but the in-place path adds a realistic trigger (the gateway restarted between review and apply, which fails the drain signature).

The rest are should-fix items around registration proof, the Pulse unit, the update marker held across restart, and consumer handling in recovery and rollback.

## 1. Findings ranked by severity

### Blocking

**B1. Fresh-install forward recovery refuses once any host file is published.**

Evidence (verified). `inplace_worker.py:200-202`: `fresh_recovery` calls `inspect_operation(..., fresh_recovery=True)`, which is `inspect_inplace`. `inplace_plan.py:59-67` then requires, with no `fresh_recovery` exception:

- `host['state'] == request['host']['state']` (`'compatible'` for a first install). After `ProgramTransaction.apply` has published some targets, `inspect_host` reports `partially_patched`; after all targets, `patched_without_record`; after `lifeos-host.json` is published, `installed`.
- `record_digest == request['host']['record_sha256']` (`None` for a first install). Once `lifeos-host.json` is published this is non-null.
- `sha(selected_lock(source)) == request['dependencies']['seed_sha256']`. After `synchronize` commits a new generation, the selected lock is the new one.

So recovery is refused after a crash at every checkpoint from the first `artifact-published` through `native-mounted`. The crash matrix in progress confirms the first case: `crash-results/artifact-published-60.txt` records `"message": "The Hermes installation changes after preparation; prepare the operation again"` from `inplace_plan.py:64`, state `recovery_required`, `gateway: inactive`, `git status` summary `46 M 12 ??`, and `hermes: 'lifeos-release' is not a hermes command`. The remaining three cases (`programs-published`, `dependencies-synchronized`, `native-mounted`) will fail the same way for the reasons above (inferred from the code; not yet in the results directory).

Failure scenario. Worker is killed (OOM, reboot, `systemctl --user stop`) during publication of a first install. The owner's Hermes has a mixed tree, the gateway stays stopped, the release manager CLI and dashboard page are unavailable because the plugin directory or `hermes_cli` modules are mid-swap, and the only recovery action the state machine allows (`recover`) is refused before it touches a service. There is no supported path back.

Fix. In `inspect_inplace`, when `fresh_recovery` is true (and later for the update recovery path if it ever inspects): accept host states `{compatible, partially_patched, patched_without_record, installed}` provided every target hash is either the entry's stock or patched value (reuse `_targets`), accept `record_digest in {request['host']['record_sha256'], sha(job/'generated/lifeos-host.json')}`, and accept the selected lock hash in `{seed_sha256, dependencies.lock_sha256}`. `ProgramTransaction.resume` already enforces per-file identity, so this does not weaken the transaction. Add the four crash points to the unit tests with a disposable Git checkout, not only to the container matrix. Also decide what the worker should do when recovery is refused: today it exits before `services`, leaving the gateway stopped; at minimum the status error should say so.

**B2. `_rollback` raises when the drain never published its journal, and recovery repeats the raise.**

Evidence (verified). `inplace_worker.py:166-170`: `_rollback` unconditionally calls `services.quiesce()`. `profile_services.py:259-263`: `quiesce` raises `MemoryUnavailable` when `_load()` returns `None`, which is the case when `drain` raised before `_publish` (`profile_services.py:247-255`: the signature comparison at line 253 runs before `_publish` at 255). `MemoryUnavailable` is a `RuntimeError` (`memory_access.py:51`), so `execute` (`release_worker.py:312-319`) records it and writes `recovery_required` because the state is `applying`. The `recover` action for a non-fresh operation goes to `inplace_worker.py:219-236` and calls `_rollback` again at line 228, which raises again at `quiesce`. The fresh path guards this (`inplace_worker.py:250-253` checks `services.status()['state'] != 'none'`); the non-fresh and rollback paths do not. The managed worker has the same shape (`release_worker.py:465-466`), so this is partly pre-existing.

Failure scenario. Owner prepares an update, then restarts the gateway by hand (or systemd restarts it after a crash). On apply, `drain(signature=...)` raises "The reviewed profile service state changes before draining" because `active`/definition changed, before any file moved. `_rollback` raises `MemoryUnavailable`, the original refusal is lost from `status.json`, the state becomes `recovery_required`, and `recover` fails identically forever. Nothing on disk changed, but the UI shows an unrecoverable operation and blocks every other action (`admit_operation` refuses siblings in `recovery_required`, `release_worker.py:71-75`).

Fix. In `_rollback`, call `services.quiesce()` only when `services.status()['state'] != 'none'`; otherwise skip service handling and still restore programs. Record the original exception before attempting rollback (it already is, via `record_failure`, but the surfaced `status.json` error comes from `execute`; include the `worker-failure.json` message as `_preparation_error` does for preparation).

### Should fix

**S1. Registration proof skips a created gateway and silently passes a non-active gateway.**

Evidence (verified). `inplace_worker.py:97-98`: `if 'gateway' not in plan['services']['roles']: return None`. `roles` are bound units only (`inplace_plan.py:99`); a gateway replaced by a created unit is in `created`, not `roles`. `inplace_worker.py:107-108`: `if ActiveState != 'active': return None` succeeds without a receipt.

Scenario. Stock host where the owner runs `hermes gateway run` in a terminal (common before `gateway install`). The review offers a unit, the worker kills the process, creates and starts `hermes-gateway.service`, and never checks the receipt. If the bridge registers `reduced` (for example because a plugin-dispatch patch target did not take effect), the install reports `applied`, which the plan forbids ("must not report a complete installation when only a reduced set of hooks registers"). Design section 7 requires the receipt from the restarted gateway.

Fix. Verify when `'gateway' in roles or 'gateway' in created`. Treat a non-active gateway as a failure whenever it was active before the drain or was just created; keep `None` only for a gateway that was inactive before and is inactive after.

**S2. The Pulse unit is published but never enabled or started on a first in-place install.**

Evidence (verified in this repository; the intended behaviour is unclear to me). `inplace_plan.py:101-102` adds `'pulse'` to `created`; `release_worker.py:226-228` publishes its unit file; `inplace_worker.py:22` limits `CREATED_UNITS` to gateway and dashboard, so `_start_created` (`82-85`) ignores Pulse, and `services_for` binds only `roles` (bound units), which on a stock host excludes Pulse. Nothing in `_run` activates it and `verify_runtime` does not check it. I did not find where the managed flow activated Pulse either, so this may be a deliberate later step (memory ownership workflow). If Pulse is expected to run after a first install, this is a functional gap; if not, the review text "User services created: pulse" is misleading.

Fix. Either `enable --now` Pulse with the other created units and verify it active, or state in the review that Pulse is created disabled and when it starts.

**S3. The Hermes update marker is held across the service restart; a restarted process that takes the stale-environment boot branch refuses to start.**

Evidence (verified code, inferred consequence). `inplace_worker.py:185-192`: `UpdateLock(install_root=source).acquire()` takes the checkout flock and the marker `<root>/.hermes-update-in-progress`, released only after `_run` returns, that is after `services.resume()` and `verify_registration`. `HERMES/hermes_cli/venv_sync.py:405-408`: a launching Hermes process whose environment is not current or which finds a pending completion marker calls `UpdateLock(install_root=root, checkout_first=False).acquire()` and raises "an update is still running; wait for it to exit, then relaunch Hermes" when refused. `update_lock.py:1537-1543`: adoption succeeds only for the owner, an ancestor, or the hand-off partner; a gateway started by systemd is none of these. `owed_to_cli` (`venv_sync.py:388`) skips the branch for supervised children, and the stock unit sets `HERMES_SUPERVISED_CHILD=1`, but the units `release_services.service_files` creates do not (`release_services.py:68-70`), and a hand-started dashboard replacement therefore does not benefit.

Scenario. A host with a pending completion marker from an earlier interrupted `hermes update` (`completion_pending_path`), or whose created dashboard unit boots into the not-current branch for any reason: the unit fails to start while the worker holds the marker, `services.resume()` or `_start_created` fails, the worker rolls back a successful publication, and inside `_rollback` the same `resume()` can fail again, leaving `recovery_required`.

Fix. Hold only the checkout lock during the operation (`update.acquire_checkout(source)`; `hermes update` takes the checkout lock first at `update_lock.py:1443-1446` and is refused without needing the marker), or release the lock before `services.resume()`; publication and synchronization are complete by then. Set `HERMES_SUPERVISED_CHILD=1` in the created units as the stock unit does (`HERMES/hermes_cli/gateway.py:3336`).

**S4. `restore` of a completed in-place install is refused after any Hermes write to `config.yaml`.**

Evidence (verified). `release_worker.py:222` keeps `<profile>/config.yaml` as a byte-managed `ProgramTransaction` file target for format 2. `check_restore` (`release_worker.py:576-585`) requires `fingerprint(target) == after` unless the mount manifest overrides it. Hermes rewrites `config.yaml` on `/model` persistence, dashboard settings, plugin enable/disable, and migrations. Design section 14 resolved the review finding for removal ("record key before-values; removal restores keys") but `restore` still uses byte identity.

Scenario. Owner installs, changes the model in the dashboard, then clicks Restore: "The prepared release changes or has unfinished recovery". The only remaining path is removal, which is a different workflow with memory-return semantics.

Fix. For `restore`, compute an override for `config.yaml` that accepts the current bytes when the key-level record (`host_configuration.record`) shows the installed values intact, and restore by key as removal will; or state on the page that Restore is available only until the configuration changes.

**S5. Recovery and rollback never look for hand-started consumers; fresh recovery also skips `_consumers_stopped`.**

Evidence (verified). `inplace_worker.py:219-236` (recover/restore of a non-fresh operation) does not call `inventory` or `_terminate`. `inplace_worker.py:255-256` runs `_consumers_stopped` only when `not fresh_recovery`. `inspect_inplace` during fresh recovery treats a hand-started gateway or dashboard as an offer, not a blocker (`inplace_plan.py:95-98`).

Scenario. Crash after `programs.apply` began; the owner, seeing the dashboard gone, starts `hermes dashboard` by hand (it boots a mixed tree). Recovery (once B1 is fixed) resumes publication under that process, then `_start_created` starts the new dashboard unit on the same port. Or: `restore` after a completed install while an interactive `hermes` session runs; files move under it. The plan requires the worker to "enumerate all consumers ... and refuse an uncontrolled consumer" for the transaction, not only for apply.

Fix. Run the same inventory and refusal (or terminate-and-replace for offered roles) at the start of the recover and restore paths, before `write_state('recovering'/'restoring')`.

**S6. Terminating a hand-started consumer is not undone on failure, and only the main process is signalled.**

Evidence (verified). `inplace_worker.py:52-63` sends SIGTERM to the reviewed PIDs only; `66-79` then polls for 15 s and refuses if anything still uses the source. `_rollback` resumes only bound units; the created unit file is removed by `programs.restore()` and nothing restarts the owner's process.

Scenario. Hand-started gateway with child processes (MCP servers, `hermes-worker-*` scopes) that outlive the SIGTERM for more than 15 s. The worker refuses ("Hermes processes still use the installation"), rolls back, and the owner has no gateway at all, with a message about processes rather than about the gateway it stopped.

Fix. Terminate the process group (`os.killpg` when the process leads one) or wait for descendants explicitly; on rollback after a terminate, tell the owner in `status.json` which processes were stopped and that they must be restarted by hand. Consider refusing when the hand-started process has children outside the reviewed PID.

**S7. The worker and later actions are bound to an interpreter path inside an environment generation that `hermes pm gc` deletes.**

Evidence (verified). `inplace_preparation.py:174-175` and `200` record `request['runtime']['python'] = host_python(source)` (the selected generation at preparation time). `inplace_worker.py:270` commits a new generation. `cli.py:284` launches recover and restore workers with that recorded path. `HERMES/pm/cli.py:511-528` (`cmd_gc`) removes unselected dependency generations.

Scenario. Install succeeds; weeks later the owner runs `hermes pm gc`; then clicks Restore: "The owner service manager cannot start the release worker" (`cli.py:292-295`). The e2e restore passed because gc did not run in between.

Fix. Resolve the interpreter at launch from `pm.environments.project_python(source)` (or `<source>/.hermes/bin/hermes --run-module`), and record the generation only as information. `inspect_inplace` already checks `request['runtime']` equality (`inplace_plan.py:51-55`); keep that for the other fixed paths.

**S8. Unit creation is implicit; the design said the owner accepts or the installer refuses.**

Evidence (verified). `inplace_plan.py:100`: `created = list(consumers['offers'])` with no owner input; the review page shows "User services created" and "Stops the hand-started ..." (`plugin_api.py:407-420`, `dist/index.js` `inPlaceReview`). Design section 1 and 14: "The owner can accept, or close the process and prepare again; otherwise the installer refuses." Approving the review is a defensible form of acceptance, but it is a change from the recorded decision and the page should say that approving creates the unit. Minor plan deviation; recorded here because it changes what approval means.

### Minor

**M1. The design's `__pycache__` removal before restart is not implemented.** Design section 7 says the worker removes the bytecode of changed modules. `grep __pycache__ optional/lifeos_release_manager/inplace_*.py` finds only exclusions. Python's size-and-mtime check makes stale bytecode unlikely, since `publish` writes fresh mtimes, so the risk is small; either implement it or drop it from the design.

**M2. Orphan retained originals after an update.** `inplace_plan.py:131-133` keeps every existing original with `setdefault`, while `build_record` (`134`) lists only the new entry's targets. A target the old release changed and the new one does not is restored on the host but its original stays in `.lifeos-host/originals/` outside the record forever. Design section 8 and review finding S7 wanted the retained copy removed. Harmless to correctness; disk and audit noise.

**M3. A failed dependency restore during rollback ends in `rolled_back` with no visible error.** `inplace_worker.py:174-178` writes `dependency-restore-failure.json` and continues; `311` writes `rolled_back`; `action_state` (`release_operation.py:77-82`) allows no further action from `rolled_back`. The design says "recorded, and recovery repeats it", but recovery is not offered. Hermes's boot-time sync will eventually rebuild the environment, so the practical effect is a stale generation and a silent owner. Surface the failure in `status.json`.

**M4. `current` is shadowed in the rollback path.** `inplace_worker.py:232-233` rebinds `current` (the bridge module) to the configuration bytes. Nothing uses it afterwards, so no bug today; rename to avoid the trap.

**M5. `host_configuration.record` skips the whole `plugins` root.** `host_configuration.py:14` (`OWNED_ROOTS = ('plugins',)`) and `51-66`. Design review S5 asked for `plugins.enabled`, `plugins.disabled`, and `plugins.entries.lifeos-*` before-values. Removal (out of scope) will have to rely on fixed transforms for these keys. Record them, or document why not.

**M6. `GET /api/plugins/lifeos-release-manager/compatibility` is not owner-gated.** `plugin_api.py:367-373`. It is read-only, but it returns the source path, interpreter path, and Python version. Other read endpoints in this router are also open, so this follows the existing pattern; noting it for consistency with the owner-only design statement in the verification record.

**M7. `request['runtime']['source']` names the preview after `remove_preview` deletes it.** `inplace_worker.py:160-163, 235, 298`; `release_worker.py:348` inserts it into `sys.path` for every later action. Later imports resolve through the venv's editable install instead (inferred; the e2e restore passing supports this). Harmless, but the worker imports `hermes_cli.update_lock` from the patched preview during apply and from the host afterwards; worth a comment or a stable path.

**M8. Residual window for Hermes's own eviction sync.** If the owner runs any `hermes` command between `programs.apply` and `synchronize`, the boot-time sync with `evict_incompatible_plugins=True` (`HERMES/hermes_cli/venv_sync.py:589-603`) can disable the bridge in `config.yaml`; the later `programs.restore()` then refuses because `config.yaml` no longer matches `after`. The plan accepts that owner actions outside the workflow are not preventable; the window is short. No change requested, recorded for the crash matrix.

**M9. Same-user system gateway unit.** `inventory` consults only `systemctl --user`. A gateway installed with `hermes gateway install --system` but running as the owner is found by the `/proc` scan as a hand-started gateway, offered a user unit, and SIGTERMed; systemd restarts it and `_consumers_stopped` refuses after 15 s. Safe but confusing; refuse at review when a system unit named `hermes-gateway.service` is active for this uid.

## 2. Focus-area answers

### 2.1 `inplace_worker.py`

- **Apply order** (`244-299`): drain bound units, verify stopped, terminate offered hand-started processes and re-scan, restore a pending mount (recovery only), create parent directories, native init (fresh), publish programs, `daemon-reload`, synchronize dependencies and compare the lock hash, mount, check configuration and inventory, `verify_runtime`, resume, start created units, registration proof, record configuration, `applied`. This matches design 4.2 except for the registration gap (S1) and the Pulse unit (S2).
- **Rollback order** (`166-180`): quiesce, stop created, mount, programs, `daemon-reload`, dependencies, resume. Matches design 4.2 and review resolution S1. Problem B2 (quiesce without journal) and S5 (no consumer scan).
- **Fresh forward recovery**: B1 makes it unusable after publication begins.
- **Restore** (`219-236`): correct order; S4 (byte-managed `config.yaml`), S5.
- **Update lock** (`183-192`): non-blocking acquire, held for the whole run, released in `finally`. `hermes update` is refused while held (verified: `HERMES/hermes_cli/main.py:2426-2432` acquires the same lock first and exits 2). S3 explains the cost of holding the marker through the restart.
- **Consumer termination**: `replace_with_units` (`inplace_services.py:61-77`) re-reads the start time immediately before `_terminate`, so a reused PID is refused rather than signalled (verified). The window between the start-time read and `os.kill` is microseconds and acceptable. Weaknesses are S6 (children, no undo).
- **Dependency synchronize** (`41-49`): runs `pm.client.sync_venv(explicit=True, project_root=source)` under the host interpreter with `PYTHONPATH=source`, matching design 5 and review B1. The lock hash comparison against the preparation-time resolution (`271-272`) is the right proof and is verified by the e2e run.
- **`verify_registration`**: receipt identity uses PID plus start time (`registration.py:172-180`), so a recycled PID cannot satisfy it (verified). Gaps are in S1.
- **Configuration and inventory checks** (`135-157`, `286-289`): `check_preserved` protects model, providers, platforms, toolsets, MCP; `check_inventory` compares other plugin trees, their enablement, and locked package versions. Correct. Note `_tree_digest` reads every file of every other plugin twice (performance only).
- **Mixed-state risk** ("patched files but mismatched environment"): the only window is between `programs-published` and `dependencies-synchronized`, during which no admitted consumer runs. A crash there is recoverable for an update (rollback) but not for a first install (B1).

### 2.2 `inplace_plan.py`, `inplace_preparation.py`, `dependency_plan.py`

- **TOCTOU between review and apply**: closed in depth. The admission re-runs `inspect_inplace` and re-seals the plan (`release_worker.py:38-58, 85-88`); the worker runs it again (`inplace_worker.py:202`) plus `check_plan` and `check_prepared` (`241-243`); `ProgramTransaction.apply` verifies each target's `before` fingerprint immediately before moving it (`release_programs.py:237, 272-285`). The seed lock (`inplace_plan.py:65-67`), record hash (`61-64`), and `config.yaml` hash (`inplace_worker.py:237`) are rechecked. One soft spot: if the set of offered units changes between prepare and admission, `check_plan` refuses with "The reviewed entries differ from the candidate program plan" rather than a message about services (verified by reading `release_worker.py:224-228` and `release_programs.py:146-163`). Fail-safe but opaque.
- **Update staging from retained originals**: `stock_source` (`inplace_preparation.py:63-83`) takes originals for recorded targets, the host for unrecorded ones, and refuses a recorded target without an original; `stage_host_files` then hashes every copy against the entry. `desired_host_files` (`49-60`) restores or deletes targets the new release drops. Correct for added, dropped, and kept targets (review finding S7), apart from the orphan copies in M2.
- **Transition from a managed runtime**: `check` (`host_compatibility.py:437-444`) inspects `<profile>/hermes-agent` when the running source is a managed job; `prepare_inplace` (`inplace_preparation.py:150-151`) requires an update intent with an installed native tree and no record; `transition_launchers` (`inplace_plan.py:144-155`) writes forwarders identical to Hermes's own (`HERMES/hermes_cli/_launchers.py:543-544`, verified) as `ProgramTransaction` file targets with retained before-copies, so a rollback returns the launchers to the managed runtime. `verify_runtime(restored=True)` uses `plan['launchers'][0]` which is the account launcher in transition mode (`inplace_plan.py:107`). This is consistent with design 10.4. Not exercised by the e2e record; the design calls for a rehearsal on a clone first.
- **`resolve_dependencies`**: the throwaway workspace seeds `uv.lock` from the selected lock and locks with the current members plus the staged bridge keyed by its future path (`dependency_plan.py:50-65`). The worker's lock-hash equality proves the resolution reproduces. `changed` refuses version changes or removals before review (plan requirement, review B4).

### 2.3 Supporting modules

- `host_compatibility.py`: unchanged logic from the verified detector plus `installed`, `host_drift`, `bridge_disabled`, and `transition`. `_installed_reasons` (`329-353`) compares source, commit, working tree, target hashes, and bridge enablement. Correct. `_dependencies` uses `sys.path` of the calling process, which in the worker is the host interpreter (good) and in the dashboard is the same environment.
- `host_patches.py`: stages in a temp directory, hashes every input and output, refuses extra produced files, atomic rename. Correct.
- `host_record.py`: strict structure, owner-only regular file, every original hashed on load. Correct.
- `host_configuration.py`: `changed_paths` recursion treats `ABSENT` sentinels correctly; `record` merges keeping earliest before-values; `restore` refuses conflicts. M5 on the `plugins` root.
- `consumer_scan.py`: matches roots with a delimiter check (`_references`, `9-18`), reads cmdline, environ, exe, and cwd; tolerant of non-dumpable processes; exports no arguments. `_role` (`21-28`) treats any command line containing `dashboard`/`serve` as a dashboard and `gateway run` as a gateway, so `hermes gateway run` in a `tmux` named "dashboard" would be misclassified; negligible.
- `inplace_services.py`: `_properties` requires an empty stderr, so a `systemctl` warning refuses (fail-closed). `inventory` excludes control groups of bound units and operator ancestors with role `other` only. Correct.
- `integration_package.py`, `release_catalog.download_integration`, `scripts/build_integration_release.py`: exact top-level set, exact file maps, certificate fields all bound, format 1 releases refused, GitHub asset digests and sizes checked. The builder produces reproducible archives (fixed owner, mtime, normalized modes). No findings. Note the tarball normalizes file modes to 0644/0755 while `file_map` hashes content only; nothing executes those files directly, so this is fine.

### 2.4 `hermes-update-hold.patch`

Verified: the two copies are byte-identical (`diff` prints nothing). `evaluate_update_admission` is the first layer and is called from the three mutating surfaces: `hermes update` preflight (`HERMES/hermes_cli/main.py:2379`, before the lock at `2426` and before `_cmd_update_impl` at `2444`, whose stash happens at `update_cmd.py:1403`), `hermes update --check` (`update_cmd.py:651`), and the dashboard update action (`web_routers/actions.py:255`). The zip path is inside `_cmd_update_impl`, so it is gated too. No other caller outside tests (`grep`). Fail-closed behaviour is correct: missing directory passes; symlink, non-directory, unreadable, non-JSON, missing or non-string fields, or oversized text refuse with `update-hold-invalid`; any exception in the hold check also refuses. Paths that still mutate the checkout and are not gated: rerunning `install.sh`, `hermes pm update` writing lock files, hand edits. The design accepts these as detectable drift. The passive "update available" banner and the dashboard `can_apply` flag are unchanged, as design 6 states.

One nit: the hold is published with mode 0600 (`ProgramTransaction` default); the patch reads it as the same user, so that works, but a system-level supervisor running `hermes update` as another user would see `PermissionError` and refuse with `update-hold-invalid`. That is the fail-closed outcome, so acceptable.

### 2.5 Shared code

- `release_worker.py`: format 2 dispatch at `358-360`; `_program_plan` branches on format for host entries, receipts, and created roles; `record_failure` now surfaces refusal text. `validate_operation_package` picks the right validator. No regressions found for format 1 paths (the managed `_prepare_managed_package` is retained but no longer called, per design 11).
- `release_plan.py`: `inspect_operation` dispatch, `existing_native` extraction (behaviour preserved, verified by reading the before and after bodies), `service_environment` drops `PYTHONPATH` for format 2 so the host launcher activates its own environment. Correct.
- `cli.py`: `compatibility` command, `_preparation_error`, `launch_worker` uses `validate_operation_package`. S7 on the recorded interpreter.
- `profile_services.py` roles: validation of distinct known roles, `required` derived from roles, stop and start orders filtered. Correct. The `first_installation=True` state directory `.lifeos-installation-services` is used consistently by `services_for` and the fresh-recovery status check.
- `release_services.service_files(roles=...)`: correct filtering; S3 notes the missing `HERMES_SUPERVISED_CHILD`.
- Dashboard `plugin_api.py` and `dist/index.js`: review payload and compatibility section match the Python shapes; the Install button requires `compatible`, update buttons require `compatible` or `installed`. M6 on gating.
- `registration.py` and `__init__.py`: receipts written for `inactive`, `reduced`, `patched`; stale receipts for dead PIDs removed on each write; `read_receipt` validates PID and start time. `write_receipt` never raises into plugin registration. Correct.

## 3. Plan and design conformance table

| Requirement | Status |
| --- | --- |
| Preparation changes nothing active | Met (verified: preparation writes only under the job directory; `build_preview` and staging read the host) |
| Recheck under locks, stop all admitted consumers before change | Met for apply; not met for recover and restore (S5) |
| Durable transaction, originals retained, resumable | Met for updates; first-install resume blocked by admission (B1) |
| Hermes updater coordination | Met (hold patch, update lock); marker held through restart (S3) |
| Restart admitted consumers, verify patched source and controls | Partially: registration proof skips created gateway (S1), Pulse not started (S2) |
| Preserve installed tools, plugins, model configuration | Met (`check_preserved`, `check_inventory`) |
| Owner chooses unit creation | Implicit through approval (S8) |
| Removal restores recorded keys | Out of scope; `plugins` root not recorded (M5) |

## 4. What I ran

Interpreter `/home/outsider/.cache/lifeos-daily-promotion-20261014/frozen-test-environment/bin/python`, `PYTHONPATH=REPO:/home/outsider/.cache/lifeos-release-0.7.3-20261016/archive-integration-wgrx453d/package/hermes`, `python -B -m unittest discover -s tests -p <file>` from `REPO`:

| Suite | Result |
| --- | --- |
| test_inplace_preparation.py | 7 OK |
| test_inplace_services.py | 6 OK |
| test_consumer_scan.py | 7 OK |
| test_dependency_plan.py | 3 OK |
| test_host_record.py | 6 OK |
| test_host_configuration.py | 4 OK |
| test_host_patches.py | 7 OK |
| test_host_compatibility.py | 34 OK |
| test_host_compatibility_manifest.py | 8 OK, 1 skipped (stock archive not set) |
| test_integration_package.py | 6 OK |
| test_bridge_registration.py | 4 OK |
| test_profile_services.py | 18 OK |
| test_release_catalog.py | 10 OK |
| test_release_preparation.py | 15 OK |
| test_release_manager_cli.py | 9 OK |
| test_release_dashboard.py | 6 OK, 1 skipped (needs managed fresh operation) |
| test_release_configuration.py | 9 OK |
| test_lifeos_install_source.py | 14 OK |

Not run: `test_release_ui.cjs`, the container e2e harness, the Hermes patch's own test file (needs a stock Hermes test environment). There is no unit test for `inplace_worker.run`; `check_inventory` is the only worker function with a unit test (`tests/test_inplace_preparation.py:87`). The crash cases in B1 are the kind of test that belongs in `tests/` with a disposable Git checkout and a stub service layer, since the container matrix is slow and uncommitted.

## 5. Raw data

### 5.1 Crash-matrix result read from disk (uncommitted, `git status` shows `?? docs/verification/2026-10-17-inplace-e2e/crash-results/`)

```
== case artifact-published-60
exit=9
state after crash: {"identifier": "5df2972c02824e8c8b1c001d758f8d16", "state": "applying"}
gateway after crash: inactive
state after recovery: {"identifier": "5df2972c02824e8c8b1c001d758f8d16", "state": "recovery_required", "error": "The release worker refuses the current artifacts or authority. Review the private operation before recovery."}
{"exception": "ReleaseRejected", "frames": [... "inplace_plan.py", "line": 64, "function": "inspect_inplace"], "message": "The Hermes installation changes after preparation; prepare the operation again"}
hermes: 'lifeos-release' is not a `hermes` command.
gateway: inactive
hermes: 'lifeos-version' is not a `hermes` command.
     46  M      12 ??
```

### 5.2 Stock Hermes facts used

- `hermes_cli/main.py:2379` admission before `2426` lock before `2444` `_cmd_update_impl`; stash at `hermes_cli/update_cmd.py:1403`.
- `hermes_cli/update_lock.py:1443-1458` `acquire` takes checkout lock then marker; `1537-1543` adoption only by owner, ancestor, or hand-off partner.
- `hermes_cli/venv_sync.py:405-408` boot refuses while a foreign marker is live when the environment is not current or a completion is pending; `388` `owed_to_cli` exemption for supervised children.
- `hermes_cli/gateway.py:3330-3346` stock unit: `WorkingDirectory` is HERMES_HOME (`3137-3145`), `Environment="HERMES_SUPERVISED_CHILD=1"`, `KillMode=mixed`, `Restart=always`.
- `pm/cli.py:511-528` `cmd_gc` removes unselected dependency generations.
- `pm/workspace.py:112-140` `_generate_pyproject` accepts a mapping of identity to source, as `dependency_plan.resolve` uses.
- `pm/install.py:791-859` `sync_venv(explicit=True)` with `plugins=None` discovers members from configuration and commits only on success.

### 5.3 Manifest summary

`optional/lifeos_release_manager/host-compatibility.json`: entry `v0.21.7` at `71d34bad1045610252eda02ee79549436896e784`, 96 targets, 27 added, 11 patches ending in `hermes-update-hold.patch`, dependencies `tree-sitter==0.26.0`, `tree-sitter-bash==0.25.1`, `pathspec==1.1.1`, `mcp==2.0.0`.

### 5.4 Commands

```
git diff --stat 0517bd8c..HEAD -- optional lifeos_hook_bridge scripts patches tests   # 57 files, +4860 -181
diff patches/hermes-update-hold.patch lifeos_hook_bridge/patches/hermes-update-hold.patch   # identical
grep -rn evaluate_update_admission HERMES --include=*.py   # 3 callers outside tests
grep -n __pycache__ optional/lifeos_release_manager/inplace_*.py   # exclusions only
```
