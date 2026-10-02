# Independent review of the Opus finding corrections

Date: 2026-10-02.

Agent role: independent reviewer, Cerebo. Review only.

Question: Do the corrections close Opus findings F1 through F4, and do their immediate callers preserve the required behavior?

Actual assigned model: GPT-6.1-Sol. Reasoning effort: high. This review uses the assigned Codex agent directly, with no second model or agent CLI.

Exact reviewed correction commit: `f6620c5616686c583e6755d7557df8f9d747c200`.

Exact parent: `c484ea071634187a76e8673c17dd24edc2a5a2c8`.

PR context: https://github.com/0ut5ider/lifeos-hermes-plugin/pull/1. The review uses the provided local PR reports and exact Git diff. It does not fetch new GitHub state.

Adrian, F2, F3, and F4 close their original findings within the tested scope. F1 now refuses ordinary later profile edits and archives replaced targets, but two restore boundaries can still stop the gateway and leave a partial restoration. The worker error status prevents the browser recovery action from handling these failures. Keep the PR in draft until these paths are corrected.

## Closure table

| Original finding | Status | Evidence and limits |
| --- | --- | --- |
| F1: Restore overwrites later Hermes profile edits | Partially closed | Existing edit, mode, type, and tree-shape regressions pass. Post-stop validation restarts on refusal. The rename-boundary archive test passes. New probes expose a late refusal after program swap, a cross-filesystem archive failure, and unavailable browser recovery. |
| F2: Direct child admission checks only the model | Closed in reviewed direct gateway path | The complete body reaches admission with `aux_task='lifeos_child'`. Forgotten system and generated user claims produce no HTTP requests. Approved routes, invalidated contexts, route revocation, retained disabled contexts, and a fresh disabled child behave as expected. This is not complete child route acceptance. |
| F3: Development recorder retains unknown environment credentials | Closed for supported environment mappings | The allowlist projection and pre-encoding secret collection scrub unknown values and echoes. Real hook behavior tests pass. Additional probes cover `env`, `environment`, case variation, outer JSON text, bytes carrying JSON, aliased mappings, and later artifacts. Arbitrary prose and unrelated encodings remain documented limits. |
| F4: Mount preparation snapshots keep credential copies permanently | Closed within reviewed lifecycle | Terminal snapshots disappear. Pending snapshots remain. Preparation killed before journal publication is cleaned on a later operation. Binding, private identity, symlink, unknown directory, missing snapshot, and malformed journal checks preserve necessary or unrecognized state. Version-update archives remain separate. |

## Reproduced findings, ordered by severity

### R1. High: Cross-filesystem profiles make restore and recovery fail after the program swap

- Exact lines: `lifeos_hook_bridge/update_transaction.py:91`, `:102`, and `:166`. The new archive moves use `os.replace`. The apply preflight checks only the installed tree against the snapshot filesystem.
- Caller path: apply or browser version restore -> `update_worker._execute_update_job` -> `restore_update` -> `_restore_mount`. Update rollback and `recover_update` use the same helper.
- Expected behavior: an accepted profile layout has a working restore and rollback path. If the archive cannot safely preserve that layout, validation refuses before stopping the gateway or changing live directories.
- Actual behavior: a real regular Hermes profile under `/dev/shm` and installed/snapshot directories under `/tmp` pass `apply_update`. `restore_update` stops, swaps the installed program to the prior version, then raises `OSError` with errno 18 at the first profile archive move. The selected profile remains live, the manifest is `restoring`, and the start callback never runs. Direct `recover_update` repeats the same error and cannot complete. No credential archive is created for the profile contents.
- Evidence: `raw/probe_restore.txt`, record `cross_filesystem`. The filesystem device identifiers differ, 27 and 52 in this run. These are actual filesystem operations. Stop/start callbacks record the service lifecycle; no real gateway service runs.
- Reproduction: with the environment in `raw/commands.sh`, run `python docs/agents/2026-10-02-sol-review-fixes/raw/probe_restore.py`.
- Proposed correction: validate the filesystem requirements for all archive moves, including the baseline, before apply accepts the transaction and before restore/recovery stops or swaps anything. A clear early refusal is the smallest correction. If separate filesystems must remain supported, preserve targets in an archive on each target filesystem and record those archives durably. Do not replace the atomic move with an unchecked copy followed by deletion.
- Scope: this archive constraint is introduced by this batch. The previous helper copied and deleted profile targets and did not require them to share the version snapshot filesystem. This is a regression in accepted layouts, without a reproduced data-loss claim.

### R2. Medium: The final profile guard can refuse after directory swaps without restarting the gateway

