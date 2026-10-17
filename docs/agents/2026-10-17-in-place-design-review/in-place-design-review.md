# In-place installation design review

Date: 2026-10-17. Role: independent design reviewer. Model: Claude Fable 5.1.

Question: review `docs/in-place-installation-design.md` against the accepted plan
(`docs/in-place-installation-plan.md`), the two mapping reports, the implemented release-manager
pieces, and stock Hermes v0.21.7 (`71d34bad`) at `/home/outsider/agent-scratch/hostcompat/hermes-agent`.
Find design flaws, missing failure modes, wrong assumptions about stock Hermes, ordering bugs in
apply and rollback, and plan violations. Answer questions A to H with file:line evidence.

Conventions. `HERMES` means the stock checkout above. `REPO` means
`/home/outsider/Projects/Hermes_agent/LifeOS_plugin` (branch `feature/minimal-install-review`,
HEAD `679c24ee`). "Verified" means I read the code. "Inferred" means I reason from code I read but
did not execute, or from documented systemd behaviour. I ran no Hermes code and changed no file
except this report.

## 1. Findings ranked by severity

### Blocking

**B1. `hermes pm install` is the wrong synchronization call; it does far more than build a generation.**
Design section 5 says the worker runs `hermes pm install` and that this is "the explicit
synchronization that `hermes update` also uses". Both claims are wrong.

- `cmd_install` with no names installs every lockfile tool and re-verifies their digests
  (`HERMES/pm/cli.py:356-371`, `_install_names(..., verify=not trust_recorded)`), then runs
  `activate`, then `sync_venv(extras or ["all"], explicit=True)` (`pm/cli.py:310-322`), then
  installs the optional defaults `agent-browser` (Chromium) and `cua-driver` unless declined
  (`pm/cli.py:297-307, 387-392`), then rewrites the activation input stamps (`pm/cli.py:393-397`).
- Installing the `python` tool calls `publish_launchers(repo_root(), create=False)`
  (`pm/cli.py:249-252`), which runs `expose_cli` and rewrites every `~/.local/bin/hermes*` it
  already owns (`hermes_cli/venv_sync.py:69-100`, `hermes_cli/_launchers.py:738-795`). The plan
  (line 65) forbids touching the public launchers.
- `hermes update` does not use this path. Its completion child calls
  `pm.sync_venv(explicit=True, project_root=root, evict_incompatible_plugins=True)` (map section 2;
  `hermes_cli/venv_sync.py:589-603` shows the same call for the boot-time path).

The parts the design wants (discover members from every live profile's `config.yaml`, re-lock
against the seed lock, build a new generation, select only on success) are the inner call
`pm.sync_venv(explicit=True)` with `plugins=None` and `evict_incompatible_plugins=False`
(`HERMES/pm/install.py:791-855`; member discovery `pm/plugins_state.py:118-148`; commit order in
`_commit_selection` `pm/install.py:769-788`; failed generation removed `pm/packages.py:484-486`).
Fix: have the worker run, with the owner's interpreter and `cwd=<source>`,
`python -c "from pm.client import sync_venv; sync_venv(explicit=True, project_root=<source>)"`
(`pm/client.py:208-235`). Do not run tools, defaults, or launcher publication. If the host is
missing lockfile tools the sync fails and that is a correct refusal.

