<!-- Saved by the parent agent on 2026-10-17 from the subagent's final reply; the subagent could not write files. -->

# Release manager map for the in-place redesign

Date 2026-10-17. Role: read-only code mapper. Model: Sonnet 5.5. Question: map the release manager and its bridge counterparts for the in-place Hermes patching redesign.

**The report file was not written.** My tools are read-only, with no Write tool and no file creation allowed. The requested path `/home/outsider/Projects/Hermes_agent/LifeOS_plugin/docs/agents/2026-10-17-in-place-design-mapping/release-manager-map.md` does not exist. Save this message there if you want the file.

All paths below are under `/home/outsider/Projects/Hermes_agent/LifeOS_plugin`. `OPT` means `optional/lifeos_release_manager`. `BR` means `lifeos_hook_bridge`.

## 1. Catalog, certificate, builder, qualification

### Discovery and download: `OPT/release_catalog.py`

- **Repository.** `REPOSITORY = '0ut5ider/lifeos-hermes-plugin'` is fixed (line 16). The default origins are `https://api.github.com` and `https://github.com` (line 92).
- **Release lookup.** `download()` (144-185) sets the selector to `latest` or `tags/v<version>`. It queries `GET {api}/repos/<repo>/releases/<selector>` (148). Requests are sent with `User-Agent: LifeOS-Hermes-release` (97).
- **Version format.** Versions must match `X.Y.Z` or `X.Y.Z-(dev|rc).N` (line 20).
- **Release checks.** The tag must be `v<version>`, `draft` must be false, and `latest` additionally requires `prerelease` false (149-154).
- **Asset checks.** `_asset()` (107-118) requires all of the following:
  - the name matches `[a-zA-Z0-9_.-]+`;
  - the size is an int with `0 < size <= 1 GiB`;
  - the API `digest` is `sha256:<64 hex>`;
  - `browser_download_url` equals exactly `https://github.com/<repo>/releases/download/<tag>/<name>`, with no query or fragment.
- **Required assets.** `RELEASE-CERTIFICATE.json` and `hermes-dashboard.tgz` must be listed (163). The archive is named `<version>-<program_commit[:8]>.tgz` (178). A real example is `0.7.3-70fa8390.tgz`, 288,173,954 bytes, with `hermes-dashboard.tgz` at 1,542,030 bytes.
- **Download order.** The certificate is fetched first and capped at 512 KiB (169). Then the archive and the dashboard tarball are fetched.
- **Download checks.** `_download()` (120-142) streams to a temporary file. It enforces the declared size and the SHA-256 from the API metadata, then does `fsync` and `os.replace`.
- **Extraction.** `extract_package()` (54-88) accepts gzip tar with only regular files and directories. It rejects absolute paths, `..`, backslashes and duplicate names. Limits are 100,000 members and 5 GiB extracted. Files are written `0600`, or `0700` if executable, into a private staging directory and then renamed.

### Certificate and authenticity

- **Checked fields.** The catalog reads only these fields (173-183):
  - `format == 1`
  - `status == 'QUALIFIED'`
  - `version == tag[1:]`
  - `program_commit`, a 40-hex string
  - `archive_sha256` and `archive_bytes`, which must equal the archive asset's published digest and size
  - `hermes_dashboard_sha256`, which must equal the dashboard asset's digest
- **No signature, no pinned key.** There is no cryptographic signature of the certificate and no pinned key.
- **Trust anchor.** Authenticity rests on three things: HTTPS to GitHub, the per-asset `digest` field in the GitHub API response, and the certificate binding the archive and dashboard hashes. A compromised release or API response would be accepted.
- **Duplicate JSON fields.** They are rejected by `_unique_pairs`.
- **Other fields ignored by the catalog.** `release_stage.validate_package` (which you already read) applies further package checks.
- **Full certificate shape.** `docs/verification/2026-10-16-release-0.7.3/RELEASE-CERTIFICATE.json` has 4,225 bytes. Besides the six fields above it carries:
  - `production_qualified`
  - `hermes_base`, `lifeos_base`, `hermes_patch_count` (10) and `lifeos_patch_count` (25)
  - `final_independent_review`, `independent_review_rounds`, `reviewed_repository_head`
  - `source_review_equivalence`, `unresolved_findings`
  - test-count fields (`exact_archive_*`, `integration_*`)
  - `inherited_release`, `inherited_release_certificate_sha256`, `inherited_checks`
  - `known_baseline_limits`
  - `qualification_receipt_sha256` (map of receipt file to hash)
  - false flags: `personal_data_imported_or_reset`, `development_promotion_verified`, `daily_promotion_verified`, `automatic_morning_observed`, `whole_guest_restore_repeated`, `single_clean_full_run`

### Builder: `scripts/build_managed_release.py` (82 lines)

- **Requirements.** The tracked tree must be clean (22-23). Required arguments are `--output`, `--hermes-source`, `--lifeos-source` and `--python-closure`.
- **Package directory.** It creates `<output>/<VERSION>-<head[:8]>/`.
- **`git archive` of selected paths** (29-32): `lifeos_hook_bridge`, `optional`, `scripts`, `tests`, `docs/deployment/daily-text`, `VERSION`, `CHANGELOG.md`, `README.md` and `docs/verification/2026-10-11-daily-guest/deliver_morning.py`.
- **Prepared patched Hermes tree.** `hermes/` comes from `install_source.prepare_supported_hermes` (39).
- **Stock archive.** `stock-hermes.tgz` comes from `stock_hermes.build_archive` (41). It is a plain `git archive` of the pinned commit.
- **Patched LifeOS tree.** `lifeos/` comes from `prepare_lifeos` with `SUPPORTED_LIFEOS_COMMIT` and `LIFEOS_PATCHES` (42).
- **Python runtime.** `python-runtime/` holds `pyproject.toml`, `uv.lock` and `plugin-deps/` (44-49).
- **`DAILY-CANDIDATE.json`** (51-62). Its fields are:
  - `version`, `head`, `status: 'release_candidate'`
  - `stock_hermes` = `{format:1, commit, path:'stock-hermes.tgz', sha256, bytes}`
  - `plugin_files` (`lifeos_hook_bridge/<rel>` mapped to sha256)
  - `manager_files` (files of `optional/lifeos_release_manager`)
  - `python_runtime_files`
  - `daily_configuration_files` (`docs/deployment/daily-text/*`)
  - `prepared_manifest_files` (hashes of `hermes/hermes-source-manifest.json` and `lifeos/lifeos-source-manifest.json`)
  - `operators.morning` = `{path, sha256}`
  - `native_manifests_verified: True`, `combined_release_verified: False`, `live_selection_changed: False`
