# In-place installation design

Date: 2026-10-17. Status: revised after the [independent design review](agents/2026-10-17-in-place-design-review/in-place-design-review.md); section 14 lists the resolutions. Amended after the [PR 40 code review](agents/2026-10-17-pr40-code-review/round1-fix-plan.md) to match the code; section 15 lists the amendments. This document turns the accepted [in-place installation plan](in-place-installation-plan.md) into a concrete design. The plan states the requirements; this document states how the code meets them.

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
| When the dashboard or gateway runs outside a user service, the review offers to create the standard user unit for it. Without that choice, the installer refuses. | Owner, 2026-10-17 |
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
- `lifeos`: `{upstream, commit, tree_sha256}`, where `tree_sha256` is the digest that `prepare_lifeos` produces after the capability record. The block has no `patches` field. The LifeOS patches are files under `lifeos_hook_bridge/patches/`, so `plugin_files` binds them.

The format 2 certificate binds `version`, `program_commit`, `status: QUALIFIED`, the archive name, SHA-256, and size, `host_compatibility_sha256`, and the `lifeos` block. Qualification fields stay as in format 1. Authenticity is unchanged: HTTPS to GitHub, GitHub's asset digests, and the certificate's hash bindings. There is no signature today, and this design does not add one.

Each entry of `host-compatibility.json` qualifies one Hermes commit. It holds:

- `label`, `commit`, `patches` (name and SHA-256 of each Hermes patch group), and `files` (the stock and patched hash of each target).
- `python`: the major.minor interpreter version that runs Hermes at that commit, read from the stock `pm/lock.json`.
- `capabilities`: `{hooks, middleware_api}`. `hooks` names the plugin hooks that the patches add. `middleware_api` is the required `REQUIRED_MIDDLEWARE_API_VERSION`.
- `known_conflicts`: optional. Each item is one sentence about a known conflict at that commit. The review shows the list.

`scripts/build_host_compatibility.py` writes the manifest from the exact stock archive and the distributed patches.

Installed 0.7.3 managers require `hermes-dashboard.tgz` and format 1. They refuse a format 2 release, so an old manager cannot misinstall a new release.

## 3. Bootstrap

1. The owner installs the release manager plugin with `hermes plugins install` and the repository subdirectory URL. Hermes uses a shallow, blobless, sparse clone of only that subdirectory. The manager has no Python dependencies.
2. The manager page shows the compatibility result (implemented).
3. **Install LifeOS** is available only when the result is `compatible`.

## 4. Operation lifecycle

The existing operation framework stays: one private job directory per operation under `<profile>/.lifeos-releases/<id>`, `request.json`, a sealed `plan.json`, owner review, admission, a detached worker, and the status and recovery actions. Only the program plan and the runtime inputs change.

### 4.1 Preparation (no active change)

1. Run the compatibility check against the running Hermes, before any download. Require `compatible` for a first installation or `installed` for an update (section 8). An interpreter other than the entry's `python` refuses with `unsupported_interpreter`. A host record that cannot be read or validated refuses with `invalid_host_record` (state `host_drift`), and the message names the record.
2. Download and verify the certificate and the integration archive. Extract the archive and verify both file maps and the compatibility manifest hash.
3. Select the compatibility entry for the detected commit.
4. Stage the host files with `stage_host_files` into `job/host/{stock,patched}` (implemented). For an update, stage from the retained originals instead of the host (section 8).
5. Prepare LifeOS with `prepare_lifeos(..., expected_tree=certificate.lifeos.tree_sha256)` into `job/lifeos` (implemented).
6. Download Bun into `job/tools` with the existing pinned tool record.
7. Build a preview tree: copy the host's tracked files (`git ls-files -z`, reflink where possible) into `job/hermes-preview`, then overlay the staged patched files. The capability probe (section 7) runs against the preview with the host interpreter. Preparation also uses the preview as the source for the reference LifeOS installation. The preview stays in the job until apply or rollback. Apply checks its fingerprint, and the program review runs the configuration stage on it. It never becomes a launcher target: the service environment of an in-place operation drops `PYTHONPATH`. The worker deletes it after `applied` or `rolled_back`.
8. For a first installation, install LifeOS into `job/reference-home/.claude` as the current release does.
9. Build the program plan (section 4.3), prepare the `ProgramTransaction`, and seal the plan. The program review writes `job/inplace-review.json`: every configuration key that changes between the current and the generated `config.yaml`, and, for an update, the targets that the new release adds, changes, or returns to their originals. The review payload shows the Hermes version and commit, the changed and added host files, the configuration keys, the update difference, the known conflicts, the Python packages to add, and the services that restart.

