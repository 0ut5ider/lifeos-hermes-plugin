# In-place installation design

Date: 2026-10-17. Status: draft for review. This document turns the accepted [in-place installation plan](in-place-installation-plan.md) into a concrete design. The plan states the requirements; this document states how the code meets them.

Evidence for the stock Hermes and release manager behavior below is in the [design mapping](agents/2026-10-17-in-place-design-mapping/). File references point to stock Hermes `v0.21.7` (`71d34bad`) or to this repository.

## 1. Decisions

| Decision | Source |
| --- | --- |
| Patching the owner's existing Hermes installation is the only installation path. | Owner, 2026-10-17 |
| No replacement Hermes runtime, now or as a fallback. | Owner, 2026-10-17 |
| The installer checks compatibility first and refuses with a specific reason. | Owner, 2026-10-17 |
| Development and daily move to a fresh stock Hermes Git installation, then receive the in-place installation. Their profile configuration, Discord setup, memory, and native LifeOS data stay. | Owner, 2026-10-17 |
| The first supported layout is a single-profile, user-owned Linux Git checkout at a qualified commit. | Plan |
| An 11th Hermes patch group adds generic update holds to `hermes update` admission. | This design, section 6 |
| The bridge's Python dependencies enter the owner's environment through Hermes's own environment manager. | This design, section 5 |

## 2. Release format

The release stays a GitHub release of `0ut5ider/lifeos-hermes-plugin` with tag `vX.Y.Z`. The certificate changes to format 2. A format 1 release is a managed-runtime release, and the in-place manager refuses it.

| Asset | Content | Approximate size |
| --- | --- | --- |
| `RELEASE-CERTIFICATE.json` | Format 2 certificate | 5 KB |
| `lifeos-integration-X.Y.Z-<commit8>.tgz` | `lifeos_hook_bridge/`, `optional/lifeos_release_manager/`, `VERSION`, `CHANGELOG.md`, `INTEGRATION.json` | 2 to 3 MB |

The archive does not contain Hermes, a stock Hermes archive, a prepared LifeOS tree, a frozen Python closure, or a compiled dashboard.

`INTEGRATION.json` records:

- `version` and `head` (the program commit).
- `plugin_files` and `manager_files`: exact SHA-256 maps of the two plugin trees.
- `host_compatibility_sha256`: the hash of `optional/lifeos_release_manager/host-compatibility.json`.
- `lifeos`: `{upstream, commit, tree_sha256, patches}`, where `tree_sha256` is the digest that `prepare_lifeos` produces after the capability record.

The format 2 certificate binds `version`, `program_commit`, `status: QUALIFIED`, the archive name, SHA-256, and size, `host_compatibility_sha256`, and the `lifeos` block. Qualification fields stay as in format 1. Authenticity is unchanged: HTTPS to GitHub, GitHub's asset digests, and the certificate's hash bindings. There is no signature today, and this design does not add one.

Installed 0.7.3 managers require `hermes-dashboard.tgz` and format 1. They refuse a format 2 release, so an old manager cannot misinstall a new release.

## 3. Bootstrap

1. The owner installs the release manager plugin with `hermes plugins install` and the repository subdirectory URL. Hermes uses a shallow, blobless, sparse clone of only that subdirectory. The manager has no Python dependencies.
2. The manager page shows the compatibility result (implemented).
3. **Install LifeOS** is available only when the result is `compatible`.

## 4. Operation lifecycle

The existing operation framework stays: one private job directory per operation under `<profile>/.lifeos-releases/<id>`, `request.json`, a sealed `plan.json`, owner review, admission, a detached worker, and the status and recovery actions. Only the program plan and the runtime inputs change.

### 4.1 Preparation (no active change)

1. Run the compatibility check against the running Hermes. Require `compatible` for a first installation or `installed` for an update (section 8).
2. Download and verify the certificate and the integration archive. Extract the archive and verify both file maps and the compatibility manifest hash.
3. Select the compatibility entry for the detected commit.
4. Stage the host files with `stage_host_files` into `job/host/{stock,patched}` (implemented). For an update, stage from the retained originals instead of the host (section 8).
5. Prepare LifeOS with `prepare_lifeos(..., expected_tree=certificate.lifeos.tree_sha256)` into `job/lifeos` (implemented).
6. Download Bun into `job/tools` with the existing pinned tool record.
7. Build a preview tree: copy the host's tracked files (`git ls-files -z`, reflink where possible) into `job/hermes-preview`, then overlay the staged patched files. The preview runs only preparation checks with the owner's interpreter: `hermes config check` on the generated configuration and the reference LifeOS installation. It never becomes a launcher target, and preparation deletes it after the checks.
8. For a first installation, install LifeOS into `job/reference-home/.claude` as the current release does.
9. Build the program plan (section 4.3), prepare the `ProgramTransaction`, and seal the plan. The review payload shows the Hermes version and commit, the 94 host files, the Python packages to add, the configuration keys, and the services that restart.