- **Outputs.** It writes the tgz of the package directory, excluding `__pycache__`. It also writes `<package>-build.json` with `archive_bytes`, `archive_sha256`, `hermes_base`, `lifeos_base` and the patch counts.
- **Other assets.** `hermes-dashboard.tgz` is not produced by this script. I found no script that builds it; the build records under `docs/verification/` reference it.

### How the certificate is created

- **No certify script in `scripts/`.** `CONTRIBUTING.md` lines 71-77 say a build creates a candidate, not a certificate.
- **Per-release scripts.** Each release has its own `certify_release.py` under `docs/verification/<date>-release-X/`. Examples are `2026-10-16-release-0.7.1/certify_release.py` (37 lines), `2026-10-14-release-0.5.0/` and `2026-10-12-release-0.4.1/`.
- **What the 0.7.1 script does.** It asserts the build output, archive hash, size and head. It also asserts the PASS status of the review-equivalence, package-verification, native-delta, archive-integration, process-boundary and installed-verification receipts. It then writes `RELEASE-CERTIFICATE.json` with `open('x')`.
- **0.7.3 has no `certify_release.py`.** Its record is `docs/verification/2026-10-16-release-0.7.3/`, containing `README.md`, `package-identity.json`, `release-publication.json`, `QUALIFICATION-PROVENANCE.json`, `qualification/` and `deployment/`.
- **Publication.** `release-publication.json` shows assets uploaded without clobbering prior assets (73 preserved). There are no other generator scripts for `release-publication.json`.
- **Related files.** `scripts/release_transaction.py` (301 lines) is a separate older stage/apply/restore tool for hermes, plugin and LifeOS trees. `tests/test_release_transaction.py` covers it. `scripts/system_overlay_snapshot.py` supports it.

## 2. Services

### Units: `BR/profile_services.py:20`

```
UNITS = {'gateway': 'hermes-gateway.service',
         'dashboard': 'hermes-dashboard.service',
         'pulse': 'com.lifeos.pulse.service'}
```

- **Stop order.** gateway, pulse, dashboard (line 22).
- **Start order.** dashboard, pulse, gateway (line 23).
- **No other units.** Memory workflows use transient `lifeos-memory-<job>-<hex8>` units. The dashboard uses transient `lifeos-bridge-<action>-<hex>` and `lifeos-bridge-selection-<hex>` units, all started through `systemd-run --user --collect`. Those are not part of `ProfileServices`.

### Fresh-install unit creation: `OPT/release_services.py`

- **`service_files(request, generated)` (39-69).** It writes three units to `<home>/.config/systemd/user/`. Existing regular files are kept as they are; only missing ones are generated.

  | Unit | WorkingDirectory | ExecStart |
  | --- | --- | --- |
  | `hermes-gateway.service` | profile | `~/.local/bin/hermes gateway run --external-supervisor` |
  | `hermes-dashboard.service` | `installed.parent` (account home) | `~/.local/bin/hermes dashboard --isolated --no-open` |
  | `com.lifeos.pulse.service` | `<installed>/LIFEOS/PULSE` | `~/.local/bin/bun --no-install <installed>/LIFEOS/PULSE/pulse.ts` |

- **Common settings.** `Type=simple`, `Environment=HERMES_HOME=<profile>`, a `PATH` of `~/.local/bin:/usr/local/bin:/usr/bin:/bin`, `PYTHONDONTWRITEBYTECODE=1`, `UMask=0077`, `KillMode=control-group`, `TimeoutStopSec=45s`, `Restart=on-failure`, and `WantedBy=default.target`. The header says "without enabling it".
- **Path rules.** `_service_paths` (32-37) rejects whitespace, quotes, `$`, `;` and `}` in home, profile and installed paths. Paths must be physical, not symlinks.
- **`require_fresh_services` (19-21).** It refuses a release whose `ProfileServices` lacks a `first_installation` parameter. This raises `FirstInstallationUnavailable`.
- **`fresh_services` (72-82).** It subclasses `ProfileServices(first_installation=True)`. Only the `dashboard` role is bound, and the journal directory is `<profile>/.lifeos-installation-services` (profile_services.py:76,84). `_inspect` also folds in `dashboard_binding`.
- **`dashboard_binding` (94-138).** It checks the following:
  - the main PID's `/proc` cmdline resolves to a `dashboard` or `serve` command;
  - the home reported by `hermes_cli.dashboard_procs._hermes_home_for_pid` equals the profile;
  - `Environment=HERMES_HOME` equals the profile, with no `EnvironmentFiles`;
  - any `--profile` flag resolves to that profile;
  - otherwise the active profile is `default`.
- **`fresh_preview` (141-175).** It requires all of these:
  - the dashboard `ExecStart path=` is `~/.local/bin/hermes`;
  - the fragment is `~/.config/systemd/user/hermes-dashboard.service`;
  - there are no drop-ins;
  - `check_dashboard_writers` passes.

  Any existing gateway or pulse unit must be inactive and match the fixed WorkingDirectory, fragment, executable and args exactly, with `KillMode` of `mixed` or `control-group`. Otherwise it raises "Fresh installation preserves an existing service from another deployment".
- **`check_dashboard_writers` (178-199).** It scans `/proc` for the user's own `dashboard` or `serve` processes whose Hermes home equals the profile. Each must be in the owner service's cgroup (`0::<ControlGroup>`). A foreground dashboard is refused with "Run this profile dashboard through its owner user service".
- **`verify_installed_services` (202-205).** It runs `systemctl --user daemon-reload` and then `ProfileServices(...).preview()` with all three roles.

### `ProfileServices` operations