### 4.2 Apply (detached worker)

The dashboard launches the worker with `systemd-run --user`, because the worker stops the dashboard. The worker runs with the owner's Hermes interpreter and imports only the release manager, the bridge, and stdlib-only Hermes modules (`hermes_cli.update_lock`).

1. Take the LifeOS installation lock, the program lock, and the Hermes checkout lock (`UpdateLock(install_root=<source>)`). An update in progress refuses the operation.
2. Repeat the compatibility check. Require the same commit, the same per-file identities, and the same `config.yaml` hash as the review.
3. Stop the consumers (section 7). Refuse if any consumer cannot be stopped.
4. Publish the program plan with `ProgramTransaction.apply`.
5. Synchronize the environment (section 5).
6. Run the native LifeOS steps as today: native initialization for a first installation, then the governed mount when required.
7. Start the consumers that were running. Verify the result (section 7). The worker also requires `config.yaml` to keep its `memory.provider` value unless the operation owns that change, as a first installation does.
8. Record `applied`.

Any failure after step 3 runs, in this order: restore the mount, restore the programs, synchronize the environment against the restored configuration, then resume the services. The mount comes first because `config.yaml` is both a mount target and a program target (`release_worker.py:434-448`). A failed environment synchronization does not stop the rollback; it is recorded, and recovery repeats it.

### 4.3 Program plan

The plan uses `ProgramTransaction` for every change. It provides fsynced publication, retained before-copies, resumable application, and refusal of later edits.

| Target | Change |
| --- | --- |
| 96 Hermes source files | Stock to patched (27 added files have no before-copy) |
| `<profile>/plugins/lifeos-hook-bridge` | New directory |
| `<profile>/plugins/lifeos-release-manager` | Replace with the release's manager |
| `<profile>/config.yaml` | Enable both plugins; set the bridge `lifeos_source_dir` |
| `~/.local/bin/bun` | Pinned Bun |
| `<profile>/integration-release.json` | Release receipt, extended with the host identity |
| `<profile>/lifeos-host.json` | Host record (section 8) |
| `<profile>/.lifeos-host/originals/` | Retained original host files |
| `<source>/.git/hermes-update-holds/lifeos.json` | Update hold (section 6) |
| Native LifeOS files, settings, and dependencies | As today for an update |

Outside the transition (section 10), the account launchers (`~/.local/bin/hermes`, `hermes-agent`, `hermes-acp`) and the service definitions are not changed. A first installation creates only the Pulse unit, and it neither enables nor starts that unit, as the managed release did. It uses the owner's existing gateway and dashboard units (section 7).

## 5. Python dependencies

Hermes builds each environment as a generation under `<root>/installs/<key>/environments/<uuid>/venv`. It includes enabled plugins' `python_dependencies` as workspace members, and it selects the generation in `facts.json` (`pm/packages.py:430`, `pm/workspace.py`). The bridge declares four exact pins in `plugin.yaml`.

The worker publishes `config.yaml` with the bridge enabled, then calls `pm.client.sync_venv(explicit=True, project_root=<source>)` with the host interpreter, plugin discovery from the configuration, and no plugin eviction. It resolves the bridge member against the current resolved lock, builds a new generation, and records it in `facts.json` only when the build succeeds (`pm/install.py:769-855`, `pm/packages.py:484-486`). A failure leaves the previous generation selected, and the worker rolls back. The worker does not run `hermes pm install`: that command also reinstalls tools, downloads optional defaults, and republishes launchers (`pm/cli.py:343-398`).

Rollback and removal publish the configuration without the bridge and synchronize again. That builds a generation without the bridge member. The previous generation is not reselected; Hermes has no generation history (stock-Hermes map, section 3).

Preparation proves the resolution before review. It generates a throwaway workspace with the currently enabled plugin members and the staged bridge, seeds it with the current resolved lock, and runs `uv lock` without installing anything. It refuses when any package of the current lock would change version or disappear. The review lists the added packages. The worker records the selected generation's lock hash at review and refuses at apply if it changed.

## 6. Hermes updater coordination