**B2. ProfileServices cannot bind a stock host, so "reused without change" (section 11) is false.**
`ProfileServices.__init__` requires all three units unless `first_installation=True`, and
`first_installation` binds only `dashboard` (`REPO/lifeos_hook_bridge/profile_services.py:76-80`).
`_inspect` demands `LoadState=loaded` for each bound unit (`profile_services.py:147-157`). A stock
Hermes install has at most `hermes-gateway.service`; nothing in stock generates
`hermes-dashboard.service` (verified: `HERMES/hermes_cli/gateway.py:3300-3350` renders only the
gateway unit; the map's claim that dashboard units are only recognised, never generated, holds).
`com.lifeos.pulse.service` does not exist before the first installation. So the non-fresh mode
refuses every stock host, and the fresh mode refuses every stock host without a dashboard unit.
Fix: add a mode that binds the gateway (required), the dashboard (optional, only if a unit is
loaded), and creates Pulse through `resume(roles=..., activate=True)`. Record which roles existed.

**B3. The dashboard that launches the worker is itself an uncontrolled source consumer on a stock host.**
On a stock host the owner runs `hermes dashboard` in a terminal or via the Desktop app's `serve`
(map section 5). It imports the checkout (`pm/environments.py activate_dependencies`, map section 3),
so section 7's `/proc` scan (`REPO/optional/lifeos_release_manager/consumer_scan.py:21-63`) will
flag it unless it is in a stopped unit's cgroup, and the worker refuses. If the scan excludes it,
it keeps running stale code and the only thing that restarts it is the owner. Section 7 says the
worker stops and restarts `hermes-dashboard.service`, which does not exist on stock. The design
must choose: create a dashboard unit as part of the first installation (as `release_services.
service_files` does for the managed release) and require the owner to run the dashboard through
it, or treat a foreground dashboard as a consumer that is stopped by killing it and tell the owner
to relaunch. Either way the page cannot show the result until the dashboard is back; say so.

**B4. The design accepts resolver conflicts at apply time; the plan requires proof before review.**
Plan lines 36 and 49: preparation is allowed only with "compatible dependencies" and dependencies
may be added "only when the reviewed plan proves compatibility". Design sections 5 and 13 admit the
pins are compared only against installed distributions (`host_compatibility.py:282-295`) and that
a resolver conflict "appears at apply time and causes a rollback". Pin equality against installed
packages is not a resolution against the seed lock: the stock `uv.lock` may already pin a
transitive dependency incompatibly even when none of the four names is installed. Fix: at
preparation, run the same re-lock PM would run, in a throwaway workspace (`pm/workspace.
lock_and_sync` with the bridge dir as the only extra member, into `job/resolve`), or at minimum
`uv lock --check`-style resolution with the seed lock; refuse on `ResolutionConflict`. This also
protects the dev/daily transition (finding G2).

### Should fix

**S1. Rollback order in section 4.2 is stated wrong and would break the mount restore.**
Section 4.2 says a failure "restores the programs, synchronizes the environment back ..., restores
the mount, and resumes the services, as the current worker does". The current worker does the
opposite: `services.quiesce()`, `_restore_mount(...)`, `programs.restore()`, `services.resume()`
(`REPO/optional/lifeos_release_manager/release_worker.py:434-448`). The order matters because
`config.yaml` is both a program target (`release_worker.py:211`) and a mount target
(`MountTransaction` mounted files, map section 6). If programs are restored first, `config.yaml`
returns to its pre-install bytes, and the mount's `restore_completed` then sees a target that does
not match its recorded `after` digest and refuses; conversely, `ProgramTransaction.restore` only
accepts a target whose current fingerprint is `before` or `after` (`release_programs.py:360-373`).
Keep the existing order and insert the environment re-sync after `programs.restore()` and before
`services.resume()`. Treat a failed re-sync as a warning, not a rollback failure: with the bridge
disabled in config the venv stamp no longer matches, so the next launch re-syncs on its own
(`HERMES/hermes_cli/venv_sync.py:355-383`, `_sync_source_dependencies`). Also add the re-sync to
the `recover` and `restore` actions; the design mentions it only for apply failure and removal.

**S2. The update-hold location in the design differs from the implemented patch.**
Design sections 4.3 and 6 say `<install state>/update-holds/*.json`. The patch stores holds in
`<git common dir>/hermes-update-holds/` (`REPO/lifeos_hook_bridge/patches/hermes-update-hold.patch`,
`update_holds_dir`), that is `.git/hermes-update-holds/`. The `.git` location is the better one
(not stashed, not reported as a local change), but the design text, the program-plan table, and
the `ProgramTransaction` target must agree. Note `ProgramTransaction.fingerprint` refuses targets
with group or other write bits (`release_programs.py:59`); `.git` entries are usually 0644, fine.

**S3. The hold does not stop the passive "update available" nag or the dashboard's check endpoint.**
`evaluate_update_admission` is called by exactly three mutating surfaces: `hermes update` preflight
(`HERMES/hermes_cli/main.py:2375-2383`), `--check` (`hermes_cli/update_cmd.py:647-655`), and the
dashboard update action (`hermes_cli/web_routers/actions.py:253-261`). Verified: no other caller
outside tests. But `hermes --version` and the banner call `check_for_updates(passive=True)` and
print "Update available, run hermes update" (`hermes_cli/_startup_fast.py:220-237`;
`source_check.py:382-406` honours only `updates.check`). The dashboard's
`GET /api/hermes/update/check` sets `can_apply: install_method == "git"` without consulting the
gate (`actions.py:302-330`), so the Update button appears, then refuses. Fix: either extend the
patch so `check_for_updates(passive=True)` and `check_hermes_update` report the hold, or document
the nag and the dead button as known behaviour on the page.

**S4. Preparation-time service inspection is missing.**
Plan line 2 of the contract says the plugin identifies "services". `host_compatibility.inspect_host`
never looks at units or processes (`host_compatibility.py:312-366`). A gateway installed as a
system unit (`hermes gateway install --system`, `gateway.py:3283-3300`), a bare `hermes gateway run`,
a launchd or s6 supervisor, or a Desktop-owned `serve` is discovered only at apply time by
`ProfileServices` or the `/proc` scan, after the owner has reviewed and admitted. Add a read-only
service and consumer inventory to the compatibility result (`systemctl --user show` of the three
units plus `consumer_scan.source_consumers`) and refuse or warn before review.

**S5. Config.yaml is byte-managed by `ProgramTransaction`, so Hermes's own config writes make job
restore and recovery refuse.** Any later Hermes write to `config.yaml` (plugin enable through PM's
`PluginSelection.publish`, `pm/publication.py:85-93`; config migration; `/model` persistence;
dashboard settings) changes the fingerprint, and `check_applied`, `check_recovery`, and `restore`
all raise "preserves a later artifact edit" (`release_programs.py:165-175, 360-373`). The managed
release has the same property, but the plan for removal says "restore only recorded configuration
keys" (line 75) and the design reuses `removal_configuration`, whose transforms are fixed (set
`platforms.discord.enabled: false`, drop `memory.provider`, filter lists; map section 5) rather
than recorded before-values. Record the key-level before-values at install (`plugins.enabled`,
`plugins.disabled`, `plugins.entries.lifeos-*`, `memory.provider`, `skills.external_dirs`,
`platforms.discord.enabled`) in `lifeos-host.json` and restore those keys on removal; keep
`ProgramTransaction` for files Hermes never rewrites.