- **`_inspect` (144-175).** It requires `LoadState=loaded`, `NeedDaemonReload=no`, no RootDirectory or RootImage, and `KillMode` of `mixed` or `control-group`. WorkingDirectory must equal the role's fixed directory, with `directories` set at line 86. Definition files must be owner or root files, not group/other-writable, and at most 256 KiB. Their hashes are bound into a digest. The control group must be under `user@UID.service/`.
- **`preview` (236-241).** It returns a signature of the admission without changing anything. It refuses if a prior journal is not `active`.
- **`drain(signature)` (243-253).** It takes the installation lock plus a `flock` on `<state>/lock`. It publishes a journal of state `stopping` that records each unit's definition digest, `active` flag and control group. It then stops units, and each must be inactive/failed with `MainPID=0` and `cgroup.events` showing `populated 0`. The journal state becomes `stopped`.
- **`quiesce` (255-265).** It re-drains from an existing journal after re-checking definitions.
- **`verify_stopped` (267-274).** It requires state `stopped` and every cgroup empty.
- **`resume(roles=None, activate=False)` (276-317).** It drains first if the state is `stopping`. It starts units that were `active` before, in start order, and publishes `starting` then `active`. It verifies each active unit has a MainPID. `roles` and `activate` allow starting a chosen subset, including newly created units.
- **Journal.** `<profile>/.lifeos-services/operation.json` has fields `version, profile, installed, installed_physical, state, services`. States are `stopping|stopped|starting|active`.
- **`status()` and `verify_active()` (319-339).** Both read the journal.
- **Not covered by `ProfileServices`.** Other Hermes processes, such as CLI sessions and cron workers, are not enumerated. Removal does this separately through `removal_consumers`.

### `BR/installation_lock.py` and `BR/program_lock.py`

- **`installation_lock(profile, wait=False, lease=None)` (145-177).** It is an exclusive `flock` on `<profile>/.lifeos-installation/lock`. It yields a `_InstallationLease`. The lease can be borrowed by nested operations in the same pid and thread. It re-verifies device, inode and permissions on entry and exit. Raises `InstallationBusy` if not waiting.
- **`program_lock` (63 lines).** It uses `<profile>/.lifeos-installation/program.lock`. Turns take a shared non-blocking lock (`shared()`, returns `None` while a swap holds the lock). Update, restore, recover and removal use `exclusive(profile, timeout)`. The timeout is 600 s in update_worker (`TURN_WAIT_SECONDS`) and removal publication.
- **Hermes updater lock.** Neither module coordinates with it.

## 3. `OPT/release_initialization.py` `NativeInitialization` (class at line 33)

- **Setup.** `user = installed.parent/.config/LIFEOS/USER`. `seed = job/native-seed`. `journal = job/native-initialization.json`.
- **Journal.** Fields are `format, binding, installed, user, native_identity, user_identity, state`. The `binding` is `request_digest(request)`. States are `prepared`, `publishing-user`, `publishing-native` and `complete`.
- **`prepare` (about 53-101).** It refuses if `installed` or `user` already exist. A stale seed is renamed `native-seed-incomplete-<hex>`. It then:
  1. copies `<runtime.reference>/LIFEOS/USER` to `seed/user` (mode `0700`);
  2. calls `fresh_store._empty_personal_templates`, which empties personal TELOS, HEALTH, FINANCES and WORK. Examples are kept outside the active tree;
  3. rewrites `IDENTITY_FILES` (`CONFIG/LIFEOS_CONFIG.toml`, `PRINCIPAL/PRINCIPAL_IDENTITY.md`, `DIGITAL_ASSISTANT/DA_IDENTITY.md`) with the principal name (`request['name']`) and assistant name (`request['assistant']`). Originals are saved to `job/fresh-templates/identity-originals/`;
  4. copies the reference `.claude` tree to `seed/native` with symlinks preserved;
  5. replaces `LIFEOS/USER` with a symlink to `~/.config/LIFEOS/USER`;
  6. moves `LIFEOS/MEMORY` into `user/MEMORY` and links it back;
  7. rewrites the reference parent path in `settings.json` to the account home;
  8. records the `prepared` journal.
- **`execute` (about 103-142).** It publishes in three steps:
  1. rename `seed/user` to `~/.config/LIFEOS/USER`;
  2. rename `seed/native` to `~/.claude`;
  3. record `complete`.

  Checkpoints exist at each step. Resume re-verifies fingerprints and refuses later edits.
- **Caller.** `release_worker._fresh_native` (line 265), using `fresh_store` as the helpers module.
- **Not done here.** There is no `bun` install, no mount, and no baseline. Those occur elsewhere in `release_worker`.

## 4. `BR/install_source.py`

### Constants (26-70)

- `UPSTREAM_LIFEOS` is `https://github.com/danielmiessler/LifeOS.git`.
- `SUPPORTED_LIFEOS_COMMIT` is `5e2f2e8c0abde612da0e99c16c0d07d4ec21b88c`.
- `SUPPORTED_HERMES_COMMIT` is `71d34bad1045610252eda02ee79549436896e784`.
- `HERMES_PATCHES` has 10 entries (lines 29-40):
  - plugin-events
  - turn-gates
  - command-policy
  - session-lifecycle
  - child-routing
  - strict-inference
  - remote-files
  - cron-bootstrap
  - required-middleware
  - web-result-status
- `LIFEOS_PATCHES` has 25 entries (lines 41-67), from `lifeos-task-governance` to `lifeos-content-response-consumption`.
- `INSTALL_STEPS` are `InstallSettings, DeployCore, ScaffoldUser, LinkUser, InstallHooks, ActivateImports`.
- Patch files live in `BR/patches/`.

### LifeOS side

- **`prepare_lifeos(source, target, supported_revision, patches, patch_names)` (145-182).**
  1. `git ls-remote source HEAD` must equal the supported commit. Upstream HEAD must still be that commit; this is the dependency the in-place plan wants removed.
  2. `git clone --no-checkout`, then checkout of the revision.
  3. For each patch: `git apply --check` then `git apply`. Then `git diff --check`.
  4. `native_capabilities.install_capability_record(stage/'LifeOS/install')` is run via `runpy`.
  5. It writes `lifeos-source-manifest.json` with `{upstream, upstream_commit, patches:[{name,sha256}], tree_sha256}`.
  6. It clears group/other write bits and does an atomic rename.