`hermes update` stashes local changes, updates, and reapplies them, or parks them after a conflict (`update_cmd_stash.py`). No plugin hook or setting makes it refuse. The CLI, the update command, and the dashboard update action all call `evaluate_update_admission` (`hermes_cli/update_contract.py:82`).

The new patch group `hermes-update-hold.patch` adds a first admission layer. It reads `<git common dir>/hermes-update-holds/*.json`, beside Hermes's own checkout lock and outside the working tree. A valid hold refuses the update with the hold's message. An unreadable or malformed hold also refuses, because an integrity defect is not permission to update. The patch is generic: any integration can place a hold. It changes `hermes_cli/update_contract.py` and adds one test file.

The LifeOS hold message tells the owner to remove LifeOS, or to wait for a release that qualifies the new Hermes version. The hold is part of the program plan, so rollback and removal delete it.

The installer cannot stop the owner from rerunning `install.sh`, running `hermes pm update`, or editing files. The bridge detects that drift (section 9). The hold does not hide the passive update banner or the dashboard check's `can_apply` value; the update itself refuses.

## 7. Consumers and restart

All Hermes processes import the checkout directly (`pm/environments.py`, `activate_dependencies`). The consumers are the gateway (which also runs cron and Kanban watchers), the dashboard or `serve`, ACP, CLI sessions, and separate cron or Kanban worker processes.

- Preparation inventories the profile's consumers: the stock gateway unit (`hermes-gateway.service`, created by `hermes gateway install`), a dashboard unit, the Pulse unit, and any Hermes process outside a unit. A gateway or dashboard that runs outside a unit is shown in the review with an offer to create its standard user unit. The owner can accept, or close the process and prepare again; otherwise the installer refuses.
- The worker stops and restarts the bound units with `ProfileServices`, extended to bind only the roles that exist on the host. Preparation records each bound unit's active state and enabled state (`UnitFileState`) in the in-place plan. The `ProfileServices` journal format does not change, because installed bridges share it.
- Before publication, the worker scans `/proc` for this account's processes whose executable, command line, or current directory uses the Hermes source or its environment generations. Any process outside the stopped units' control groups refuses the operation, with the process identities shown. An interactive CLI session must be closed first.
- After restart, the worker checks each restarted or created unit. The unit must be active, with a main process that started after the drain that precedes publication. Its `UnitFileState` must equal the recorded value. The worker runs `hermes lifeos-version` and a host capability probe in fresh processes. The probe runs `python -I -B` with the host interpreter. It requires the entry's `python` version, every hook of `capabilities.hooks` in `VALID_HOOKS`, and `REQUIRED_MIDDLEWARE_API_VERSION` equal to `capabilities.middleware_api`. The same probe runs against the preview at preparation. The bridge writes a registration receipt with its process ID and registration mode; the worker requires a `patched` receipt from the restarted gateway's main PID.

Python revalidates `.pyc` files by source size and modification time, so the publication of new source files invalidates old bytecode. The worker still removes the `__pycache__` entries of the changed modules before restart.

## 8. Host record, updates, and removal

`<profile>/lifeos-host.json` records the source path, the commit, the compatibility entry label, and each target's stock and patched hash. It holds nothing else. `<profile>/.lifeos-host/originals/` holds the original bytes and modes of the 69 modified files (96 targets, 27 added). Their hashes equal the manifest's stock hashes, so the originals are verifiable without the job directory. `<profile>/.lifeos-host/configuration.json` holds the before-values of the configuration keys LifeOS changes. The worker writes it at the end of a successful apply. Each later operation keeps the earliest before-value of a key. A restore or a recovery that rolls back records the restored configuration as the installed value of each recorded key.

The compatibility check gains an `installed` state. It applies when the record exists, the commit matches, and every target has its recorded patched hash. Every other case keeps its current refusal.

**Update LifeOS** and **Update plugin** stage the new patched files from the retained originals. For each target in either release, the desired content is the new patched file, or the original (or absence) when the new release no longer changes that path. The transaction moves from the recorded state to the new state. A Hermes commit change is refused unless the new release has an entry for the new commit and a qualified transition; this design does not implement Hermes version transitions.

**Removal** keeps the current order: a verified memory provider return, then software removal. The in-place removal plan restores the 69 modified host files from the originals, deletes the 27 added files, removes the bridge and manager directories, removes the LifeOS configuration keys, removes the hold, the host record, and the receipts, and synchronizes the environment without the bridge. It does not prepare a stock runtime or change launchers. The configuration, `.env`, settings-hook, native-file, and service logic in the existing `removal_*` modules is reused; the generation and runtime selection is replaced.

