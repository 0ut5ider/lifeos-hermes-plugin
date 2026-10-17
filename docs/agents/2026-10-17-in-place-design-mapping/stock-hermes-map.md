<!-- Saved by the parent agent on 2026-10-17 from the subagent's final reply; the subagent could not write files. -->

I could not write `stock-hermes-map.md`. This session is read-only: it has no file-write tool, and creating files is prohibited. The report below is the full text, ready to paste into that file with the header: date 2026-10-17, role "read-only code mapper", model Sonnet 5.5, question as given.

Everything is from reading the source at `/home/outsider/agent-scratch/hostcompat/hermes-agent`. I ran no code. Anything I did not read directly is marked **(inferred)**. Paths are relative to that root. I read `HERMES_HOME` as `~/.hermes` by default.

## Items that bear directly on in-place patching

1. **Your patches make the tree dirty.** Git status decides local-change detection (item 2). Your 26 added files are untracked, so `git stash push --include-untracked` takes them too.
2. **The install stamp records `dirty`.** `write_source_stamp` writes it from `_git_version_info(include_untracked=True)` (`hermes_cli/source_stamp.py`). `_tree_matches_completed_stamp` returns False for any stamp without `dirty: false` (`hermes_cli/venv_sync.py:~320`).
3. **Running processes will not notice your patch.**
   - The staleness check (`gateway/code_skew.py`) compares only the git HEAD/ref fingerprint, so edits to the working tree do not register.
   - The bytecode sweep (item 8) is also HEAD-keyed.
   - After patching you must restart processes yourself and clear `__pycache__` yourself.
4. **Old environment generations are cleaned up, not versioned.** There is no built-in rollback to an older generation (item 3).
5. **Plugin dependency sets are shared across profiles.** One environment serves every live profile, built from the union of all their plugin selections (item 3).
6. **The default update channel is a release, not `main`.** An official-origin checkout updates to the latest GitHub release commit, detached, even though `install.sh` clones `main` (item 2).

## 1. Default install layout

**`scripts/install.sh`** is a staged installer. The stages are `prerequisites`, `repository`, `venv`, `python-deps`, `config`, `products`, `setup`, `gateway`, `complete` (`install.sh:~336`).

- **Checkout location:** `INSTALL_DIR="${HERMES_INSTALL_DIR:-$HERMES_HOME/hermes-agent}"` (`install.sh:~100`).
  - `HERMES_HOME` defaults to `$HOME/.hermes`.
  - There is no root-specific path in the script.
  - `/usr/local/lib/hermes-agent` appears only as a second "blessed root" for adopting stampless checkouts (`hermes_cli/post_update.py`, `step_adopt_blessed_checkout`).
- **Clone:** `git clone --filter=blob:none --branch main <url>` (`install.sh:~690`).
  - It is blobless, not shallow, and uses the repo URL `HERMES_REPO_URL`, default `https://github.com/NousResearch/hermes-agent.git`.
  - It clones into a staging dir and `mv`s it into place.
  - The script itself adds no tag fetch, but a plain clone brings the tags reachable from `main`.
  - `--commit SHA` detaches at that commit.
  - It sets `maintenance.commit-graph.enabled=false`, `gc.writeCommitGraph=false` and `fetch.writeCommitGraph=false` in the checkout's git config.
- **Re-running on an existing checkout:** it fetches `origin/main` and checks out `main`.
  - A dirty tree is stashed as `hermes-install-autostash-<ts>`.
  - If it cannot fast-forward, it saves the old tip under `refs/hermes-update-backups/...` and runs `git reset --hard origin/main`.
- **Environments:** the installer creates no venv in the checkout.
  - `stage_venv` only fetches the pinned `uv` (to `$HERMES_RUNTIME_DIR` or `$HERMES_HOME/tools/uv-<ver>-<target>/`) and a bootstrap Python.
  - Then `python -m pm.cli install` builds the real environment (item 3).
- **Products and launchers:** the `products` stage runs `hermes_cli/source_completion.py`.
  - It publishes launchers, builds products (including the web UI), and runs maintenance.
  - The launcher is `<checkout>/.hermes/bin/hermes`; `install.sh` itself calls it for `setup` and `gateway install`.
  - `expose_cli` (`hermes_cli/_launchers.py:738`) exposes the command on PATH. I read only the sealed-bundle docstring naming `~/.local/bin/{hermes,hermes-agent,hermes-acp}`. For a source install, `~/.local/bin` is **(inferred)**. `install.sh` `wire_shell_path` appends `~/.local/bin` to the shell rc files.