**S6. Plugin eviction can rewrite `config.yaml` outside the transaction.**
The boot-time sync runs with `evict_incompatible_plugins=True` (`venv_sync.py:602`) and
`pm/plugin_eviction.py:78-125` publishes config edits that disable a plugin whose member fails to
build, and clears `memory.provider` when it names the plugin (map section 2). After installation,
any event that makes the venv stale (an owner's hand edit of `plugins.enabled`, a `pm/lock.json`
or `uv.lock` change, a resolver that now fails for the bridge pins because a mirror changed) makes
the next launch sync with eviction; a bridge failure then disables the bridge and switches memory
off LifeOS, silently. The compatibility check and the host record do not detect this (the record
covers host files only, `host_record.py:build_record`). Add the plugin-selection keys to the drift
check (section 9) and make the releases page report "bridge disabled by Hermes" with the
`publication.json` reason.

**S7. Update staging from retained originals is incomplete for added and dropped targets.**
Section 8: "stage the new patched files from the retained originals". A target that release B adds
and release A did not have has no retained original; it must be read from the host and its hash
checked against B's stock hash, then retained. A target that B drops must be restored from the
original and its retained copy removed. The `originals` directory is a `ProgramTransaction`
directory target, so the whole directory is swapped; the staged copy must therefore be the full
new set. Also state the counts per release: the manifest has 96 targets, 27 added, 69 modified
(`host-compatibility.json`, computed), while the design says 94, 26, and 68 (sections 4.3 and 8).

**S8. Dev/daily transition: install.sh will not repoint the launchers, and it runs maintenance on
the live profile.** Verified in `HERMES/scripts/install.sh`:
- `--skip-setup` sets `NON_INTERACTIVE=true` (line 62); `run_stage` skips `setup` and `gateway`
  (lines 962-966, 904-921). No `hermes setup`, no `gateway install`, no service restart.
- `products` runs `hermes_cli/source_completion.py` (lines 857-879), which calls
  `publish_launchers(root)` with `create=True` (`source_completion.py:129, venv_sync.py:92-100`).
  `_publish_conveniences` skips an existing `~/.local/bin/hermes` unless `_owns_launcher(target,
  root)` recognises it as pointing into the new root (`_launchers.py:531-548, 505-525`). The
  managed launcher `exec '<job>/bin/hermes'` does not match, so the launchers stay pointed at the
  managed runtime. Design 10.4 must repoint unconditionally, not "if the installer did not".
- The same completion runs `build_update_products` and `_run_post_update_maintenance(assume_yes)`
  (`source_completion.py:131-141`), which syncs bundled skills into every profile and runs the
  config migration on `~/.hermes/config.yaml` (`update_cmd_maint.py:1060-1068, 849-874`). That file
  is a `MountTransaction` and `ProgramTransaction` target of the managed release. Record its hash
  before and after `install.sh`; if it changes, say in the design that the managed jobs' restore
  path is dead after the transition.
- `python-deps` runs `pm.cli install` with discovery from `~/.hermes/config.yaml`
  (`install.sh:766-789`), so the stock environment is built with the bridge member already in it.
  A pin conflict here fails `install.sh` (finding B4). Pass `--skip-browser --skip-computer-use`
  unless dev and daily use those tools; otherwise install.sh downloads Chromium.