- Exact lines: `lifeos_hook_bridge/update_transaction.py:72` and `:265` through the call at `:267`. The error handler at `:260` only covers the preceding `validate_restore` call.
- Caller path: browser restore -> detached worker -> `restore_update` -> `_restore_mount(expected_state=...)`.
- Expected behavior: a later profile edit causes a safe refusal with the edit preserved, a coherent selected program/profile, and the gateway restarted. If restoration has already mutated state, it retains an actionable recovery state.
- Actual behavior: the probe writes a later `config.yaml` edit immediately after the installed directory moves into `restored-selected`. The next program rename installs the prior tree. `_restore_mount` then detects the edit and refuses. The lifecycle output is only `['stop']`, the program is `owned-v1`, the profile remains edited against the selected version, and the manifest is `restoring`. Direct recovery succeeds and archives the edit, but the browser route cannot invoke it because of R3.
- Evidence: `raw/probe_restore.txt`, record `late_refusal`. The probe injects the race at an actual rename boundary and uses real temporary files. It does not replace profile collection or restoration logic.
- Reproduction: with `raw/commands.sh` environment, run `python docs/agents/2026-10-02-sol-review-fixes/raw/probe_restore.py`.
- Proposed correction: cover the final guard and directory swaps with a coordinated failure path. Before profile mutation, a refusal can restore the selected program directories, return the manifest to `applied`, and restart. If a partial profile restoration has occurred, preserve its archives and expose recovery instead of leaving an unreported partial state. Keep the guard and archive preservation intact.
- Scope: the third check is new in this batch. The ordinary post-stop refusal regression covers the second check and therefore misses this later path.

### R3. Medium: The worker marks an unfinished restore as failed and the recovery route rejects it

- Exact lines: `lifeos_hook_bridge/update_worker.py:248`; `lifeos_hook_bridge/dashboard/plugin_api.py:508` and `:598`.
- Caller path: an exception from `restore_update` -> worker `_main` -> `_write_status(state='failed')` -> `get_lifeos_update_status` -> authenticated `POST /installation/update/recover`.
- Expected behavior: a snapshot whose transaction state is `restoring`, `stopped`, `swapped`, or `rollback_failed` remains available for recovery after its worker exits with an error.
- Actual behavior: `_main` converts `restoring` to the job state `failed`. The status route returns `state='failed', transaction_state='restoring'`. It only checks worker inactivity for `preparing`, `applying`, `restoring`, and `recovering` job states. The recovery route requires the job state `interrupted`, so it responds with HTTP 409, `There is no interrupted LifeOS swap to recover`.
- Evidence: `raw/probe_callers.txt`. The probe injects the already reproduced exception at `run_update_job`, executes the real worker exception handler, then calls the real authenticated local API. It does not execute systemd or a complete worker. The worker stderr is captured and inspected. This is a boundary integration probe, not an end-to-end acceptance test.
- Reproduction: with `raw/commands.sh` environment, run `python docs/agents/2026-10-02-sol-review-fixes/raw/probe_callers.py`.
- Proposed correction: reconcile job state from the recoverable transaction state after an exited worker, or preserve an explicit recovery-required status in `_main`. Permit recovery based on the validated transaction and worker lifecycle. Also examine retry of an `applied` transaction after a harmless pre-mutation refusal, because the same handler writes `failed` there.
- Scope: these status lines precede the batch. They are a missed immediate caller contract exposed by the newly introduced F1 refusal and archive failure paths. R3 adds the browser reachability consequence to R1 and R2; it does not claim a separate profile data-loss mechanism.

## Static observations and hypotheses

No additional static defect is promoted to a release blocker.

The new update profile archive renames do not fsync the archive directory or the original profile parent. `_write_json` fsyncs a manifest file, but that does not durably publish the moved profile directory entries. Static inspection therefore does not establish archive preservation across a power loss. A process exit or SIGKILL is a different case: the filesystem renames remain visible to the next process. Optional hardening is to sync both parents and record the archive location before further destructive steps. No power-loss test is performed, and no archive loss is claimed.

Concurrent detached restore/recover launches remain an existing hypothesis from the Opus report. This review does not run two workers or establish a concurrency failure. Same-account filesystem substitution races remain an explicitly documented acceptance limit. The probes here demonstrate ordinary transaction race handling and a valid filesystem layout, without asserting a new hostile same-account boundary.

Cleanup exceptions propagate from `_prune_snapshots`, including the final cleanup after a terminal journal write. Thus a disk or permission failure can report an operation error after commit. Static inspection shows a terminal journal remains available and a later cleanup attempt can retry; it does not prove behavior for every disk fault. No cleanup failure is reported as a reproduced new defect.

## Verification and raw evidence

All commands run with `/home/outsider/.cache/lifeos-plugin-memory/memory-plugin-test-env/bin/python`. The Python path includes the repository, tests, and the supplied pinned Hermes fixture. Bytecode writing is disabled. Native TaskGovernance has the supplied source path, so its test is not skipped.