- **Config stage:** it creates `cron sessions logs pairing hooks image_cache audio_cache memories skills` under `$HERMES_HOME`. It copies `.env.example` to `.env` and `cli-config.yaml.example` to `config.yaml` if they are absent.
- **Receipts:** `stage_complete` writes `<checkout>/.hermes-bootstrap-complete`.
  - Its fields are `{schemaVersion:1, pinnedCommit, pinnedBranch, completedAt}`.
  - `refresh_bootstrap_receipt` updates it after every stamp write, only if the file already exists.
  - A failed install also leaves `$HERMES_HOME/telemetry/shared_metrics/pending_installs/<id>.json`, and the install log is `$HERMES_HOME/logs/install.log`.
- **`install-stamp.json` for a Git install:** `<checkout>/install-stamp.json`, written by `write_source_stamp` after a fully successful completion tail (`hermes_cli/source_stamp.py:15`):
  ```
  schemaVersion 2, commit, commitDate, branch, builtAt, dirty,
  source "git", distribution null, updateMechanism "self",
  baseVersion, displayVersion, distance, payload "bootstrap", tag null
  ```
  - `adoptedAt` is added if the stamp came from boot-time adoption.
  - If git cannot identify the tree, the stamp is deleted.
  - The write is atomic (temp file, `os.replace`, fsync).
- **`hermes_bootstrap.py` is not an installer.** It is the per-process entry hardening: Windows UTF-8, Happy Eyeballs sockets, `harden_import_path`, scratch `TMPDIR`, and `_settle_interrupted_update`.
- **`hermes_cli/boot_bootstrap.py`** runs home maintenance once per (install, profile, git HEAD).
  - The record is `<default root>/installs/<key>/bootstrap/<profile>.json`, with an `O_EXCL` lock file next to it.
  - It runs `post_update.BOOT_HOME_STEPS`: adopt checkout, migrate config, state-db guard, drop plugin catalog cache, `expose_cli`.
  - The identity is `git rev-parse HEAD`, so working-tree patching does not retrigger it.
- **Systemd units from `hermes gateway install`** (`hermes_cli/gateway.py`):
  - The name is `hermes-gateway.service` for the default home, `hermes-gateway-<profile>.service` for a profile, and `-<8-hex hash>` for a custom home.
  - The user unit goes in `$XDG_CONFIG_HOME/systemd/user`; `--system` goes in `/etc/systemd/system`.
  - `ExecStart` is the install's launcher running `gateway run`. `HERMES_HOME` is pinned in `Environment=`, and `HERMES_SUPERVISED_CHILD=1` is set.
  - `Restart=always`, `RestartSec=5`, `KillMode=mixed`, `ExecReload=kill -USR1 $MAINPID`, and `ExecStopPost` runs `gateway.cgroup_cleanup`.
- **Dashboard units:** stock Hermes recognises `hermes-dashboard.service` and `hermes-serve[-profile].service` but does not generate them. The only mentions are in `main_dashboard.py:82`, `update_cmd_fleet.py` and `update_inventory.py`. A user or an app creates those units.

## 2. `hermes update`

**Entry** (`hermes_cli/main.py:2403`, `cmd_update`):
- It retargets to the owning install.
- `_update_preflight_handled` (`main.py:~2330`) then runs these checks:
  - `--install-id` and `--set-channel` are handled first.
  - `is_managed()` refuses.
  - `--plan` prints the runtime inventory read-only.
  - `evaluate_update_admission` returns exit 2 for any of these:
    - Stamp `source == "commit-build"`.
    - A valid or invalid image-provenance marker.
    - A sealed tree (no `.git`) whose stamp `distribution` is `desktop-app`, `docker`, `nix` or `apt-termux`.
    - Termux.
    - Docker, Nix or apt detection.
  - `--check` reports and exits.
- **Refusal conditions that apply to you.**
  - A `.git` entry is what makes a tree updatable. Keep `.git`, and do not set `source: commit-build` or a non-`self` `updateMechanism`.
  - `update_channel.py` treats `updateMechanism: external` as having no channel, and the launcher publishers skip such installs.
  - I found no plugin hook, `plugins.*` setting, or marker file that makes `hermes update` refuse.
  - A git operation in progress (merge, rebase and so on) does refuse with exit 1 (`update_cmd.py:1803`).