- `--commit` requires the commit to be an ancestor of `origin/main` (`install.sh:684-686, 734-741`).
  The scratch repo has no remote refs, so I could not confirm `71d34bad` is on `main`; the tag
  `v0.21.7` points at it. Confirm during the rehearsal.

**S9. The worker's `/proc` scan is correct but the design under-describes the cron and Kanban case.**
Restart-safe cron and Kanban workers are spawned as `systemd-run --user --scope --unit
hermes-worker-<suffix>` (`HERMES/hermes_cli/gateway.py:3292-3294, 4625`; `cron/scheduler.py:3800-3840`;
test fixture `tests/hermes_cli/test_kanban_gateway_restart_handoff.py:81`). A transient scope is a
separate unit under the user manager, outside `hermes-gateway.service`'s cgroup (systemd
semantics, inferred). `systemctl stop hermes-gateway.service` therefore does not stop them;
`gateway/cgroup_cleanup.py` kills only the gateway unit's own cgroup (lines 1-45). The scan sees
them (their environment carries `PYTHONPATH=<checkout>`), they are not in an excluded group, and
the worker refuses. That is the plan's required behaviour, but a long Kanban task can block
installation for hours. Say so on the page and offer "wait for workers to finish" with the unit
names (`systemctl --user list-units 'hermes-worker-*'`) rather than a bare refusal.

### Minor

**M1. Launch during publication is not blocked.** `prepare_launch` takes the update lock only when
the venv is stale or a completion marker is pending (`venv_sync.py:355-384`). While the worker
publishes 96 files with the venv still current (before step 5), an owner-started `hermes` boots on
a half-patched tree. Stock `hermes update` has the same exposure. Document it; publish host files
module-by-module in import order if it is cheap.

**M2. The preview tree in 4.1.7 can create an orphan install-state directory.** Importing
`hermes_cli.config` from `job/hermes-preview` with the owner's interpreter may touch
`pm.environments.install_state_dir(preview)` and create `~/.hermes/installs/<newkey>/`. The
current `program-configuration` stage sets `HERMES_HOME=job` (`release_worker.py:208-210`), which
moves the default root as well (`hermes_constants.py:216-233`), so the state lands under the job.
Keep that environment; delete the preview with the job.

**M3. Section 5 says the explicit sync "resolves the bridge member against the seed lock".**
Verified in part: `Venv.apply` replays the recorded `resolved_lock` when it exists
(`pm/packages.py:460-474`) and `lock_and_sync` re-locks when the member set requires it. "Seed lock"
is the design's term, not PM's; use PM's wording ("replays the recorded lock, re-locks for new
members").

**M4. Dirty-tree completion tail.** With `dirty: true` in the stamp (`source_stamp.py:27-44`),
`_tree_matches_completed_stamp` is false forever (`venv_sync.py:297-312`). Consequence: every
future boot-time sync arms the full completion tail (`_finish_source_update`, `venv_sync.py:437-449`,
`arm=not completed`), which republishes launchers (owned ones only), rebuilds products, runs
maintenance, and rewrites the stamp. No loop: `clear_completion` runs on success and the retry
counter caps at 6 (`venv_sync.py:187-191, 254-270`). Not a reset: nothing in the tail runs git
write commands. The web freshness receipt hashes `web/src`, `package.json`, `tsconfig.json`
(`scripts/build/freshness.mjs:27`); no LifeOS target is under `web/`, so no web rebuild is
triggered by the patch. Section 13 should state the "every boot-time sync runs the tail" cost.

**M5. `hermes pm update` and hand edits rewrite tracked files (`pm/lock.json`, `uv.lock`) and are
not gated.** They are explicit owner actions; the compatibility check reports them as
`modified_source`, but `lifeos-host.json` drift (section 9) does not, because only targets are
compared. Mention in section 9.

**M6. `gateway code_skew`, `boot_bootstrap`, and the bytecode sweep are HEAD-keyed and ignore the
patch** (`gateway/code_skew.py:22-57`; `boot_bootstrap.py:83-100, 135-143`;
`main_web_build.py` per map). The design's restart plus `__pycache__` removal is sufficient;
`publish()` writes a new inode and mtime, so timestamp-validated `.pyc` files are recompiled
anyway. No action beyond stating it.

**M7. Transition mode is undefined.** Section 10.4 says "LifeOS is already installed and the host
is unpatched", but section 8's `installed` state requires `lifeos-host.json`, and the managed
release leaves a format 1 `integration-release.json` and the old bridge in
`<profile>/plugins/lifeos-hook-bridge`. Define the admission: stock-compatible checkout, no host
record, format 1 receipt present, `.claude` present; then the plan skips native initialization
and runs the host patch, plugin replacement, launcher repoint, and hold.

## 2. Answers to questions A to H