Before and after each operation the worker records an inventory: the other plugins' directory digests, the enabled plugins, and the selected environment's locked packages. Verification requires each item to be unchanged, except the packages that the review adds. `check_preserved` protects the rest of `config.yaml`. It refuses any change under `toolsets`, `mcp_servers`, `model`, `providers`, `custom_providers`, `fallback_model`, `auxiliary`, and `platforms`. These roots have no planned difference, so the review lists them only through the configuration keys. After restart the worker also checks memory authority: `memory.provider` must not change unless the operation owns that change (section 4.2).

Removal keeps the native LifeOS data, `lifeos-memory.json`, and the removal selection, so the owner can roll the removal back. Installing LifeOS again after a verified removal is not supported: preparation refuses while the removal selection exists, and a fresh installation refuses an existing native destination. This limit predates the in-place design. A supported reinstall needs an owner decision on how to reattach or set aside the retained data.

## 9. Drift reporting

Three places report drift:

- The releases page and `hermes lifeos-release compatibility` run the compatibility check against the host record. A changed patched file gives `host_drift` with the changed paths. Edited, untracked, or Git-hidden files give their own reasons. A profile that no longer enables the bridge gives `bridge_disabled`, because a boot-time environment synchronization can evict a plugin (`hermes_cli/venv_sync.py:602`, `pm/plugin_eviction.py`). A damaged record gives `invalid_host_record`.
- `hermes lifeos-version` adds a `host` block. Without a record it is `null`. With a record it is `{state, source, changed}`, where `state` is `installed` or `host_drift` and `changed` lists each recorded file whose hash differs, that is missing, or that is a link. A damaged record gives `{state: host_drift, reason}`. The worker's fresh `lifeos-version` run after publication refuses `host_drift`.
- At registration the bridge writes only the registration receipt (section 7). It does not compare the host with the record.

No drift report compares `memory.provider`. The worker checks it after restart (section 8). The releases page shows drift with a repair path: run the compatibility check, then remove or reinstall LifeOS. Lasting memory stays fail-closed, as today. This design does not change the turn policy when the host lacks the patched hooks.

## 10. Development and daily transition

1. Back up the profile, `~/.claude`, `~/.config/LIFEOS`, `~/.local/bin`, and the user units.
2. Stop the services.
3. Install stock Hermes `v0.21.7` with `install.sh --commit 71d34bad... --skip-setup` into `~/.hermes/hermes-agent`. `--skip-setup` skips `hermes setup` and `gateway install`. The installer's products stage still runs configuration migration and skills synchronization on the live profile, and its environment build includes the enabled bridge, so the backup in step 1 is required and the rehearsal checks the result. The installer does not repoint launchers that another owner created (`hermes_cli/_launchers.py:505-548`).
4. Run the in-place operation in transition mode: LifeOS is installed and the host is unpatched. The transition plan points the account launchers at the stock installation unconditionally. A managed gateway unit runs the managed launcher, so preparation also generates the unit that `hermes gateway install` writes for the stock checkout (`hermes_cli.gateway.generate_systemd_unit`). The program transaction publishes it with the launchers. Preparation reads every start, reload, and stop command of the gateway, dashboard, and Pulse units from `systemctl --user show`. It refuses the transition while such a command runs the managed runtime through a program other than the three account commands. A gateway unit that preparation replaces is exempt, but a drop-in that sets one of its commands refuses, because the drop-in stays after the replacement. Another Hermes checkout can own such a forwarder, for example `~/workspace/hermes-agent/.hermes/bin/hermes` on development, and that checkout can rewrite it later. The owner points the unit at `~/.local/bin/hermes` first (review item R2-1, decided by the owner on 2026-10-18). The service controller then rebinds the stopped gateway role to the reviewed unit file, so resume, rollback, and recovery accept either the managed or the stock definition. Preparation refuses the transition when another unit still runs the managed runtime. The registration receipt names the Hermes checkout that the gateway imports, and the worker requires the stock checkout.
5. Verify, then retain the managed job directories until the owner approves their removal.

The transition is rehearsed first on a clone of the development container.

## 11. Code structure