- **Locking** (`hermes_cli/update_lock.py`, `UpdateLock`):
  - **Marker file:** `<default hermes root>/.hermes-update-in-progress`, the same path for all profiles.
    - Its body is `pid\nstarted_at\nct:<create time>\n[delegate:...]`.
    - It is live while the pid is alive and the creation time matches.
    - Only a v1 marker, which carries no creation time, ages out (after 20 minutes).
    - It is shared with the Tauri/Electron updaters.
    - `HERMES_UPDATE_HANDOFF_PID` lets a parent updater's lock be adopted.
  - **Checkout lock:** a kernel `flock` on `<git common dir>/hermes-update.lock` (`<root>/.hermes-update.lock` for non-git installs).
    - It is held for the whole update process tree, and the completion children inherit the fd.
    - A dead marker over a held checkout lock is refused and kept.
  - **Exit code:** a contended lock exits with code 2 (`UPDATE_EXIT_CONCURRENT`).
  - **Who else takes the lock:**
    - `source_completion.complete_source_checkout`, which is also the install tail.
    - `venv_sync.prepare_launch`, which uses a marker-only claim (`checkout_first=False`) and takes the checkout lock only to mutate.
    - Your installer should take `UpdateLock(install_root=<checkout>)`. It is stdlib-only and importable as `hermes_cli.update_lock`.
- **Channel, pin and target** (`update_channel.py`, `source_releases.py`, `update_cmd_check.select_apply_target`):
  - **Default channel:**
    - For an official-origin checkout, the default is `stable`.
    - `stable` is the latest published GitHub release (strict `vX.Y.Z`), verified against origin.
    - Forks and mirrors default to `main`.
  - **Per-install override:** `update.installs.<sha16 of checkout path>.channel` in `config.yaml`, set with `hermes update --set-channel`.
  - **`--branch`:** this bypasses channel selection.
  - **Forward-only:** a checkout that already contains the release stays at its HEAD (`forward_only` via `_head_containing`).
  - **Release fetch:** the update fetches only that commit (`fetch --no-tags origin <sha>`) and lands detached at it.
  - **Tags refreshed afterwards:** `fetch_full_commit_graph` fetches `refs/tags/v*` in the maintenance tail.
  - **No setting disables updating,** other than the admission gates above. `updates.check` only controls passive banner checks.