- **Capability record** (`BR/native_capabilities.py`, 40 lines). `install_capability_record` copies `native_capabilities.json` into `hooks/lifeos-bridge-capabilities.json`, but only if `hooks/` exists and every listed file hash matches. The only listed file is `TaskGovernance.hook.ts` with a pinned sha256. The contract is `task_session_count: 1`, with `source_commit` set to the LifeOS commit. `supports_task_count(root)` re-verifies it.
- **`validate_candidate` / `validate_prepared_lifeos` (123-142, 190-192).** They check the manifest commit and patch list/hashes against the current patch files. They also check `git rev-parse HEAD` and the recomputed tree digest, which excludes `.git` and rejects symlinks and non-regular files.
- **`install_lifeos(candidate, installed, failed, bun, rev, patches, names)` (278-357).**
  - Preconditions: `installed.name` is `.claude`, `installed` and `failed` do not exist, and `bun` exists on `PATH`.
  - Environment: `HOME`, `CLAUDE_CONFIG_DIR`, `LIFEOS_DIR`, `LIFEOS_CONFIG_DIR` (`~/.config/LIFEOS`) and `PROJECTS_DIR`.
  - It copies `install/CLAUDE.template.md` to `CLAUDE.md`.
  - For the supported revision it validates dependency locks from `BR/dependency_locks/catalog.json`, seeds them, and uses a dependency environment.
  - It runs each `Tools/<Step>.ts` through `bun` with `--config-root --config-dir --skill-root --apply`, with a 300 s timeout each.
  - It verifies `LIFEOS/VERSION` equals the source version and that `settings.json` has hooks.
  - On failure it renames `installed` to `failed`.
  - Returns `{installed_version, upstream_commit, steps, restart_required, dependencies?}`.
- **`finalize_lifeos` (365-403).** It needs `LIFEOS/HERMES/Mount.ts`, `settings.json` and `config.yaml`. It builds `memory_administration.mount_environment`. It creates a version-drift baseline and runs `MountTransaction.execute(..., baseline_data=...)`.

### Hermes side

- **`prepare_hermes` (216-247).** The source must be a regular directory at the supported commit, with a clean `git status --porcelain --untracked-files=all`. It clones locally into a stage, applies patches, and writes `hermes-source-manifest.json` (`{base_commit, patches, tree_sha256}`).
- **`validate_hermes_candidate` / `validate_supported_hermes` (195-213, 258-260).** These are the same checks for the Hermes candidate.

### In-place host patch (429-780)

- **`_patch_paths` (429-442).** It lists changed and untracked files in the candidate relative to `HEAD`, excluding the manifest. This is the set of 94 files per the host-compatibility record.
- **`_write_patch_state` (449-459).** It writes the manifest through a temp file with `chmod 0600` and `os.replace`. There is no `fsync` of the file or directory.
- **`_write_patch_files` (524-541).** It copies with `copy2` into a temp file in the destination directory and `os.replace`. A target whose value for the field is `None` is unlinked. The source hash is checked first. There is no `fsync`.
- **`stage_hermes_patch(snapshot, current, candidate, config, revision, patches, names)` (468-512).** It validates the candidate. The `current` tree must be a regular directory at the supported commit with a clean status. `config` must be a regular file, and the snapshot must be new and outside both trees. Under a `0700` stage it saves:
  - `files/<path>`: a `copy2` of each existing target;
  - `config.yaml`: a copy of the config;
  - `manifest.json` with `state: 'staged'`.

  Manifest fields are `current, candidate, config, config_hash, revision, patches, patch_names, files: {path: {before: sha|None, after: sha}}`.
- **`apply_hermes_patch` (544-608).**
  1. It requires state `staged` and revalidates the candidate, the `current` commit and clean status, and the config hash. It also checks every `before` hash and every saved backup.
  2. It sets the state to `applying`.
  3. It runs `stop()` and then copies the candidate files into `current`. It checks every `after` hash, runs `start()` and `verify()`, and rechecks the config hash.
  4. On error before any copy, the state is `failed_preflight`. On error after copying, it runs `stop`, restores the backups, restores the config, runs `start` and `verify_restored`, and checks that git is clean. The result is `rolled_back` on success or `rollback_failed` on failure.
  5. Success sets the state to `applied`.
- **`request_hermes_restore` / `cancel_hermes_restore` (676-692).** These toggle `applied` to `restoring`, and back with an error message.
- **`restore_hermes_patch` (611-645).** It accepts `applied` or `restoring`. Each target must still equal its `after` hash. It runs `stop`, writes the `before` files, `start`, `verify`, and checks that git is clean. On failure it reapplies the candidate (`applied` with an error message, or `restore_failed`). Success sets `rolled_back`.
- **`recover_hermes_patch` (648-673).** It accepts `applying` or `restoring`. It stops, restores the `before` files and, for an interrupted apply, the config, then starts, verifies and checks git. The state becomes `rolled_back` or `rollback_failed`.
- **Journal states.** `staged`, `applying`, `applied`, `restoring`, `failed_preflight`, `rolled_back`, `rollback_failed`, `restore_failed`. The dashboard adds a derived `interrupted` state when `applying` or `restoring` has a recorded unit that is no longer active.
- **Worker (695-780).**
  - Systemd units: `_systemctl` and `_run_hermes_patch_job` use only `hermes-gateway.service`.
  - Hard launcher requirement: `_run_hermes_patch_job` requires the gateway's `ExecStart path=` to equal `<current>/.hermes/bin/hermes` (732-737). `_verify_gateway` runs `<current>/.hermes/bin/hermes config check` (713-720). This is the managed-layout launcher, not a normal user install.
  - Apply and restore need the gateway active. After restart the `MainPID` must differ from the previous one. It sleeps 3 s and runs `hermes config check` with `HERMES_HOME`.
  - `run_hermes_patch_job` takes `installation_lock(config.parent, wait=True)`. Only the gateway is stopped. The dashboard, Pulse and other consumers are not.
  - CLI: `python install_source.py {apply|restore|recover} <snapshot>`.
  - On failure, the CLI sets a `staged` manifest to `failed_preflight` and a `restoring` manifest back to `applied`.