- New modules in the release manager: `host_compatibility.py`, `host_capabilities.py`, `host_patches.py`, `host_record.py`, `host_configuration.py`, `integration_package.py`, `dependency_plan.py`, `inplace_preparation.py`, `inplace_plan.py`, `inplace_services.py`, `inplace_worker.py`, `consumer_scan.py`, and `inplace_removal.py`. The bridge adds `registration.py`.
- Reused without change: `release_programs.py`, `release_operation.py`, `release_initialization.py`, `profile_services`, the locks, the memory administration chain, and `MountTransaction`.
- Changed: `release_catalog.py` (format 2), `cli.py` and the dashboard API (dispatch to the in-place path), the releases page, `scripts/` (`build_host_compatibility.py`, `build_integration_release.py`, and `local_release_server.py`), and the bridge (drift reporting in `hermes lifeos-version` and the update-hold patch).
- The managed-runtime code stays until development and daily complete the transition. Deleting it then is a separate change for owner approval.

## 12. Verification

- Unit tests for every new module, with disposable real Git repositories and real files.
- A real-service test in a disposable account: stock install at the qualified commit, extra plugins and tools, installation, update, interruption at each journal state, rollback, removal, and `hermes update` refusal.
- A disposable Proxmox container: the GitHub plugin URL, the dashboard buttons, and a loopback release server before publication. A published prerelease follows only with owner approval.
- A rehearsal of the development transition on a clone.
- Independent review of the design and the implementation.

## 13. Risks

- **Dirty-tree completion.** The patched tree is dirty, so `_tree_matches_completed_stamp` is false (`hermes_cli/venv_sync.py:312`). When the environment is stale or a completion marker is pending, the next launch runs Hermes's completion step once. Installed tests must cover this.
- **Shared environment.** The environment is shared by every profile on the checkout. Single-profile admission limits this. It is the first supported layout. The check refuses a named profile and a `profiles/` directory with entries. A second `HERMES_HOME` elsewhere that uses the same checkout is found only while one of its processes runs (section 7).
- **Third-party plugins.** The patches change plugin dispatch for every plugin. Qualification uses representative extra plugins; it cannot prove every plugin.
- **Resolver conflicts.** They appear only at apply time and cause a rollback (section 5).
- **No release signature.** This risk is unchanged from the current releases.

## 14. Review resolutions

| Review finding | Resolution |
| --- | --- |
| `hermes pm install` is the wrong synchronization | Section 5: `pm.client.sync_venv(explicit=True, project_root=...)` |
| `ProfileServices` cannot bind a stock host | Section 7: bind only existing roles; record enabled state |
| The launching dashboard is an uncontrolled consumer | Owner decision: offer to create the standard unit, else refuse |
| Resolver conflicts deferred to apply time | Section 5: throwaway-workspace lock at preparation |
| Rollback order | Section 4.2: mount, programs, environment, services |
| Hold location | Section 6: `<git common dir>/hermes-update-holds/` |
| No preparation-time consumer inspection | Section 7: inventory at preparation, shown in review |
| Byte-managed `config.yaml` and key-level removal | Section 8: record key before-values; removal restores keys |
| Plugin eviction at boot-time synchronization | Section 9: drift reports bridge disablement and provider changes |
| Manifest counts | 96 targets, 27 added, 69 modified |
| Transition launchers and live-profile effects | Section 10 |
| Plan gaps: inventory, tested scope, registration proof, enabled state | Sections 7 and 8; the page states the tested scope |

## 15. Code review amendments

The PR 40 code review compared this design with the code. These sections now describe the code.

| Review finding | Amendment |
| --- | --- |
| C3: the preview stays until apply | Section 4.1, step 7 |
| C4: `INTEGRATION.json` has no `lifeos.patches` | Section 2 |
| C6: configuration before-values live in a separate file | Section 8 |
| A4: drift reporting | Section 9: the page, `hermes lifeos-release compatibility`, and `hermes lifeos-version` report drift; registration writes only the receipt |
| A8: inventory scope | Section 8: `check_preserved` roots; memory provider check after restart |
| A9: shared checkouts | Section 13: single-profile admission is the first supported layout |
| B1: service launchers | Section 10; review item R2-1, preparation refuses |
| A2, A3, A7: restart checks, enabled state, manifest qualification | Sections 2 and 7 |
| A5, A6: review contents | Section 4.1, step 9 |
| C2, C5: compatibility first, damaged record | Section 4.1, step 1 |