- **Local changes** (`update_cmd_stash.py`):
  - **Detection:** `git status --porcelain -z` on the checkout. Anything not ignored counts.
    - Ignored files are never stashed: `venv`, `node_modules`, `.bytecode-fingerprint`, `hermes_cli/web_dist/`.
  - **Pre-flight cleanup:** it runs `_discard_lockfile_churn` and `_normalize_managed_eol` first. It also clears unmerged index entries and intent-to-add entries.
  - **Stash:** `git stash push --include-untracked -m hermes-update-autostash-<UTC ts>`.
  - **Restore:** after the pull, `_restore_stashed_changes` runs.
    - Interactive runs ask `[Y/n]`.
    - Non-interactive runs, or `--yes`, restore automatically.
    - `updates.non_interactive_local_changes: discard` drops the stash instead.
    - `--keep-stash` parks the stash and does not reapply (the desktop updater's mode).
  - **Verification:** it applies the stash, then checks syntax of the restored `.py` files and re-imports `hermes_cli.main`, `run_agent`, `model_tools`, `toolsets`.
    - The import check is skipped if the restored files are only docs or images.
    - A new import failure compared with the clean tree rejects the restore. It resets to the clean tree, keeps the stash, and the update exits 1 (`stash_restore_rejected`).
  - **Conflicts:** a conflicted apply is reset to clean and the stash is parked.
    - The stash is kept if the update added a file at a path where you had an untracked one.
    - The result is "partial" and exit 1, never "Update complete" (#122557).
  - **Orphan warning:** autostashes older than 7 days are named at every update. Hermes never drops one itself.
  - **Consequence for you:** your 68 modified and 26 added files will be stashed and re-applied on top of the new code.
    - Merge conflicts are likely when upstream touches the same files.
    - The critical files the update syntax-checks are listed at `update_cmd.py:~203` (for example `hermes_cli/main.py`, `config.py`, `run_agent.py`, `pm/environments.py`).
- **Parked branch:** if the checkout is on a branch other than the target, a dirty tree blocks the switch and the code update is skipped with exit 1.
- **Pause and restart:**
  - **Planning:** `_begin_update_receipt_and_plan` calls `collect_runtime_inventory` (item 5).
  - **Pause:** on POSIX, `update_cmd_posix_pause.pause_at_commit_point` stops every gateway from this install just before the first checkout write.
    - It drains via the control socket `pause-for-update`.
    - It uses `systemctl stop` for units, and marker plus SIGTERM for bare processes.
    - It writes a token through `update_pause_record`.
  - **Resume and tree gate:** `_resume_paused_before_build` restarts the set after the dependency sync and launcher publish, before the product builds. `update_cmd_pause_gate._checkout_move` binds each git write to the pause record (Windows pause is `update_cmd_windows`).
  - **Fleet restart:** `_restart_gateway_fleet_after_update` restarts every `hermes-gateway*` and `hermes-serve*` unit, user and system scope, with a SIGUSR1 drain first, then `systemctl restart`. launchd and bare `gateway run` processes are also handled.
    - **Skipped:** `--no-gateway-restart` defers the restart.
    - **Left to their owners:** Desktop-owned serves and manual `serve` processes.
  - **Host obligation** (`update_host_obligation.py`): `host-update-restart-<install key>.json` lives in `$HERMES_GATEWAY_LOCK_DIR`, else `$XDG_STATE_HOME/hermes/gateway-locks` (default `~/.local/state/hermes/gateway-locks`).
    - It prevents each profile's update from re-killing the single shared multiplexer.
    - The per-home `fleet_restart_pending` marker is its fallback.
  - **Pause-record scoping:** `update_pause_record` appears to scope itself to `updateMechanism: self` **(inferred from a partial read)**.
- **Completion** (`update_completion.py`): `run_completion` launches `update_completion.py` from the **new** tree as a child, with `-I -S -X pycache_prefix=<tmpdir>`. The sequence is:
  1. `arm_completion` writes `installs/<key>/source-completion-pending`.
  2. `convert_treeless_checkout_first`.
  3. `ensure_tools_for_sync`.
  4. `pm.sync_venv(explicit=True, project_root=root, evict_incompatible_plugins=True)`.
  5. `collect_superseded_generations`.
  6. A second child `--prepared` runs on the newly selected interpreter. It calls `_sweep_bytecode_after_update`, then `complete_source_checkout`, then the fleet restart and verification.
  - If the tail is owed, the next launch retries it. Retries back off after 2 failures (15 minutes) and stop after 6 attempts (`venv_sync.py:~222`).
- **`post_update.py`:** the steps (`HOME_STEPS`) are adopt checkout, migrate config (with backup and rollback), sync skills, state-db guard, drop plugin catalog, `expose_cli`.
  - `step_provision_runtimes` calls `pm.sync_venv(explicit=True, evict_incompatible_plugins=True)` but is in `MACHINE_STEPS`, run only by `python -m hermes_cli.post_update --scope machine|all`.
  - The update itself uses the completion child above.
  - **Plugins during update:** `evict_incompatible_plugins` makes `pm/plugin_eviction.py` disable, in the config of every home that enables it, any plugin that cannot fit the new core.
    - Disabling applies when the plugin's manifest, its `requires-python`, or the resolver or build rejects it.
    - A plugin that fails `requires_hermes` is only left out of the build: it stays enabled in config and rejoins later.
    - Disabling writes `plugins.disabled`, clears `memory.provider` if it names the plugin, and prints warnings.
    - The sync never fails because of a plugin. It builds core alone first, then re-adds members in config order and drops any that break.
  - The update has no other plugin handling. It does not run `hermes plugins update`. It does drop the live plugin-catalog caches for every profile.
- **After the pull:** the config migration (`updates.pre_update_backup: quick` by default) and a pre-update snapshot run before any git write.

## 3. Python environment manager `pm/`

**Layout** (`pm/environments.py`):
- **State dir:** `install_state_dir = <default hermes root>/installs/<sha256(resolved checkout path)[:16]>`. `dependency_home_root()` resolves to the default root even when `HERMES_HOME` is a profile.
- **Generations:** `<state>/environments/<uuid hex>/` containing `venv/`, `workspace/` (generated `pyproject.toml`, `uv.lock`, snapshot of core inputs), `.lease-managed`, and `.leases/`.
- **Selection record:** `<state>/facts.json`, key `packages.venv.environment` plus `stamp`, `extras`, `resolved_lock`.
  - `runtime_facts_path` = `facts.json`; `selected_venv` = recorded venv, else `venv/` or `.venv/` in the checkout (before first sync); `committed_venv` = recorded only.
  - `_recorded_venv` errors if the path is outside `<state>/environments/` or lacks `pyvenv.cfg`.
- **Other state files:** `inputs/` (mtime stamps), `.install.lock`, `publication.json` (the crash journal), `source-completion-pending`, `source-completion-attempts`, and `pm-runtime/`.
- **Activation at process boot:** `activate_dependencies`.
  - Under `runtime_lock` (10 s wait), it recovers any journal, leases the generation, prepends `<checkout>` and the generation's site-packages to `sys.path`, and sets `PYTHONPATH`.
  - So the **checkout source wins over the venv's copy**.
  - It puts `<checkout>/.hermes/bin` first on PATH.
- **Build:** `Venv.apply` (`pm/packages.py:430`) makes a new uuid generation, creates the venv, then runs `lock_and_sync`.
  - It runs `uv sync --frozen --all-packages --compile-bytecode` (`pm/environment.py:354`). The sync is `--frozen` unless a plugin member set requires re-locking.
  - On failure it removes the generation.
  - Success is committed by `facts.record_state`, after an fsync-like `flush_before_selecting`.
- **Rollback:**
  - **Not built in.** The facts file holds one selection and no history.
  - `pm repair` / `repair_dependencies` rebuilds the recorded set into a new generation. It is not a reselect.
  - Reselecting an older generation means editing `facts.json` by hand.
  - **(Inferred)** the old generation's venv would stay usable until collected.
- **Garbage collection** (`hermes_cli/runtime_state.py:184`, `collect_generations`):
  - **What it removes:** unselected, `.lease-managed`, at least 24 h old, with no live lease.
  - **Leases:** a lease is an `flock`ed file in `.leases/`, held for the process lifetime.
  - **When it runs:** after each update or boot-time sync (`collect_superseded_generations`) and on `hermes pm gc`.
  - **Orphans:** `pm gc` also removes install-state dirs of deleted checkouts.
- **Workspace members** (`pm/workspace.py`, `pm/plugin_declarations.py`):
  - **Where it reads from:** `read_python_declaration(plugin_dir)` reads `plugin.yaml`/`plugin.yml`, else `plugin.json`, and `pyproject.toml`.
  - **Rule:** if a `pyproject.toml` has no "GENERATED by pm" marker, it owns packaging and `[project].dependencies` are used.
    - Otherwise `python_dependencies` and `pip_dependencies` in `plugin.yaml` are used.
  - **What is excluded:** URL requirements and `hermes-agent` itself are dropped. `python_runtime: external` opts out of membership.
  - **Member candidates:** a plugin is a member only if it has a `pyproject.toml` or at least one applicable requirement (`is_member`).
  - **`manifest_version`:** the core limit is `SUPPORTED_MANIFEST_VERSION`, which I did not read.
  - **Building the workspace:** `_generate_pyproject` copies core inputs and sets `tool.uv.workspace.members`, with member dirs under `plugin-sources/<key>` or `plugin-deps/<key>`. `<key>` is `<name>-<sha256(path)[:16]>`.
    - A plugin with no pyproject becomes a metadata-only member `hermes-plugin-<key>`.
    - `_copy_core_inputs` copies `pyproject.toml`, `setup.py`, top-level `*.py`, and the package dirs matched by `tool.setuptools.packages.find.include`.
    - **Consequence:** a new top-level package you add to core is copied only if the include patterns match it. The runtime does not depend on that copy, because `sys.path` has the checkout first.
  - **`members_stamp`:** a sha256 over each member's identity path plus its declaration files (plus all of its tree if it has a `pyproject.toml`).
  - **When a rebuild is needed:** the venv stamp covers `uv.lock` digest, extras, the Python pin from `pm/lock.json`, and `members_stamp`.
    - Editing `pyproject.toml` or `uv.lock` therefore forces a rebuild.
    - `pm.venv_is_current` compares the stamp.
- **Who is in the member set:** the union, in config order, of every live profile's `plugins.enabled` plus `memory.provider` (`pm/plugins_state.py`).
  - The profiles are the default home plus `profiles/<id>` dirs that have an identity marker and no tombstone.
  - An unreadable secondary config is skipped during an update but refuses an admission.
  - Plugin dirs come from `<home>/plugins/<key>`, falling back to `<checkout>/plugins/<key>` for bundled ones.
- **Boot-time sync:** if you patch `pyproject.toml` or `uv.lock`, the next launch's `prepare_launch` (`venv_sync.py:~270`) sees the stamp mismatch and runs `sync_venv(explicit=True, evict_incompatible_plugins=True)`. It re-execs into the new interpreter. Unless lazy installs are disabled, it also rebuilds the owed tail.

## 4. Plugin enable admission and install

- **Admission call:** `admit_plugin_set_change(candidate_enabled, candidate_disabled, *, active_plugins_dir=, extra_dirs=, expected_config=, plugin=)` (`hermes_cli/plugins_admission.py:50`).
  - It calls `pm.client.sync_venv(explicit=True, plugins=Selection({home, enabled, disabled, extra_dirs, expected_config}))`.
  - It does not write config or the environment itself.
- **Inside the PM worker, under `.install.lock`** (`pm/install.py:791`, `pm/publication.py`):
  1. `PluginSelection` snapshots all homes' configs, checks `expected_config` (the sha256 of the current `config.yaml`, or `"missing"`), and builds the proposed config bytes.
     - `plugins.enabled` and `plugins.disabled` are rewritten as **sorted** lists.
     - The write is a ruamel round-trip, so comments survive.
  2. It computes the candidate members.
  3. It builds a new generation if the stamp changes, with `uv` re-locking against the seed lock.
  4. `publish` writes the `publication.json` journal, then `config.yaml`.
  5. `facts.json` is committed, then `finish_publication`.
  - A crash before the facts commit rolls the config back at the next boot or lock (`recover_publication`).
- **The CLI path** is `_admit_and_save_plugin_sets` (`plugins_cmd.py:488`), with `_set_plugin_enabled` taking a per-home thread lock and passing `expected_config = _plugin_selection_version()`.
- **Programmatic call for `$HERMES_HOME/plugins/<name>`.** Call `plugins_cmd._set_plugin_enabled(name, enable=True)`, or `admit_plugin_set_change`:
  ```
  enabled = existing enabled set | {name}; disabled = existing disabled set - aliases
  admit_plugin_set_change(enabled, disabled, active_plugins_dir=<home>/plugins,
                          expected_config=<sha256 of config.yaml>, plugin=name)
  ```
  - `HERMES_HOME` must point at the home being changed.
  - The plugin dir must already exist.
  - Running it as a subprocess via `hermes plugins enable <name>` is the safer route **(inferred)**.
- **Dependency conflict:** a resolver failure raises `DependencyConflict` (a subclass of `AdmissionRefused`). Both leave `config.yaml` and the active environment unchanged. Other `Exception`s are wrapped as `AdmissionRefused(str(exc))` (`plugins_admission.py:75`).
- **Disable** goes through the same transaction. The stamp changes if the plugin was a member, so a new generation is built **without** it. If nothing changes the member set, only the config is published. The old generation is later garbage-collected.
- **`hermes plugins install <url>`** (`plugins_cmd_install.py`, `plugins_cmd.py`):
  - **URL parsing** (`_resolve_git_url`, `plugins_cmd.py:294`):
    - `https://github.com/o/r/tree/<branch>/<sub>` gives `https://github.com/o/r.git` plus subdir `<sub>`.
      - It drops the first two segments after `tree`, so the branch is assumed to be a single path segment, and a branch containing `/` mis-parses.
      - `blob` and other browser segments are accepted for the repo but give no subdir.
    - `<url>#sub`, `<url>.git/<sub>` and `owner/repo/sub` also work.
    - A bare name resolves through the catalog.
  - **Clone:**
    - It does `git clone --depth 1`, plus `--filter=blob:none --no-checkout` and a sparse checkout restricted to the subdir (`plugins_cmd_git.py:218`).
    - A `--ref` must be a full 40-character commit SHA.
    - It then runs a security scan.
  - **Target:** the plugin name comes from `plugin.yaml` `name`, else the subdir leaf, else the repo name. The target is `$HERMES_HOME/plugins/<name>`.
    - Only the subdir content is copied, with no `.git`.
    - `hermes plugins update` requires `<target>/.git` for a custom source (`plugins_transaction.py`). Subdir installs therefore cannot be updated in place **(inferred from that check)**.
  - **Install-time Python-dependency consent:** a prompt, or `--yes-deps` for non-interactive use.
    - A non-interactive run without it leaves the plugin installed but disabled.
    - `--enable`/`--no-enable` set the enable choice.
  - **Publish:** `publish_plugin` swaps the tree and writes `plugins/.install-metadata.json` (`{source, revision, pinned, ...}`) through the PM `StagedUpdate` path (journalled, same lock).
    - A disabled plugin's code change does not touch the environment.
    - The plugin is only enabled if the user opts in.
  - **Live load:** `activate_plugin_now` loads an enabled plugin into the running gateway where possible.

## 5. Process model

- **Everything imports the checkout directly** (`activate_dependencies` puts the checkout first on `sys.path`). The processes are:
  - `hermes` CLI sessions.
  - `hermes gateway run`. Cron ticks and Kanban dispatch/notify watchers run **inside** the gateway (`cron/scheduler*.py`, `gateway/kanban_watchers*.py`).
  - Cron/Kanban workers run as separate processes, `systemd-run --user --scope` where that is available.
  - `hermes dashboard` and `hermes serve` (the headless backend).
  - `hermes-acp`.
  - The multiplex gateway.
- **Gateway identity files**, per home: `gateway.pid`, `gateway.lock`, `gateway_state.json`, plus a control socket. Cross-profile locks live in `$HERMES_GATEWAY_LOCK_DIR` or `~/.local/state/hermes/gateway-locks` (`gateway/status.py:~320`).
  - `live_gateway_pid_for_home(home)` (`gateway/status.py:1506`) gives a verified pid: pid file plus lock first, then the runtime-status record, with a start-time reuse guard.
- **Multiplexing:** the update code describes a model where exactly one `hermes gateway run` serves all profiles per host (`update_host_obligation.py` docstring). Legacy per-profile units can coexist.
- **Existing enumeration helpers:**
  - **`hermes update --plan`:** this is the best read-only helper. It runs `collect_runtime_inventory()` (`update_inventory.py:~375`) and returns each gateway (kind, profile, pid, supervisor, code sha) plus serve/dashboard processes from the spawn ledger.
  - **`find_gateway_pids(all_profiles=True)`, `find_profile_gateway_processes()`, `_get_service_pids(all_profiles=True)`, `kill_gateway_processes()`,** and `stop_profile_gateway()`, all in `hermes_cli/gateway.py`.
  - **Spawn ledger:** `<default root>/spawn-ledger.json` (`hermes_cli/process_identity.py`).
    - Spawn tag: the `HERMES_SPAWN` env var, `v1:<install id>:<purpose>:<spawner pid>:<create time>`.
    - Entries are `(pid, create_time, purpose, argv, host, port, profile, home)`.
    - `ledger_entries()` verifies pid reuse.
  - **Dashboard scan and stop:** `_scan_dashboard_processes` scans `ps` for `dashboard|serve`. `hermes dashboard --stop` and `--status` use it.
- **Supervisors:** systemd user or system units, launchd (`ai.hermes.gateway[-profile]`), Windows service/scheduled task, s6, Desktop (spawns `serve`), or manual.
  - `hermes gateway restart` and `stop` are the supported CLI. The update's drain-first path uses SIGUSR1 (`_graceful_restart_via_sigusr1`).
  - **Stopping everything for a source tree** (my suggestion, **inferred**): take the update lock, run the `--plan` inventory, stop units through their supervisor, signal bare processes and `dashboard --stop`, then restart afterwards.
- **After `hermes update`:** the services are restarted by the update itself in the completion child (item 2). The result is verified against the new code sha through `gateway_state.json`'s code identity.

## 6. Profiles

- **Layout:** `<root>/profiles/<name>/`, where `<root>` = `get_default_hermes_root()` (`hermes_constants.py:216`).
  - A profile has its own `config.yaml`, `.env`, `state.db`, `plugins/`, `skills/` and so on.
  - Live profile ids need a valid `PROFILE_ID_RE` and an identity marker, with no `.deleted/` tombstone.
- **Selection:** `-p/--profile <name>` is pre-parsed from argv in `main.py:~430-595` (`_apply_profile_override`) before imports, and sets `HERMES_HOME=<root>/profiles/<name>`. There is also a sticky active profile.
- **Shared source and environments:**
  - Profiles share **one checkout**, one `installs/<key>/` state dir, one `facts.json`, one set of generations, and one bytecode cache. Dependency state is keyed by the default root and checkout path, not by profile.
  - Plugin dependencies are the **union** across profiles (item 3).
  - Per-profile pieces: boot-bootstrap record, `config.yaml`, plugin dirs, gateway files, and service unit names.
  - Update markers and the install key are at the root level, not per profile.

## 7. `web_dist`

- The compiled dashboard frontend is `<checkout>/hermes_cli/web_dist/`, listed in `.gitignore:92` (it is Vite's `outDir`, `main_web_build.py:_web_dist_dir`).
  - `hermes_cli/web_server.py:61` serves it, and `HERMES_WEB_DIST` overrides the path.
- **Built at install and update time:** by the `products` stage of `source_completion` (`build_update_products` in `hermes_cli/source_build.py`).
  - Freshness is a receipt checked by `scripts/build/freshness.mjs`, run with PM's Node. `source_product_current` returns False if PM's Node is not installed.
  - A rebuild is serialised with `<checkout>/.web_ui_build.lock`.
  - `hermes dashboard` also builds on demand unless `--skip-build`. `hermes serve` skips the build.
- **Effect of your patch:** because the freshness receipt reads the sources, changing files under `web/` (or other frontend sources) triggers a rebuild at the next completion or dashboard start **(inferred; I did not read the receipt's input set)**. Python-only patches do not.

## 8. Bytecode and `.bytecode-fingerprint`

- **Where bytecode goes:**
  - A normal Python run writes `__pycache__` into the source tree. I found no `PYTHONDONTWRITEBYTECODE` in the normal entry points.
  - The launchers set `sys.dont_write_bytecode = True` in some modes (`_launchers.py:391, 448`), whose scope I did not fully trace.
  - `uv sync --compile-bytecode` precompiles the venv site-packages.
  - The update's completion children use `-X pycache_prefix=<tmpdir>` and `-B`, so they do not write into the tree.
  - Syntax checks compile to a temp dir.
- **`.bytecode-fingerprint`:** at `<checkout>/.bytecode-fingerprint` (gitignored, along with `.tmp`).
  - **Contents:** the git fingerprint string `git:<ref>:<sha>` from `_read_git_revision_fingerprint(PROJECT_ROOT)` (`hermes_cli/main.py:944`), which parses `.git` files without spawning git.
  - **Writer:** `_record_bytecode_fingerprint` (`main_web_build.py:22`), atomic. It is called by `_sweep_stale_bytecode_if_checkout_changed` and by `_sweep_bytecode_after_update` (`update_cmd_maint.py:812`).
  - **Reader:** `_sweep_stale_bytecode_if_checkout_changed` (`main_web_build.py:37`), called at launch (`main.py:3553`). If the stored value differs from the current HEAD fingerprint, it removes all `__pycache__` dirs under the checkout (excluding `venv`, `.venv`, `node_modules`, `.git`, `.worktrees`) and re-stamps.
  - **What it does not do:** it never refuses to start or forces a recompile of anything else, and it ignores non-git trees.
- **If source files change without a HEAD change** (your in-place patch): the fingerprint is unchanged, so no sweep happens.
  - Python's timestamp-based `.pyc` validation would recompile files whose mtime or size changed.
  - Clearing `__pycache__` yourself, or deleting `.bytecode-fingerprint`, is a belt-and-braces step. A deleted fingerprint causes one sweep at the next launch **(inferred from the code above)**.
  - The update's stash restore also changes files without moving HEAD, so the same applies.

## Not read, so unverified

- The exact input set of the web freshness receipt.
- `hermes gateway restart/stop` command bodies.
- The remaining parts of `update_pause_record.py`.
- `SUPPORTED_MANIFEST_VERSION`.
- The Tauri/Electron updater behaviour.
- `install.sh`'s `--include-desktop` path.