## 5. Complete removal (`OPT/removal_*.py`)

The sequence follows `removal_workflow.execute` (51-103).

1. **Gate, `removal_preparation.returned` (9-35).** A verified provider-return workflow must exist. `ownership_enabled` must be false, and the workflow's status, receipt and review signatures must match. `MemoryTransition` and `MemoryReturn` states are re-checked.
2. **Select the generation, `removal_generation.selected` (270-311).**
   - `account()` requires profile `~/.hermes` and installed `~/.claude`, with no named profiles.
   - `integration-release.json` must be `verified` by `release_version.status`.
   - Exactly one `.lifeos-releases/<id>` job must be `applied` and match the request and identity.
   - The account launcher `~/.local/bin/hermes` must equal `launcher_script(job/bin/hermes)`.
   - `validate_package` runs on the package, the runtime source fingerprint is compared, and `DAILY-CANDIDATE.json` hashes are checked against `plugins/lifeos-hook-bridge` and `plugins/lifeos-release-manager`.
   - Launchers `hermes`, `hermes-agent`, `hermes-acp` and the `bun` identity are checked.
   - This module is tied to the replacement-runtime model. It selects `job/bin/hermes` and a program snapshot.
3. **Prepare, `removal_preparation.prepare` (102-196).** Under `installation_lock`:
   - `basic_settings` requires dashboard password auth. The owner must be `dashboard:basic:<username>`.
   - No other release job may be pending.
   - `_consumers` (85-99) combines `ProfileServices._admission` with `removal_consumers.unit_files`. That scans all user unit paths and `systemctl list-units` output for anything using the installed tree, the lifeos plugin, `bun` or the profile. It also runs `removal_consumers.processes`, a `/proc` scan outside the known cgroups.
   - `removal_ownership.guard` proves the four native guard files (`__init__.py`, `guard.py`, `plugin.yaml`, `policy.json` under `plugins/lifeos`) from the committed `MountTransaction` journal.
   - `removal_ownership.pulse` proves the Pulse unit was created by an applied fresh release's program journal.
   - The stock runtime comes from `prepare_runtime(..., stock=True)` using `stock-hermes.tgz` from the package. `removal_runtime.launchers` rewrites the launchers' bytecode selection.
   - Retained recovery copies of the bridge and manager are copied to `removal/recovery-bridge` and `removal/recovery-manager`.
   - `removal_inventory.native` demands every native program file match the qualified source. Anything unreviewed under `hooks`, `skills`, `agents`, `commands`, `test` or `LIFEOS` blocks removal. `USER`, `MEMORY` and `PULSE/state` are retained.
   - `settings.json` hooks are stripped with `update_hooks.replace_owned_hooks(current, owned, {})`.
   - `removal_preparation.software` builds the `ProgramTransaction` plan and `RemovalServices.prepare`.
   - A signed `plan.json` is written, along with `operation.json` (`state: ready`), `owner-policy.json` and a `recover` script.
4. **What the plan restores or removes** (`removal_preparation.software`, `removal_configuration`).
   - **Directories removed:** `plugins/lifeos`, `plugins/lifeos-hook-bridge` and `plugins/lifeos-release-manager`.
   - **Files removed:** native program files, the Pulse unit file, the account `bun`, `lifeos-memory.json`, `lifeos-installation.json` and `integration-release.json`.
   - **`config.yaml`:**
     - `memory.provider` is removed, with `memory_enabled` and `user_profile_enabled` set true. The prior provider must already be `builtin`.
     - The three plugin names are filtered out of `plugins.enabled`, `plugins.disabled` and `plugins.entries`.
     - The installed `skills` path is filtered from `skills.external_dirs`.
     - `platforms.discord.enabled` is set false.
   - **`.env`:** the `HERMES_WRITE_SAFE_ROOT=<workspace>:<profile>` block is removed and `_sanitize_env_lines` is applied.
   - **Launchers:** `hermes`, `hermes-agent` and `hermes-acp` are repointed to `job/stock-runtime/bin/*`. Removal installs a stock runtime from the archive and does not restore original files.
   - **Retained:** the native store (`LIFEOS/USER`, `MEMORY`), `~/.config/LIFEOS/USER`, Hermes `memories/`, `SOUL.md` and the workspace. `RemovalPublication.__init__` refuses to target personal data.
5. **Apply, `removal_publication.RemovalPublication.apply` (274-298).** It holds the `installation_lock` and an exclusive `program_lock` (600 s). The journal `removal/operation.json` moves through these states:
   - `draining`: `RemovalServices.stop`, after `daemon-reload`.
   - `publishing`: inside `barrier` (a `BEGIN IMMEDIATE` read-only SQLite lock on the native registry). The native signature is checked before and after `ProgramTransaction.resume`.
   - `restarting`: `RemovalServices.resume`. Pulse is not started; only previously active Hermes services are.
   - `verification_required`.
   - `verified`: `verify()` runs a fresh stock agent probe, via `memory_workflow._probe`, and demands `provider == builtin`, no LifeOS plugins and unchanged retained files.

   Also defined are `ready`, `restoring` and `rolled_back`.
6. **Rollback and recovery.** `rollback` restores programs from `ProgramTransaction.restore()`, resumes services with `restored=True` and sets `rolled_back`. `removal_recovery.py` is a standalone password-authenticated CLI (`recover` or `rollback`). It uses the stock Hermes `BasicAuthProvider` and relaunches the memory workflow. `removal_bootstrap.py` validates the retained files. `removal_state.retained` and `prepared` bind `.lifeos-removal.json` to a signed plan and a retained owner policy.
7. **`RemovalServices`** (`removal_services.py`) binds the original and removed unit definitions. `prepare` requires Pulse to be inactive and disabled/static. It checks that exactly the Pulse fragment and its drop-ins are removed and that gateway and dashboard definitions are untouched. `stop`, `resume` and `verify` check that definitions, cgroups, `LoadState` and WorkingDirectory match the review.

## 6. Bridge side

