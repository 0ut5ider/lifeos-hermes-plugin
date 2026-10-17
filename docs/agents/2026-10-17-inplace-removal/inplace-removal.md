# In-place software removal

- Date: 2026-10-17
- Role: implementation agent
- Model: Claude Opus 5.5 (claude-opus-5-5)
- Branch: `feature/inplace-removal` (worktree `/home/outsider/Projects/Hermes_agent/LifeOS_plugin-removal`, base `2bfc5d42`)
- Task: make complete software removal work for an in-place installation (request format 2, `lifeos-host.json` present), keep the managed path working, and keep the existing removal safety contract (verified provider return, owner review, signed plan, marker, recovery command, rollback, verify).

## Status

Code and unit tests are done and committed. The end-to-end removal on CT 111 is **not done**. The coordinator stopped all Proxmox operations while my reset of CT 111 (`pct stop 111 && pct rollback 111 installed-baseline && pct start 111`) was running. The ZFS rollback hung in D state on the Proxmox host. I stopped my local tasks that sent that command and its follow-up container commands, and I did not retry. I can't confirm whether the remote `pct start 111` ran after I stopped the local ssh client. At my last check, CT 111 was `stopped`.

Before the reset I ran a de-risking pass on CT 111 with the **base** code (not my changes). That pass is described below. It found the provider-return blocker that the first commit fixes.

## Commits

1. `319a30a8` fix(memory): bind provider return to the given units
2. `b8de109b` feat(removal): remove an in-place installation
3. (this report and raw data, docs commit)

## What changed

### Bridge: `lifeos_hook_bridge/memory_transition.py`
`MemoryTransition` built `ProfileServices` without `roles`, so it always required all three units (gateway, dashboard, pulse). An in-place host has only `hermes-gateway.service` plus the Pulse unit that LifeOS added. The provider return therefore failed at service review. It also hit `.lifeos-services/operation.json` journals whose role set differed. The transition now binds the roles of the units its caller passes, and it resumes only the bound Hermes roles (`dashboard`, `gateway` if present). If no units are passed, the managed behavior is unchanged.

### Release manager
- `inplace_services.profile_units(profile)`: returns `None` (meaning every standard role, the managed behavior) when there is no host record. Otherwise it returns the standard units that systemd loads from a definition file. It is used by the return workflow (`memory_workflow.execute`, `_cancel_preparation`), by `removal_preparation.returned`, and by removal preparation.
- New `inplace_removal.py`:
  - `selected()` binds to the job that `record['operation']` names. The job must be `applied`, format 2, with the same profile, installed root, version, commit, package hash, host source, and commit. It validates the integration package and both installed plugin trees against that job's `INTEGRATION.json`. It requires `inspect_host(..., record=load_record(profile))` to report `installed`, and on refusal it gives the first reason with its paths. It verifies the retained originals (`check_originals`) and Bun.
  - `host_plan()`: each record target must currently have its patched hash, or the plan refuses and names the path. Each target is restored from a verified stage copy of its original (the copy keeps the original mode), or deleted when `stock` is `None`. The plan also removes `<profile>/.lifeos-host` (it refuses if it contains files the record does not name), `lifeos-host.json`, and `<source>/.git/hermes-update-holds/lifeos.json` (holder must be `LifeOS`). Copies are used because ProgramTransaction re-checks sources during publication, and the originals directory is removed in the same transaction.
  - `check_host_files()`: before apply and rollback, it refuses with the relative path when a Hermes file is neither its reviewed patched state nor its restored original. ProgramTransaction's own error does not name paths.
  - `runtime()` / `command()`: the host runtime is `{'kind':'host','source','hermes'}`. Commands use the host's `hermes_cli._launchers.runtime_command(source, ..., code=...)` without a fixed interpreter. On the qualified layout this is the store Python, and `hermes_bootstrap` selects the current dependency generation at each start. I checked this on CT 111: the store Python imported `ruamel.yaml` and `tree_sitter` from the selected generation `3da1a48c...`. So the paths stay valid after each synchronization.
  - `synchronize()`: runs `dependency_plan.py synchronize` from the retained `recovery-manager` with the interpreter that `host_python()` resolves at run time. It records the lock package diff in `removal/<label>-packages.json`.