### 4.2 Apply (detached worker)

The dashboard launches the worker with `systemd-run --user`, because the worker stops the dashboard. The worker runs with the owner's Hermes interpreter and imports only the release manager, the bridge, and stdlib-only Hermes modules (`hermes_cli.update_lock`).

1. Take the LifeOS installation lock, the program lock, and the Hermes checkout lock (`UpdateLock(install_root=<source>)`). An update in progress refuses the operation.
2. Repeat the compatibility check. Require the same commit, the same per-file identities, and the same `config.yaml` hash as the review.
3. Stop the consumers (section 7). Refuse if any consumer cannot be stopped.
4. Publish the program plan with `ProgramTransaction.apply`.
5. Synchronize the environment (section 5).
6. Run the native LifeOS steps as today: native initialization for a first installation, then the governed mount when required.
7. Start the consumers that were running. Verify the result (section 7).
8. Record `applied`.

Any failure after step 3 restores the programs, synchronizes the environment back to the restored configuration, restores the mount, and resumes the services, as the current worker does.

### 4.3 Program plan

The plan uses `ProgramTransaction` for every change. It provides fsynced publication, retained before-copies, resumable application, and refusal of later edits.

| Target | Change |
| --- | --- |
| 94 Hermes source files | Stock to patched (26 added files have no before-copy) |
| `<profile>/plugins/lifeos-hook-bridge` | New directory |
| `<profile>/plugins/lifeos-release-manager` | Replace with the release's manager |
| `<profile>/config.yaml` | Enable both plugins; set the bridge `lifeos_source_dir` |
| `~/.local/bin/bun` | Pinned Bun |
| `<profile>/integration-release.json` | Release receipt, extended with the host identity |
| `<profile>/lifeos-host.json` | Host record (section 8) |
| `<profile>/.lifeos-host/originals/` | Retained original host files |
| `<install state>/update-holds/lifeos.json` | Update hold (section 6) |
| Native LifeOS files, settings, and dependencies | As today for an update |

The account launchers (`~/.local/bin/hermes`, `hermes-agent`, `hermes-acp`) and the service definitions are not changed. A first installation creates only the Pulse unit; it uses the owner's existing gateway and dashboard units (section 7).

## 5. Python dependencies

Hermes builds each environment as a generation under `<root>/installs/<key>/environments/<uuid>/venv`. It includes enabled plugins' `python_dependencies` as workspace members, and it selects the generation in `facts.json` (`pm/packages.py:430`, `pm/workspace.py`). The bridge declares four exact pins in `plugin.yaml`.

The worker publishes `config.yaml` with the bridge enabled, then runs `hermes pm install` for the profile. This is the explicit synchronization that `hermes update` also uses. It resolves the bridge member against the seed lock, builds a new generation, and selects it only when the build succeeds. A resolver conflict leaves the previous generation selected. The worker then rolls back the programs.

Rollback and removal publish the configuration without the bridge and synchronize again. That builds a generation without the bridge member. The previous generation is not reselected; Hermes has no generation history (stock-Hermes map, section 3).

Preparation reports the four pins against the installed packages (implemented in the compatibility check). It does not resolve a candidate generation, so an unexpected resolver conflict appears at apply time and causes a rollback.

## 6. Hermes updater coordination

`hermes update` stashes local changes, updates, and reapplies them, or parks them after a conflict (`update_cmd_stash.py`). No plugin hook or setting makes it refuse. The CLI, the update command, and the dashboard update action all call `evaluate_update_admission` (`hermes_cli/update_contract.py:82`).

The new patch group `hermes-update-hold.patch` adds a first admission layer. It reads `<install state>/update-holds/*.json`. A valid hold refuses the update with the hold's message. An unreadable or malformed hold also refuses, because an integrity defect is not permission to update. The patch is generic: any integration can place a hold. It changes `hermes_cli/update_contract.py` and adds one test file.

The LifeOS hold message tells the owner to remove LifeOS, or to wait for a release that qualifies the new Hermes version. The hold is part of the program plan, so rollback and removal delete it.

The installer cannot stop the owner from rerunning `install.sh` or editing files. The bridge detects that drift (section 9).

## 7. Consumers and restart

All Hermes processes import the checkout directly (`pm/environments.py`, `activate_dependencies`). The consumers are the gateway (which also runs cron and Kanban watchers), the dashboard or `serve`, ACP, CLI sessions, and separate cron or Kanban worker processes.