| Selection | Result | Evidence |
| --- | --- | --- |
| Update transaction, mount transaction, children, administrative dashboard, update worker | 50 pass in 46.777 seconds; exit 0; no skips or warnings | `raw/focused-tests.txt` |
| Development `test_capture.py` | 32 pass in 7.280 seconds; exit 0; no skips or warnings | `raw/recorder-tests.txt` |
| Runtime, history, Hermes memory provider | 51 pass in 16.607 seconds; exit 0; no skips or warnings | `raw/runtime-tests.txt` |
| Restore boundaries | Two defect scenarios reproduced; script exits 0 | `raw/probe_restore.py`, `raw/probe_restore.txt` |
| Worker status and authenticated recovery route | One defective caller scenario reproduced; expected error captured; script exits 0 | `raw/probe_callers.py`, `raw/probe_callers.txt` |
| Direct child positive, revoked, retained disabled, and fresh disabled behavior | Four scenarios pass; script exits 0 | `raw/probe_child.py`, `raw/probe_child.txt` |
| Cleanup identities, journals, pending states, and symlinks | 13 scenarios pass; script exits 0 | `raw/probe_cleanup.py`, `raw/probe_cleanup.txt` |
| Recorder mapping variants, JSON, bytes, aliases, and later echoes | Seven scenarios pass; script exits 0 | `raw/probe_recorder.py`, `raw/probe_recorder.txt` |

Total repository test executions: 133 pass, zero failures, zero skips, zero warnings. Separate probe scenarios: 27, comprising 24 expected-behavior checks and three deliberate defect reproductions. The two restore scenarios share one script; the worker mapping reproduction is separate. The passing script exit codes show their observations match their assertions, not that the defective product behavior passes acceptance.

`raw/commands.sh` records the exact test and probe selections and required environment. `raw/reviewed.diff` records the exact correction diff. `data.json` contains structured findings, closure, coverage, and counts.

The initial `before.txt` and Opus validation reports are read as input evidence. Their historical results are not rerun by implication. The broader gate owned by the primary agent was running during this review. Its incomplete output is not counted here. The supplied 19-patch identity statement is an input assumption; this reviewer does not independently recalculate those fixture hashes.

## Coverage and acceptance limits

Reviewed the exact implementation corrections in `update_transaction.py`, `mount_transaction.py`, `bin/claude_direct.py`, and `development/hook_capture/store.py`, their changed tests, the F1 through F4 verification README and failing-before output, and the prior Opus and primary reports. Reviewed the relevant immediate paths in `dashboard/plugin_api.py`, `update_worker.py`, `memory_runtime.py`, `memory_history.py`, `memory_transaction.py`, and recorder `instrument.py`.

For F1, inspected existing profile validation, modes, nested directory shape, symlink refusal, post-stop guard, UUID archives, baseline replacement, repeated recovery, and partial restore handling. The existing tests cover normal success, rollback, recovery, profile edits, missing metadata, and a rename-boundary write. The new probes cover the final guard and filesystem requirement.

For F2, inspected full request construction and auxiliary admission. This prevents the runtime's current explicit-user-input exemption from excluding generated child content. Admission returns no projected body, but this path uses refusal semantics, so sending the original checked body is appropriate. Local requests establish the reviewed direct gateway behavior, not real-provider quality or all native inference routes.

For F3, inspected recursive declaration, JSON decoding, aliases, pre-encoding learning, and process observer ordering. `process.started` observes the subprocess options before the real child runs, so ordinary unknown environment echoes are learned before completion events. Existing real-hook tests compare observed and native behavior. Allowlisted values deliberately remain diagnostics. Values shorter than four characters, unstructured unknown secrets, and unrelated encodings retain the existing filter limitations.

For F4, inspected lock acquisition, identity ownership, terminal journal validation with an absent payload, pending retention, preparation orphan removal, and cleanup after status, execute, and recovery. Snapshot payload publication and terminal journal publication precede cleanup. `publish` syncs files and parent directories. The existing process-kill tests cover preparation, publication, and recovery. The additional probes confirm malformed journals fail before deleting state, missing pending snapshots refuse, missing terminal snapshots remain valid, and foreign/unmarked identity and symlink targets remain intact. Unknown historical orphan directories require operator inspection. No migration is required by this review.

No implementation, repository tests, configuration, branch, index, commit, deployment, server, or external application is changed by this reviewer. Only this output directory contains reviewer-authored files. Test fixtures use disposable synthetic local data. No memory or journal tools are called. No subagent is started.

This review does not establish complete hook parity, complete memory acceptance, ownership activation, live systemd service behavior, browser acceptance, SSH, Docker, remote capture, real-model behavior, power-loss durability, the full source-preparation gate, or the complete release gate.

## Recommendation and Adrian's review items

Keep the PR in draft. Correct R1 through R3 together, then rerun the failing probes and the affected transaction/caller tests. The original F2 through F4 corrections can remain in that same staged package.

Adrian's review should focus on the accepted filesystem layout, the coherent state required after a late restore refusal, and how the browser identifies a failed but recoverable transaction. The local callback probes prove the missing restart call; they do not measure a running service. No changes outside Git are made, so there is no external configuration to undo.