- `removal_preparation.prepare`: the host record selects the in-place branch. That branch prepares no stock runtime, checks no dashboard asset, and changes no launchers (`software()` gets an empty launcher map). It uses the native sources from the operation (`job/lifeos/LifeOS/install`, `request.runtime.reference`), adds the host plan, and binds services with `profile_units`. The consumer check also refuses any process that uses the host source or its environment and runs outside the bound or coordinator control groups. The plan stores `host` and `service_units`. The recovery command uses the host runtime. `stock_commit` is the host commit, and `stock_patches` is 0.
- `removal_workflow`: `_runtime()` selects the host or the stock runtime for launch, probe, and execute. Services use `service_units`. The result adds `dependencies` (the package diff).
- `memory_workflow.launch` / `_probe`: with a host runtime, `python=None` and no stock bytecode prefix.
- `removal_publication`: services use `service_units`. Apply synchronizes after `programs-published` (if that fails, the state stays `publishing` and recovery repeats it). Rollback synchronizes after restore, records a failure in `dependency-restore-failure.json`, and continues, as design section 4.2 says.
- `removal_services.prepare`: refuses with a clear message when Pulse is not bound. Before, this was a `KeyError`.
- `removal_generation.selected` (managed): also returns `native_source` and `reference`, with the same values as before.

## Tests

The suites ran with the frozen environment and the documented `PYTHONPATH`. The native memory fixtures need `LIFEOS_MEMORY_SOURCE` set to a patched LifeOS tree with `bun install` done. Without it, `test_memory_return.py`, `test_memory_transition.py`, `test_memory_export.py`, and many others error ("native LifeOS memory tools are unavailable" or "Cannot find package 'yaml'"). I copied the prepared tree from CT 111's update job to `/tmp/inplace-removal/lifeos-src/install` and ran `bun install --frozen-lockfile`.

Relevant suites, baseline (exported `2bfc5d42`) versus after, both with that source (`raw/baseline-set.txt`, `raw/after-set.txt`): identical except for the new tests.

- New or extended, all pass: `test_inplace_removal.py` (10 new), `test_memory_transition.py` (5, 1 new), `test_inplace_services.py` (7, 1 new), `test_removal_services.py` (5, 2 new).
- These fail the same way at baseline and after, from the environment:
  - `test_memory_transition_probe.py` (3): `No module named 'hermes_constants'` in the 0.7.3 Hermes on `PYTHONPATH`.
  - `test_removal_consumers.py` (1): `PermissionError /proc/<pid>/exe` on the workstation.
  - `test_removal_coordinator.py` (1): it refuses an `sshd-session` process of the workstation.
- Everything else in the set passes at baseline and after: return, export, profile services, every `test_removal_*`, `test_memory_removal_workflow`, host compatibility and record, in-place preparation, consumer scan, and dependency plan.

Full suite without `LIFEOS_MEMORY_SOURCE` (`raw/baseline.txt`): 182 of 426 files pass at baseline. The worktree comparison is in the "Full-suite comparison" section below.

## Container evidence before the stop (base code, not my changes)