- **`release_version.py` (93 lines).**
  - `versions(package)` requires `VERSION`, `plugin.yaml` and `dashboard/manifest.json` to agree on one version.
  - `status(profile, plugin)` returns `{active, staged}`. `active` carries `{version, verification, verification_scope: 'plugin_sources'}`. If `<profile>/integration-release.json` exists, `active` also gets `version, commit, package_sha256, recorded_version, modified_files`, and `verification` becomes `verified` or `modified`.
  - The receipt must be `format 1`, and its `plugin_files` hashes are checked against the plugin dir. Extra files also count as modified.
  - `integration-candidate.json` is the staged receipt.
- **`lifeos-version` command.** It is registered in `BR/cli.py` (the `register_commands` function). `run_version` (about line 164) prints `status(get_hermes_home(), Path(__file__).parent)` as JSON, or an error message with exit 1.
- **`memory_administration.py` (223 lines).**
  - `required(installed, profile)` (86-101): managed mounting is required if `LIFEOS/USER/CONFIG/memory-access.json` exists. Otherwise it is required if `lifeos-memory.json` exists and ownership is enabled. It also returns true if the installed `LIFEOS/` is missing or the config is unreadable.
  - `issue` (118-143): signed HMAC authorizations stored in `<profile>/.lifeos-memory-admin/<nonce>.json`. The account must start with `dashboard:`, the maximum ttl is 3600 s, and the purpose is `mount`, `recover` or `transition`.
  - `validate` (146-180) and `revoke` (183-187).
  - `mount_environment(installed, profile, authorization, binding)` (190-209): copies `os.environ`, drops the internal memory variables, and sets `HOME=<installed.parent>` and `HERMES_HOME`. If required it validates the grant and sets `LIFEOS_MEMORY_ADMINISTRATION`.
  - `job_binding(job, request, action)` (212-214): `{job, request_digest (without memory_authorization), action}`.
  - `lease` (217-223): a context manager that issues and then revokes.
- **`mount_transaction.MountTransaction` (502 lines).**
  - The journal is `<profile>/.lifeos-mount/operation.json`. Per-operation snapshot directories contain `stage/`, `previous/`, `selected/` and `identity.json`.
  - Mounted files (line 20): `config.yaml`, `SOUL.md`, `.env`, `plugins/lifeos/{__init__.py, guard.py, plugin.yaml, policy.json}`. The version-drift baseline file is also included when a baseline is given.
  - `execute(environment, bun, hermes, baseline_data, binding, retain_for_rollback)` (402-502):
    1. It requires installed `Mount.ts` to support `LIFEOS_MOUNT_DESTINATION`.
    2. It runs `bun --no-install Mount.ts` into the stage directory.
    3. It parses `mount-plan.json`, which must have the keys `{version, home, keepOutputFormat, signature, previous_digest}`.
    4. It enables batch edits and checks the prepared config.
    5. It records before and after digests and modes (`0600` after) in a manifest.
    6. It publishes while validating the grant and memory signature under a configuration lock.
    7. It runs `Mount.ts --check` and `hermes config check`, then verifies the targets.
    8. It writes `committed`.
    9. Any exception restores via `_restore`.
  - States: `prepared`, `applying`, `restoring`, `committed`, `rolled_back`. `PENDING = {prepared, applying, restoring}`.
  - Other methods: `status`, `recover`, `restore_completed` and the `for_selection` classmethod.
  - The source stamp covers `Mount.ts`, the identity/Telos files, skills' `SKILL.md` files and the plugin files.
- **`version_drift.py` (233 lines).**
  - The baseline is `~/.local/state/lifeos-hook-bridge/version-drift-baseline.json` by default.
  - Schema 2 holds `version, created_at, source_commit, source_root, installed_root, files{path: sha256}`.
  - `CORE_PATHS` are `hooks/, LIFEOS/ALGORITHM/, skills/, settings.json, CLAUDE.md, LIFEOS_SYSTEM_PROMPT.md, LIFEOS/TOOLS/, agents/, commands/, LIFEOS/PULSE/, LIFEOS/ATLAS/, test/, LIFEOS/DOCUMENTATION/`.
  - `PLUGIN_SOURCE_FILES` adds `LIFEOS/TOOLS/lib/MemoryAccess.ts` and `hooks/lifeos-bridge-capabilities.json`.
  - `git_response` answers only a fixed set of Git queries used by the native VersionDrift hook. There is no home-directory repo.
- **`update_plan.py`.**
  - `plan_system_files` compares the installed baseline, the prepared source and a reference install. It lists add/replace/remove actions and refuses edited or colliding files.
  - `apply_system_plan` applies them to a staged copy.
- **`update_hooks.replace_owned_hooks(current, old, new)`.** It replaces exact old LifeOS hook entries and keeps unrelated hooks. It refuses edited, ambiguous or colliding entries.
- **`update_dependencies.sync_dependencies`.** It syncs `package.json`, `bun.lock` and `node_modules` under source-owned roots.
- **`update_transaction.py` (455 lines).** It uses a staged directory and swap, with `MOUNT_FILES = config.yaml, SOUL.md, .env` and `MOUNT_DIRS = plugins/lifeos`. States are `prepared`, `stopped`, `swapped`, `applied`, `failed_before_stop`, `rolled_back`, `rollback_failed`, `restore_stopping` and `restoring`. It is built around a snapshot of the installed `.claude` tree. This is the LifeOS `~/.claude` update path.
- **`update_worker.py` (277 lines).** It runs under the `installation_lock` and `program_lock.exclusive`. It re-installs the candidate into a reference home to compute the plan, then `apply_update`. It stops and starts only `hermes-gateway.service` and checks that the gateway `ExecStart` path equals the `hermes_command` in the request. Its `verify` step also runs `Doctor.ts --hooks`, `Mount.ts --check`, `hermes config check` and the drift check.

## 7. Dashboard host-patch endpoints and hook registration

### `BR/dashboard/plugin_api.py`

Module-level paths:

- `HOST_PATCH_ROOT = ~/.local/state/lifeos-hook-bridge/host-patches` (61)
- `HERMES_CANDIDATE = ~/.local/share/lifeos-bridge/hermes-candidate` (60)
- `PATCHED_HOOKS` (the same five-hook set as in `__init__.py`)

`_host_source()` (801-808) is `Path(hermes_cli.plugins.__file__).resolve().parents[1]`. That is the source the dashboard actually imports (the `HOST_SOURCE` override is only for tests).