### A. `hermes pm install` as the dependency path

- Discovers the member set from config: yes. `sync_venv(plugins=None)` calls `_member_inputs(None)`
  which uses `enabled_member_dirs()` over every live home (`pm/install.py:832-841`,
  `pm/plugins_state.py:118-148`, `pm/packages.py:425-427`). Verified.
- Builds a new generation and leaves the old one selected on failure: yes. `Venv.apply` creates
  `environments/<uuid>`, removes it on any exception (`pm/packages.py:445-449, 484-486`);
  `_commit_selection` records facts only after `apply` returns (`pm/install.py:769-788`). Verified.
- Touches other things: yes, see B1. Tools and their digest verification, optional defaults
  (Chromium), `publish_launchers(create=False)` for the `python` tool, activation input stamps.
  It does not touch `install-stamp.json`, the completion marker, or `config.yaml` (plugins=None
  means `change=None`, `pm/install.py:736-741, 832`). `prepare_launch` skips `pm` commands
  (`venv_sync.py:333`), so no completion tail. Verified.
- `admit_plugin_set_change` instead: it would publish `config.yaml` itself through
  `PluginSelection.publish` with sorted lists (`hermes_cli/plugins_admission.py:50-80`,
  `pm/publication.py:70-93`), which conflicts with `ProgramTransaction` owning the same file
  (S5). It is the right tool only if `config.yaml` leaves the program plan. Recommendation: keep
  the transaction owning `config.yaml` and call `pm.client.sync_venv(explicit=True,
  project_root=<source>)` directly (B1). The config-before-environment gap between steps 4 and 5 is
  closed by the held update marker: a CLI launched then sees a stale venv and `prepare_launch`
  refuses with "an update is still running" (`venv_sync.py:366-369`). Verified.

### B. Update-hold coverage

Covered through `evaluate_update_admission`: `hermes update`, `hermes update --check`, the
dashboard `POST /api/hermes/update` (which spawns `hermes update`), the Tauri bootstrap installer
(it runs `hermes update --branch` and handles exit 2, `apps/bootstrap-installer/src-tauri/src/
update.rs:204-208, 594`), and the Electron managed SSH update (runs `hermes update` on the remote,
`apps/desktop/electron/managed-ssh-update.ts:8, 539`). `hermes update --plan` and
`--list-venv-holders` run before the gate but are read-only (`main.py:2347-2370`). Verified.

Not covered, by design or by omission:
- `install.sh` rerun: stashes a dirty tree, checks out `main`, fast-forwards or `reset --hard`
  (`install.sh:583-635`). Not gated; acknowledged in section 6.
- `hermes pm update` rewrites `pm/lock.json` and `uv.lock` (`pm/cli.py:660-707`). Not gated.
- Completion tail (`source_completion.py`): publishes launchers, builds `web_dist`, runs
  maintenance, writes the stamp. It does not run git write commands; it is not a checkout mutation
  in the plan's sense. Verified by reading `_complete_locked` and `_run_post_update_maintenance`.
- Boot-time adoption writes only `install-stamp.json`, and only when no stamp exists
  (`post_update.py:166-200`). Ignored by git (`.gitignore:281`).
- `_settle_interrupted_update` and `_early_recovery.restore_interrupted_pull` act only on a torn
  update marker (`hermes_bootstrap.py:511-544`). With updates refused at admission, no marker exists.

Residual gap: S3 (passive nag, dashboard check endpoint) and S2 (design text names the wrong
directory).

### C. Permanently dirty tree

- `venv_sync.prepare_launch`: no effect while the venv is current and no marker is pending
  (`venv_sync.py:355-384`). When a sync is needed, the tail is always armed because
  `_tree_matches_completed_stamp` is false (M4). One tail per such event, not a loop.
- `source_completion` and `write_source_stamp`: stamp records `dirty: true`
  (`source_stamp.py:27-44`); `_packaged` in the compatibility check still passes (distribution
  null, updateMechanism self, `host_compatibility.py:160-172`).
- `gateway code_skew`: HEAD fingerprint only (`code_skew.py:22-35`); no skew reported. Verified.
- `boot_bootstrap`: identity is `git rev-parse HEAD` (`boot_bootstrap.py:27-50, 83-100`); no
  rerun. Verified.
- `hermes update --check` banners: `--check` is refused with the hold message (exit 2). The
  passive banner is not (S3).
- Reset risk: none in Hermes's own paths. `install.sh` is the only path that resets.
- Eviction risk: S6.

### D. Consumer coverage