CT 111 was at `installed-baseline`: in-place 0.7.3 test build, operation `66f533d9...`, 96 host targets (69 modified, 27 added), the gateway unit only, Pulse unit created, no `lifeos-memory.json`. The originals keep the original modes (68 at 0644 plus 1 at 0755, the same as the install journal's `before` modes).

1. I built `0.8.0-rc.1-2bfc5d42` (base), staged it, and ran `prepare update` then `apply`: state `applied` (job `f2a63794...`). The update path works. I planned to use it as the route to put my code on the host, because removal validates the installed plugin trees against the operation's `INTEGRATION.json`. A plain file copy would fail that check by design.
2. `hermes update --check` before removal: "In-place update is held by an integration that patches this install: LifeOS: ...".
3. Dashboard basic auth set with `hermes config set dashboard.basic_auth.{username,password_hash}` (scrypt hash from `plugins.dashboard_auth.basic.hash_password`). Hermes rewrote the YAML formatting of `config.yaml` when it did this.
4. Owner claim (`MemoryPreferences.claim(account='dashboard:basic:owner')`), then reverse export (preview, snapshot, plan, apply): `exported`, `ready_for_return: true`, 0 items.
5. Provider return workflow: `interrupted` at prepare. Diagnosis: `ProfileServices(profile, installed)` (all roles) refuses with "The profile service journal belongs to another profile or has invalid metadata", because the journal binds gateway and pulse only. A preview with all roles would also fail on the missing dashboard unit. Commit 1 fixes this. I have not re-run it on the host.

### What a never-activated install needs for the provider-return precondition

1. Dashboard basic auth with username `U`, so the owner is `dashboard:basic:U`. Removal preparation requires this for standalone recovery.
2. An owner claim (`POST /memory/owner`). It creates `lifeos-memory.json` with `ownership_enabled: false`. Without it, `memory_workflow.queue` cannot load the owner policy and nothing can be queued.
3. A reverse export (`/memory/export/preview`, `snapshot`, `plan`, `apply`), even with zero native facts.
4. A provider-return workflow on that export (prepare, then apply, which verifies with a fresh agent). It must end `verified`. On an in-place host this needs commit 1.
5. Then the removal workflow (`kind: removal`, `identifier` = return workflow, `signature` = return review signature, `disable_discord: true`).

The driver in `raw/driver.py` implements steps 2 to 5 (`claim`, `export`, `return`, `removal-prepare`, `removal-admit`). Note: during removal, the driver itself must not be a consumer of the host source. My preparation now refuses any process outside the bound units that uses the source. `removal-prepare` in the driver still waits by polling through Python from the source, so it would be refused. Change it to queue, exit, and poll `status.json` from the shell before using it.

## Pending end-to-end steps (when containers are usable)

1. Reset CT 111 to `installed-baseline`, then run `loginctl enable-linger owner; systemctl start user@1000.service`.
2. `redeploy-111.sh` from the worktree HEAD (the tree must be clean), then `run-111.sh p prepare update` and `apply <id>`.
3. Run `basic-auth`, then `claim`, `export`, and `return`. The return must end `verified`.
4. Run removal prepare, then apply. Check that the result has `stock_commit` = `71d34bad...`, `stock_patches` 0, and a `dependencies.removed` list that includes `tree-sitter` and `tree-sitter-bash`.
5. Check the success criteria:
   - `git -C ~/.hermes/hermes-agent status --porcelain` is empty.
   - `hermes update --check` reports no hold.
   - The `lifeos-release` and `lifeos-version` commands are gone.
   - `plugins.enabled` contains no LifeOS plugins.
   - `import tree_sitter` fails in the selected environment.
   - The gateway is active.
   - `~/.claude` user data is retained.
   - Diff `config.yaml` against the install job's `program-snapshot/before-N` for `config.yaml`. That file is the pre-install copy, so CT 110 is not needed.
6. Test a rollback and the recovery command (`removal/recover`).

## Open risks

- **Untested end to end.** None of the removal publication, synchronization, host-runtime launch, probe, or recovery command for the in-place path has run on a real host.
- **Configuration residue.** I expect the existing `removal_configuration` transformation to leave differences against the pre-install configuration. It sets `platforms.discord.enabled: false` (the existing contract) and `memory.memory_enabled` and `user_profile_enabled` to true. It keeps empty `plugins.enabled`, `disabled`, and `entries` lists if the install created them. The install also leaves `skills.external_dirs` minus the LifeOS entry. The host record does not hold the pre-install key values that design section 8 describes, so removal cannot restore only the recorded keys. That needs a record format change.
- **Lock diff only.** Synchronization records the package diff and does not enforce it. If another enabled plugin needs `tree-sitter`, it stays, and removal still succeeds.
- **Unrelated source edits block removal.** Removal requires host state `installed`, as the task said. So an unrelated tracked-file edit in the checkout also refuses removal (`modified_files`), not only an edit of a patch target.
- **Stale interpreter on other layouts.** On a layout without store Python, `runtime_command` falls back to `sys.executable`, which is the current generation's interpreter, and could become stale after synchronization. The qualified layout has store Python.
- **Empty hold directory.** `.git/hermes-update-holds/` stays as an empty directory after removal.
- **Activation not handled.** Activation (`ownership_setup.py`, `memory_cycle.py`) also builds `ProfileServices` with all roles, so ownership activation on an in-place host is probably broken in the same way. I did not change or test it.
- **Missing unit tests.** The selection after `validate_integration`, the source-consumer check, `synchronize`, and the host branches of launch, probe, and recovery command have no unit tests. They need a real host.

## Raw data

The `raw/` folder holds:
- `baseline.txt`: full suite at the base commit.
- `baseline-set-pinned-source.txt`: relevant suites with an unpatched LifeOS source.
- `baseline-set.txt` and `after-set.txt`: relevant suites with the prepared source, before and after.
- `after-full.txt`: full suite on the worktree.
- The e2e scripts: `driver.py`, `redeploy-111.sh`, `run-111.sh`, `remote-run.sh`, `runset.sh`, `runall.sh`.

## Full-suite comparison (no `LIFEOS_MEMORY_SOURCE`)

Baseline: 182 of 426 files pass. Worktree: 184 of 427 files pass (one new file). Diff of the per-file results:

- New or extended and passing: `test_inplace_removal.py` (10), `test_inplace_services.py` (7), `test_removal_services.py` (5).
- `test_memory_transition.py`: 4 errors at baseline, 5 after. All of them, including the new test, error with "native LifeOS memory tools are unavailable" without the source. With the source, all 5 pass.
- `test_prepare_sources.py`: it failed at baseline and passes after. `test_hook_evidence.py`: it had 1 skip at baseline and none after. Neither file depends on my changes, so I treat both as environment or timing variation.
- `test_removal_execution_source.py`: it fails the same way in both runs, a temporary directory cleanup `OSError` in the run without the source. With the source, it passes in both runs.