| Endpoint | Behavior |
| --- | --- |
| `GET /installation` (824-884) | Reports `hermes` as `stock`, `patched_hooks_present` or `partial` by comparing `PATCHED_HOOKS` with `VALID_HOOKS`. It also returns candidate readiness and `dashboard_restart_required`. |
| `POST /installation/prepare-hermes` (962-971) | Requires LifeOS installed. Calls `prepare_supported_hermes(_host_source(), HERMES_CANDIDATE)`. |
| `GET /installation/host-patch` (1328-1345) | Reads the latest snapshot's `manifest.json` by mtime. If the state is `applying` or `restoring` and the recorded unit is not `active`, returns `interrupted`. |
| `POST /installation/apply-hermes` (1368-1392) | Refuses if the state is in `staged, applying, applied, restore_failed, rollback_failed`. Stages `patch-<hex>` under `HOST_PATCH_ROOT`, then `_launch_host_patch(snapshot, 'apply')`. Cleans up on error. |
| `POST /installation/restore-hermes` (1395-1414) | Requires `applied`, calls `request_hermes_restore`, then launches. Cancels the request if the launch fails. |
| `POST /installation/recover-hermes` (1417-1431) | Requires `interrupted`. Launches `recover`. |

`_launch_host_patch` (1348-1365):

- It requires `hermes-gateway.service` to be active, except for `recover`.
- It stores a unit name `lifeos-bridge-<action>-<hex>` in the manifest.
- It runs `systemd-run --user --collect --unit=... --setenv=HERMES_HOME=... <sys.executable> install_source.py <action> <snapshot>`. Python is the dashboard's interpreter.

All three mutating endpoints depend on `_fixed_mount_request` and run through `_installation_action`.

### `BR/__init__.py` registration (lines 17-92)

- **Common to both modes.** It always registers the CLI commands. It registers the memory provider if the context has `register_memory_provider`. It registers `pre_message_delivery` only if `VALID_HOOKS` has it. It returns early if `<lifeos_home>/.claude/settings.json` is missing, so no tool or prompt hooks register in that case.
- **`patched_host = PATCHED_HOOKS <= VALID_HOOKS` (54).** `PATCHED_HOOKS` is `pre_prompt_admission, pre_command_approval, augment_tool_result, pre_turn_stop, on_turn_result`. `HookBridge` is created with `hold_turns=patched_host`.
- **Also registered in both modes:**
  - `subagent_start` and `subagent_stop`, if both exist;
  - `post_api_request`, if it exists;
  - `pre_tool_call` and `post_tool_call` (the `task_result` handler).
- **Reduced mode.** The prompt hook is `pre_llm_call`. It additionally registers `post_tool_call` (`post_tool_call` handler), `on_session_finalize` and `api_request_error`, then returns.
- **Patched mode.** The prompt hook is `pre_prompt_admission`. It also registers:
  - `pre_command_approval`
  - `augment_tool_result`
  - `pre_turn_stop` (with `on_limit: fail` when `stop_cap_policy == 'fail_closed'`)
  - `on_session_finalize`
  - `api_request_error`
  - `on_turn_result`
- **No hook enforcement.** I found no "required hooks" refusal in `__init__.py`. Partial hook sets silently fall to reduced mode, because the whole set must be present for patched mode.

## 8. Tests and qualification drivers

### Unit tests by area (in `tests/`)

| Area | Test files |
| --- | --- |
| Catalog and certificate | `test_release_catalog.py`, `test_release_stage.py` (also covers `DAILY-CANDIDATE`), `test_release_configuration.py` |
| Builder | no direct test of `scripts/build_managed_release.py`; only `DAILY-CANDIDATE` consumers are tested |
| Service files and fresh preview | `test_release_services.py`, `test_release_fresh.py` (also `NativeInitialization`) |
| `ProfileServices` | `test_profile_services.py` |
| Locks | `test_installation_lock.py`, `test_installation_lease.py`, `test_program_lock.py` |
| Install source and host patch | `test_hermes_install_source.py` (stage, apply, restore, recover), `test_lifeos_install_source.py`, `test_install_step.py`, `test_latest_hermes.py`, `test_hermes_patch_regeneration.py`, `test_patch_bundle.py`, `test_native_partial_patch.py` |
| Dashboard host-patch endpoints | `test_dashboard_api.py`, `test_memory_admin_dashboard.py`, `test_dashboard_ui.cjs` |
| Hook registration modes | `test_plugin_lifecycle.py`, `test_bridge.py`, `test_host_catalog_hooks.py` |
| Compatibility detector | `test_host_compatibility.py` (26), `test_host_compatibility_manifest.py` (8, needs `LIFEOS_STOCK_HERMES_ARCHIVE`) |
| Release version and CLI | `test_release_version.py`, `test_release_manager_cli.py`, `test_release_accounts.py` |
| Mount, drift, admin | `test_mount_transaction.py`, `test_native_version_drift.py`, `test_version_drift_baseline.py`, `test_memory_administration.py`, `test_memory_admin_install.py`, `test_selection_native_mount.py` |
| Update modules | `test_update_plan.py`, `test_update_hooks.py`, `test_update_dependencies.py`, `test_update_transaction.py`, `test_update_worker.py` |
| Release program / operation | `test_release_programs.py`, `test_release_operation.py`, `test_release_preparation.py`, `test_release_baseline.py`, `test_release_transaction.py` |
| Release UI | `test_release_ui.cjs`, `test_release_dashboard.py` |
| Removal | `test_removal_*.py`: `bootstrap`, `configuration`, `consumers`, `coordinator`, `data_barrier`, `execution_source`, `generation`, `inventory`, `ownership`, `preparation`, `publication`, `recovery`, `runtime`, `services`, `state`. Also `test_memory_removal_workflow.py`, `test_memory_removal_ui.cjs`, `test_stock_hermes.py` |
| Live remote gate | `scripts/run_live_remote_gate.py` runs `tests/test_live_*` with `--ssh` and/or `--docker`. It needs `LIFEOS_HERMES_SOURCE` and fails if any selected case skips. |

The 2026-10-17 compatibility record lists these results: 26 detector tests, 8 manifest tests, 9 CLI tests, 5 dashboard tests (1 skip), 12 UI tests.