- The worker stops and restarts the supported units with `ProfileServices`: `hermes-gateway.service`, `hermes-dashboard.service`, and `com.lifeos.pulse.service`.
- Before publication, the worker scans `/proc` for this account's processes whose executable, command line, or current directory uses the Hermes source or its environment generations. Any process outside the stopped units' control groups refuses the operation, with the process identities shown. An interactive CLI session must be closed first.
- After restart, the worker requires a new main PID with a start time after publication for each restarted unit. It runs `hermes lifeos-version` and a host capability probe in fresh processes. The probe checks that `VALID_HOOKS` contains the patched hooks and that `REQUIRED_MIDDLEWARE_API_VERSION == 1`.

Python revalidates `.pyc` files by source size and modification time, so the publication of new source files invalidates old bytecode. The worker still removes the `__pycache__` entries of the changed modules before restart.

## 8. Host record, updates, and removal

`<profile>/lifeos-host.json` records the source path, the commit, the compatibility entry label, and each target's stock and patched hash. `<profile>/.lifeos-host/originals/` holds the original bytes and modes of the 68 modified files. Their hashes equal the manifest's stock hashes, so the originals are verifiable without the job directory.

The compatibility check gains an `installed` state. It applies when the record exists, the commit matches, and every target has its recorded patched hash. Every other case keeps its current refusal.

**Update LifeOS** and **Update plugin** stage the new patched files from the retained originals. For each target in either release, the desired content is the new patched file, or the original (or absence) when the new release no longer changes that path. The transaction moves from the recorded state to the new state. A Hermes commit change is refused unless the new release has an entry for the new commit and a qualified transition; this design does not implement Hermes version transitions.

**Removal** keeps the current order: a verified memory provider return, then software removal. The in-place removal plan restores the 94 host files from the originals, deletes the added files, removes the bridge and manager directories, removes the LifeOS configuration keys, removes the hold, the host record, and the receipts, and synchronizes the environment without the bridge. It does not prepare a stock runtime or change launchers. The configuration, `.env`, settings-hook, native-file, and service logic in the existing `removal_*` modules is reused; the generation and runtime selection is replaced.

## 9. Drift reporting

The bridge compares the host identity with `lifeos-host.json` at registration and in `hermes lifeos-version`. A difference produces the state `host_drift`, with the changed paths. The releases page shows it with a repair path: run the compatibility check, then remove or reinstall LifeOS. Lasting memory stays fail-closed, as today. This design does not change the turn policy when the host lacks the patched hooks.

## 10. Development and daily transition

1. Back up the profile, `~/.claude`, `~/.config/LIFEOS`, `~/.local/bin`, and the user units.
2. Stop the services.
3. Install stock Hermes `v0.21.7` with `install.sh --commit 71d34bad... --skip-setup` into `~/.hermes/hermes-agent`. Check first that the installer does not change `config.yaml`, `.env`, or the user units, and record which launchers it publishes.
4. Run the in-place operation in transition mode. LifeOS is already installed and the host is unpatched. The plan also points the account launchers at the stock installation if the installer did not.
5. Verify, then retain the managed job directories until the owner approves their removal.

The transition is rehearsed first on a clone of the development container.

## 11. Code structure

- New modules in the release manager: `host_compatibility.py` and `host_patches.py` (implemented), `inplace_preparation.py`, `inplace_plan.py`, `inplace_worker.py`, `host_record.py`, `consumer_scan.py`, and `inplace_removal.py`.
- Reused without change: `release_programs.py`, `release_operation.py`, `release_initialization.py`, `profile_services`, the locks, the memory administration chain, and `MountTransaction`.
- Changed: `release_catalog.py` (format 2), `cli.py` and the dashboard API (dispatch to the in-place path), the releases page, `scripts/` (a new release builder and certifier), and the bridge (drift reporting and the update-hold patch).
- The managed-runtime code stays until development and daily complete the transition. Deleting it then is a separate change for owner approval.

## 12. Verification

- Unit tests for every new module, with disposable real Git repositories and real files.
- A real-service test in a disposable account: stock install at the qualified commit, extra plugins and tools, installation, update, interruption at each journal state, rollback, removal, and `hermes update` refusal.
- A disposable Proxmox container: the GitHub plugin URL, the dashboard buttons, and a loopback release server before publication. A published prerelease follows only with owner approval.
- A rehearsal of the development transition on a clone.
- Independent review of the design and the implementation.

## 13. Risks

- **Dirty-tree completion.** The patched tree is dirty, so `_tree_matches_completed_stamp` is false (`hermes_cli/venv_sync.py:312`). When the environment is stale or a completion marker is pending, the next launch runs Hermes's completion step once. Installed tests must cover this.
- **Shared environment.** The environment is shared by every profile on the checkout. Single-profile admission limits this.
- **Third-party plugins.** The patches change plugin dispatch for every plugin. Qualification uses representative extra plugins; it cannot prove every plugin.
- **Resolver conflicts.** They appear only at apply time and cause a rollback (section 5).
- **No release signature.** This risk is unchanged from the current releases.