The three units plus the `/proc` scan cover: gateway (with in-process cron ticks and Kanban
watchers), a dashboard unit if one exists, Pulse, CLI sessions, ACP, Desktop `serve`, bare
`gateway run`, and worker scopes. Verified `consumer_scan.py` matches on cmdline, environ, exe, and
cwd, and excludes only the caller-provided cgroups. Gaps: B2 and B3 (stock has no dashboard unit;
the launching dashboard is a consumer), S4 (system-scope gateway or other supervisors are found
only at apply time), S9 (worker scopes survive the gateway stop; refusal is correct but needs
owner guidance). Multiplex gateway: single-profile admission means one gateway unit; the
multiplexer is the same `hermes gateway run` process. The spawn ledger
(`<root>/spawn-ledger.json`, map section 5) is not used; the `/proc` scan supersedes it. Verified
that `systemctl stop hermes-gateway.service` does not stop scopes: scopes are separate units and
`cgroup_cleanup` targets the gateway's own cgroup (`gateway/cgroup_cleanup.py:1-45`).

### E. Rollback ordering

See S1. Correct order: quiesce services, restore mount, restore programs, re-sync environment
(tolerant), resume services. States of concern:
- Bridge enabled in config with deps missing: exists between step 4 and step 5 of apply and
  between a failed step 5 and `programs.restore()`. Services are stopped; CLI launches are refused
  by the held update marker because the venv is stale (`venv_sync.py:366-369`). Covered as long as
  the worker holds the marker through rollback and through `recover`.
- Patched files with an env lacking the bridge: same window; also the final state if the owner
  later disables the bridge through PM. Harmless for Hermes (unused hooks); the manager page should
  show it (S6).
- Recovery after a crash between `programs.apply` and the sync: the `recover` action must include
  the sync; the design lists it only for apply failure and removal.
- `ProgramTransaction.restore` refuses if `config.yaml` was rewritten by anything in between
  (S5). The mount restore before program restore is what keeps this consistent today.

### F. Updates and removal with retained originals

- Correctness for a newer release: S7 (added targets have no original; dropped targets need
  restore and retained-copy removal; the `originals` directory swap must carry the full new set).
- Later-edit refusal: `ProgramTransaction.prepare` fingerprints the current target as `before`
  (`release_programs.py:193`), so an update job's `before` is the old patched content; a drifted
  host fails the `installed` check first (`host_record.check_originals` plus per-target patched
  hashes). After an update, the old job's journal no longer matches the host, so its `restore`
  and `check_applied` refuse; that is correct, and removal does not depend on job journals
  because it uses `lifeos-host.json` and `.lifeos-host/originals/`. Verified `check_originals`
  compares each original against the manifest stock hash (`host_record.py:97-118`).
- Config keys: S5.

### G. Dev/daily transition

See S8. Summary of verified facts: `--skip-setup` skips `hermes setup` and `gateway install`
(no unit changes, no restarts); `products` republishes only launchers it owns, so the managed
`~/.local/bin/hermes*` stay as they are; `products` runs config migration and skills sync on the
live profile; `python-deps` builds the stock environment with the bridge member from the live
config. The services are stopped in step 2, so nothing starts the stock Hermes before step 4. The
in-place job must repoint the three launchers and verify the gateway unit's `ExecStart` still
resolves to `~/.local/bin/hermes` (the managed unit does, `release_services.py:39-69` per map).

### H. Plan requirements the design does not cover

1. Plan line 47: record "identities and inventory" of tools, skills, plugins, extras, model
   choices before and after, and verify them after restart (line 69). Section 7 verifies only
   `hermes lifeos-version` and a hook probe.
2. Plan line 51: the page must "state the tested scope and report known conflicts". Not in the
   design.
3. Plan line 26: must not report complete when only reduced hooks register. Section 7 probes
   `VALID_HOOKS` in a fresh process; it does not prove the restarted gateway registered the
   bridge in patched mode. Add a gateway-side check (for example the bridge's registration state
   through the control socket or a gateway log line) or state the limit.
4. Plan line 67: preserve each service's "enabled and running state". `ProfileServices` records
   `active` only (`profile_services.py:224-233`); enablement is never read or restored.
5. Plan line 73: each update action "must show which components and host patches change".
   Section 8 describes the transaction but not the review payload for updates.
6. Plan line 75: removal "restore[s] only recorded configuration keys". See S5.
7. Plan step 3: "Prove that Hermes and its interpreter retain their original locations". Add the
   check to section 7 (compare `running_source()` and `sys.executable` of the probe against the
   review record).
8. Plan line 36 and 49 (dependency proof before review): B4.
9. Plan line 59 (fetch the pinned LifeOS commit directly): now satisfied; `prepare_lifeos` fetches
   the revision with `--depth 1 --no-tags` (`REPO/lifeos_hook_bridge/install_source.py:138-170`,
   commit `5d1b52c3`). The map's finding 2 is stale.