### Qualification and disposable guests

All qualification drivers are per-release scripts under `docs/verification/`. None live in `scripts/`.

- **Disposable test guests.** The guests are Proxmox LXC containers on `192.168.8.101` (`pct create`/`pct clone` via SSH `root@192.168.8.101`).
  - **Base fixture.** `docs/verification/2026-10-05-disposable-install-base/create.py` runs the following. It records no credentials.
    - `pveam download` of the Ubuntu 24.04 template;
    - `pct create 100 --hostname lifeos-install-probe --unprivileged 1 --cores 2 --memory 4096 --swap 0 --rootfs local-zfs:24 --net0 ...dhcp --features nesting=1 --onboot 0`;
    - `pct start`.
  - **Clones.** Later guests are full clones of snapshotted containers. For example, `2026-10-13-release-ui-install/public-test-guest.json` shows CT 106 `lifeos-ui-test-public` (192.168.8.249) cloned from CT 104's snapshot `stock-ui-manager-final-clean`. The 0.7.2 `qualification-guest.json` shows CT 110 (192.168.8.222) cloned from CT 106's snapshot `stock-ui-manager-qualified-baseline`.
  - **Cleanup records.** Examples are `2026-10-14-release-0.5.0/release-test-cleanup.json` and `2026-10-13-release-ui-install/diagnostic-guest-cleanup.json`.
  - **Standing guests** (per the cleanup records): CT 100 `lifeos-install-probe`, CT 101 `lifeos-dev`, CT 102 `lifeos-daily`, CT 106 and VM 801.
- **Disposable accounts.** The 0.7.3 file `docs/verification/2026-10-16-release-0.7.3/qualification/account-boundary-operator.py.gz` (gzip) shows the pattern, run as root:
  - refuse if the account or home already exists;
  - `useradd --create-home --home-dir /var/tmp/... --shell /usr/sbin/nologin --user-group <name>`;
  - copy the Python runtime, a frozen test venv, a prepared Hermes tree and `bun` into the home with `cp -a --reflink=auto`, then `chown`;
  - `loginctl enable-linger`, then `systemctl start user@UID.service`, then wait for `/run/user/UID/bus`;
  - hash the test sources before and after, run the tests, export evidence, and delete the account.
- **Other drivers.** `2026-10-12-hermes-managed-release/bootstrap_managed_account.py` prepares a release against a loopback HTTP fake of the GitHub API (serving `/repos/0ut5ider/lifeos-hermes-plugin/releases/tags/<tag>` and the three assets) under a synthetic profile. `2026-10-15-memory-portability/bootstrap_guest.py` and `bootstrap_release_guest.py` use `useradd`/`loginctl`.
- **About `lifeos-plugin-install-probe` on 192.168.8.252.**
  - `docs/test-environment.md` (line 14) says CT 101 `lifeos-dev` has the same accounts and paths as `.212`: `lifeos-claude-ref` (UID 1005) and `lifeos-plugin-install-probe` (UID 1007) "with the Hermes environment". Its address is DHCP and can change.
  - Line 20 says the `.212` copy of that account and its browser-acceptance home were removed on 2026-10-06. That removal does not say anything about the CT 101 copy.
  - Account creation commands for `lifeos-plugin-install-probe` are not documented in any doc I read, and I did not confirm the account is live today.
  - Release verification uses the `lifeos-hermes` account on `.252` and `.253`. The compatibility record shows `.252` has `/home/lifeos-hermes/.hermes` as the profile and a managed runtime source under `.lifeos-releases/<id>/hermes`.
- **Compatibility evidence.** `docs/verification/2026-10-17-host-compatibility/` holds real-host results. `.252` and `.253` are both `modified_source` with three untracked release files plus `patched_without_record`. `.213` is `unsupported_version` (a `v0.21.4` canary, commit `f4795c92`).
- **Plan and status docs.** `docs/in-place-installation-plan.md` (accepted architecture, step 1 done, steps 2-6 pending) and `docs/installation-workflow.md` (the current 0.7.3 managed flow).

## Findings relevant to the redesign

1. **Authenticity.** No signature and no pinned key. The trust anchor is GitHub's API digests plus the certificate's hash binding.
2. **LifeOS acquisition depends on upstream HEAD.** `prepare_lifeos` calls `ls-remote HEAD` and refuses if it differs from `SUPPORTED_LIFEOS_COMMIT` (`install_source.py:147-151`). The in-place plan says to fetch the pinned commit directly.
3. **The existing host-patch worker assumes the managed layout.**
   - Launcher path: it requires gateway `ExecStart path=` equal to `<current>/.hermes/bin/hermes` (732-737) and runs `<current>/.hermes/bin/hermes config check`.
   - Consumers: only the gateway unit is stopped, and no dashboard, Pulse or CLI consumers are enumerated.
   - Update lock: there is no Hermes updater lock.
   - Durability: no `fsync` in `_write_patch_state` or `_write_patch_files`.
   - Hash coverage: the apply step checks hashes only for patch targets plus `git status --porcelain --untracked-files=all` being empty. A real install with ignored venv files passes, but any untracked file refuses.
4. **Reusable durability machinery.**
   - `release_programs.publish`, `fingerprint` and `ProgramTransaction` already provide fsync'd publication, the `prepared, applying, applied, restoring, restored` states and "refuses later edits" semantics. It only handles whole files and directories with `before-N`/`incoming-N` copies.
   - `profile_services.ProfileServices` and `removal_consumers` already enumerate consumers. The latter is the broader inspector (all units, processes, hooks).
5. **Removal is runtime-replacement shaped.** `removal_generation.selected` requires an applied `.lifeos-releases` job and launchers equal to `launcher_script(job/bin/*)`. Preparation downloads a stock runtime from `stock-hermes.tgz`. The in-place plan's "restore original files from the journal" needs a different path. The config, `.env`, settings-hook and native-program transformations in `removal_configuration`, `removal_inventory` and `update_hooks` can be reused.
6. **Cross-checks on the claim "creates systemd units".** `service_files` is only used for fresh installs. The in-place plan will need a decision on whether to create units when the user's Hermes already has its own.