## 3. Verified versus inferred

Verified by reading code: everything cited with a file and line above in `HERMES` and `REPO`,
including the three `evaluate_update_admission` callers, `cmd_install`'s side effects,
`sync_venv`'s plugins=None path and commit order, `prepare_launch`'s lock conditions,
`_tree_matches_completed_stamp`, `write_source_stamp`, `expose_cli` and `_owns_launcher`,
`install.sh` stage behaviour under `--skip-setup`, `ProfileServices` binding rules, the implemented
hold patch location, `consumer_scan`, `host_record`, the manifest counts, and the current worker's
rollback order.

Inferred, not executed: that a `systemd-run --user --scope` unit sits outside the calling
service's cgroup (systemd semantics; the Hermes comments at `gateway.py:3292` describe the workers
as surviving gateway restarts, which is consistent); that config migration during `install.sh`
may or may not rewrite an already-migrated `config.yaml`; that `71d34bad` is on `origin/main`
(the scratch repo has no remote refs; tag `v0.21.7` points at it); that `uv` re-lock needs network
for uncached wheels; and the exact behaviour of `_warn_python_dependencies` when a plugin's
Python dependencies are missing (`hermes_cli/plugins.py:1424`, not read in full).

Not reviewed: the dashboard UI code, `release_catalog.download_integration` beyond its commit
message, and the LifeOS-side patches.

## 4. Raw data

### Stock Hermes evidence

- `hermes_cli/update_contract.py:82-164` `evaluate_update_admission`: layers commit-build, image
  provenance, steward, heuristics; no hold layer in stock.
- Callers: `hermes_cli/main.py:2375-2383`; `hermes_cli/update_cmd.py:647-655`;
  `hermes_cli/web_routers/actions.py:253-261`. Tests only otherwise.
- `hermes_cli/web_routers/actions.py:302-330` `check_hermes_update`: `can_apply: install_method ==
  "git"`, no admission call.
- `hermes_cli/_startup_fast.py:220-237`: passive update message; `source_check.py:382-406`.
- `pm/cli.py:343-398` `cmd_install`; `238-264` `_install_names` with `publish_launchers` for
  `python`; `297-307` `_install_defaults`; `310-340` `_install_python_environments` calling
  `sync_venv(extras or ["all"], explicit=True)`.
- `pm/registry.py:53-66` `source_install_packages`, `tool_roots`.
- `pm/install.py:791-855` `sync_venv`; `736-741` `_publication`; `769-788` `_commit_selection`;
  `652-671` `venv_is_current`.
- `pm/packages.py:408-428` `expected_stamp` (uv.lock digest, extras, python pin, members stamp);
  `430-490` `Venv.apply` with `shutil.rmtree(generation)` on failure.
- `pm/plugins_state.py:118-148` `enabled_plugins_ordered`, `dependency_homes`.
- `pm/publication.py:85-93` sorted `plugins.enabled`/`disabled` written by `PluginSelection`.
- `pm/plugin_eviction.py:78-125` config edits that disable plugins, published like a selection.
- `pm/client.py:208-235` `sync_venv` wrapper; `238-259` `ensure_tools_for_sync`.
- `pm/environments.py:111` `ACTIVATION_INPUTS = ("uv.lock", "pyproject.toml", "pm/lock.json")`;
  `37-38` `install_state_dir`.
- `hermes_cli/venv_sync.py:69-100` `publish_launchers`; `297-312`
  `_tree_matches_completed_stamp`; `315-434` `prepare_launch`; `437-508`
  `_finish_source_update`; `511-553` `_sync_source_dependencies`
  (`evict_incompatible_plugins=True`); `187-191` retry constants.
- `hermes_cli/source_completion.py:29-78` lock; `81-153` `_complete_locked` (launchers, build,
  maintenance, stamp).
- `hermes_cli/source_stamp.py:15-72` `write_source_stamp` (`dirty` from
  `_git_version_info(include_untracked=True)`).
- `hermes_cli/update_cmd_maint.py:982-1075` `_run_post_update_maintenance`; `849-874`
  `_sync_profiles_after_update`.
- `gateway/code_skew.py:22-57`; `gateway/cgroup_cleanup.py:1-45`.
- `hermes_cli/boot_bootstrap.py:27-50, 83-100, 135-143, 222-235`.
- `hermes_cli/post_update.py:166-200` `step_adopt_blessed_checkout`.
- `hermes_bootstrap.py:511-544` `_settle_interrupted_update`.
- `hermes_cli/gateway.py:3137-3147` `_stable_service_working_dir` (HERMES_HOME);
  `3300-3350` unit template (`KillMode=mixed`, `Restart=always`, `ExecStopPost=cgroup_cleanup`,
  `WorkingDirectory=<hermes_home>`); `3292-3294, 4625` systemd-run scope comments.
- `cron/scheduler.py:3800-3840` restart-safe worker dispatch, `dispatch.mode == "scoped"`.
- `tests/hermes_cli/test_kanban_gateway_restart_handoff.py:81` `["systemd-run", "--user",
  "--scope", "--quiet"]`; line 170 `--unit hermes-worker-<suffix>`.
- `hermes_cli/_launchers.py:738-795` `expose_cli`; `531-548` `_publish_conveniences`; `505-525`
  `_owns_launcher`.
- `hermes_cli/update_lock.py:110-130` `_git_common_dir`; `1416-1470` `UpdateLock`.
- `scripts/install.sh:62-64` flags; `583-635` existing-checkout fetch, stash, checkout, ff or
  reset; `684-686, 734-741` `--commit` ancestry and pin; `766-789` `bootstrap_pm` (`pm.cli
  install`, `--without` for skipped tools); `857-879` `stage_products`; `881-899` `stage_config`
  (copies config only if absent); `904-921` `stage_setup`, `stage_gateway`; `923-932`
  `stage_complete`; `962-966` NON_INTERACTIVE skip.
- `.gitignore:92 hermes_cli/web_dist/`, `174 .hermes/`, `180 .hermes-bootstrap-complete`,
  `274 .bytecode-fingerprint`, `281 install-stamp.json`.
- `hermes_constants.py:216-233` `get_default_hermes_root`.
- `scripts/build/freshness.mjs:27` inputs `web/src`, `package.json`, `tsconfig.json`.
- `apps/bootstrap-installer/src-tauri/src/update.rs:204-208, 594`;
  `apps/desktop/electron/managed-ssh-update.ts:8, 539`.
- `git tag --points-at 71d34bad` prints `v0.21.7`; `git branch -r --contains` prints nothing
  (no remote refs in the scratch clone).

### Repository evidence

- `optional/lifeos_release_manager/host_compatibility.py:160-172` `_packaged`; `196-208`
  `_shared`; `254-279` `_working_tree`; `282-295` `_dependencies`; `312-366` `inspect_host`.
- `optional/lifeos_release_manager/host_patches.py:43-96` `stage_host_files`.
- `optional/lifeos_release_manager/release_programs.py:51-94` `fingerprint` (refuses mode &
  0o022); `177-228` `prepare`; `230-263` `apply`; `351-373` `check_recovery`,
  `_check_recovery_entry`; `375-400` `restore`.
- `optional/lifeos_release_manager/release_worker.py:138-172` `_yaml_configuration`; `175-262`
  `_program_plan` (`config.yaml` at 211); `322-450` `_execute` (rollback at 434-448: quiesce,
  `_restore_mount`, `programs.restore`, resume).
- `optional/lifeos_release_manager/consumer_scan.py:21-63` `source_consumers`.
- `optional/lifeos_release_manager/host_record.py:30-37` `build_record`; `76-93` `load_record`;
  `96-118` `check_originals`.
- `optional/lifeos_release_manager/host-compatibility.json`: 1 entry, label `v0.21.7`, 96 files,
  27 added (stock null); top-level dirs `agent cli.py cron gateway hermes_cli model_tools.py
  plugins scripts tests tools`; includes `hermes_cli/update_contract.py`,
  `tests/hermes_cli/test_update_hold.py`, `hermes_cli/plugins.py`; dependencies
  `tree-sitter 0.26.0`, `tree-sitter-bash 0.25.1`, `pathspec 1.1.1`, `mcp 2.0.0`.
- `lifeos_hook_bridge/patches/hermes-update-hold.patch`: `UPDATE_HOLDS_DIRNAME =
  "hermes-update-holds"`, `update_holds_dir` under `_git_common_dir`; refusal codes `update-hold`,
  `update-hold-invalid`; test asserts `.git/hermes-update-holds`.
- `lifeos_hook_bridge/profile_services.py:20-24` units and orders; `67-87` `__init__` binding
  rules; `144-175` `_inspect`; `224-233` `_admission` (records `active` only); `276-317` `resume`.
- `lifeos_hook_bridge/install_source.py:138-170` `prepare_lifeos` fetches the pinned revision
  with `--depth 1 --no-tags` and checks `expected_tree`.
- `docs/in-place-installation-design.md` lines 92 and 111 name `<install state>/update-holds`;
  lines 84, 129 give 94, 26, 68.
- Recent commits on the branch: `679c24ee` consumer scan, `3829e62d` host record and drift,
  `9ff3a022` update holds, `7e71dc12` design doc, `9ffa8deb` host staging, `5d1b52c3` pinned
  LifeOS fetch, `fa7c5fae` compatibility check.
