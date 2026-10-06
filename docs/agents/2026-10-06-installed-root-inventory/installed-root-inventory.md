# Installed root inventory

Date: 2026-10-06. Role: Explore subagent (read-only). Model: Sonnet 5.5. Question: which plugin and native code paths determine or assume the LifeOS installed root and user-data directory. The primary agent saved this report because the read-only agent could not write files.

I could not write `installed-root-inventory.md` or `raw-grep.txt`. My instructions here are read-only, so I did not create the docs directory or the files. This report is the full content. If you want the files, write this reply to `installed-root-inventory.md` and tell me to re-run the greps into `raw-grep.txt`.

One mistake to clean up: while filtering native-tree greps I accidentally redirected output to `/tmp/x`. It is a stray scratch file, harmless, and I did not delete it because that is also outside my permissions.

Paths: P = `/home/outsider/Projects/Hermes_agent/LifeOS_plugin/lifeos_hook_bridge`, N = `/home/outsider/.cache/lifeos-full-experience-20261006/mount-yaml/candidate-after/LifeOS/install`. Line numbers come from the greps above; the TOOLS, PULSE and skills counts are totals, not itemised.

## Summary

- **The plugin has two separate roots.** The hook bridge reads settings from `~/.claude`, while memory and the dashboard read an absolute `root` from `$HERMES_HOME/lifeos-memory.json`. Those can already differ per profile. The dashboard ignores that config and hard-codes `Path.home()/".claude"`.
- **User-data dir is derived, not configured.** It is always `root.parent/.config/LIFEOS/USER`, so a selected root must be named `.claude` and sit under a "home" directory.
- **Native code has no usable root variable.** Hooks and most TOOLS and PULSE code resolve the root from `homedir()`, which Bun resolves from `$HOME`. Only `LIFEOS_DIR` and `CLAUDE_CONFIG_DIR` are partly honored, and unevenly.
- **Practical selection mechanism today.** `HOME=<selected root>.parent` plus a root directory named `.claude` makes most native code follow. This is what the bridge does for memory subprocesses and for installs. It does not do it for hook subprocesses.

## 1. Plugin (`lifeos_hook_bridge/`)

### Installed root

| file:line | Expression | Use | Override today |
|---|---|---|---|
| P/`__init__.py`:25 | `Path(os.environ.get("LIFEOS_HOOK_SETTINGS", str(Path.home()/".claude/settings.json"))).expanduser()` | Selects the settings.json that drives the hook bridge | Env `LIFEOS_HOOK_SETTINGS` (not `HOME`-independent) |
| P/`__init__.py`:~55 | `HookBridge(settings, settings.parent, ...)` | `bridge.root` is set to the settings file's parent | Follows `LIFEOS_HOOK_SETTINGS` |
| P/`bridge.py`:607-613 | `self.root = Path(root)` | Root for state dirs and `LIFEOS_DIR` default | Constructor argument |
| P/`bridge.py`:626-630 | `root/"LIFEOS/MEMORY/STATE/hermes-task-counts"`, `.../hermes-transcripts` (created at init) | Bridge state | Follows `root` |
| P/`bridge.py`:187 | Literal `"$HOME/.claude/hooks/VersionDrift.hook.ts"` / `"${HOME}/..."` | Recognises the native VersionDrift hook | No. Also falls back to `root/hooks/...` |
| P/`bridge.py`:202 | `Path(path).parts[-3:] == (".claude","hooks","CheckpointPerISC.hook.ts")` | Recognises the native checkpoint hook | No, requires a directory named `.claude` |
| P/`bridge.py`:1272-1273 | `LIFEOS_VERSION_DRIFT_ROOT=str(self.root)`, baseline `default_baseline_path()` | VersionDrift environment | Baseline via `setdefault`, so env wins |
| P/`version_drift.py`:37 | `Path.home()/".local/state/lifeos-hook-bridge/version-drift-baseline.json"` | Drift baseline, one per user, not per root | No |
| P/`carrier_probe.py`:62 | `Path.home()/".claude/LIFEOS/MEMORY/STATE"/STATE_NAME` | Carrier probe state | No. Hard-coded |
| P/`file_permissions.py`:54 | `anchor = str(Path.home())` | Resolves `~/` permission rules | Follows `HOME` |
| P/`bridge.py`:579, 586, 590 | `Path.home()` | Project-root detection and `.claude/settings.json` search | `HOME` |
| P/`bridge.py`:850-851, 875-876, 924, 972-973, 1057-1058, 1079-1080, 1141, 1504-1505 | `project_dir/".claude"/...` | Per-project settings and skills, not the installed root | No |
| P/`bridge.py`:961 | `Path.home()/".config/lifeos-hook-bridge/remote-projects.json"` | Remote trust file | Env `LIFEOS_REMOTE_PROJECT_TRUST` |
| P/`bin/claude`:5 | `${LIFEOS_HOOK_MODEL_ENV:-$HOME/.config/lifeos-hook-bridge/model.env}` | Model env | Env var |
| P/`bin/claude`:49 | `exec "$HOME/.local/bin/claude"` | Real claude | `HOME` |
| P/`bin/claude_direct.py`:26-27 | `HERMES_HOME` (default `~/.hermes`), `LIFEOS_MEMORY_CONFIGURATION` (default `home/lifeos-memory.json`) | Finds the memory config, hence `root` | Both env vars |
| P/`bin/git`:21-22 | `LIFEOS_VERSION_DRIFT_ROOT`, `_BASELINE`, `_SYSTEM_GIT` | Git shim for VersionDrift | Env vars |
| P/`bin/hook_runner.py`:29 | `env=request.get("environment")` | Runs hooks with the passed environment | Argument |

### Memory root from profile config

| file:line | Expression | Use | Override today |
|---|---|---|---|
| P/`memory_service.py`:93, 108 | `MemoryConfiguration(path)`; `root` must be an absolute string | Config class, validation | Profile file `lifeos-memory.json` holds `root` |
| P/`memory_provider.py`:18 | `get_hermes_home()/'lifeos-memory.json'` | Config location | Profile (`get_hermes_home`) |
| P/`memory_provider.py`:42 | `Path(config['root'])/'LIFEOS/TOOLS/lib/MemoryAccess.ts'` | Capability check | Config |
| P/`cli.py`:51; P/`bridge.py`:1107 | `MemoryConfiguration(get_hermes_home()/'lifeos-memory.json')` | Per-profile config | Profile |
| P/`memory_runtime.py`:142, 193, 238, 353 | `NativeMemory(Path(configuration['root']))` | Native memory root | Config |
| P/`memory_runtime.py`:275-276 | `LIFEOS_MEMORY_CONFIGURATION=self.key`, `HERMES_HOME=configuration.path.parent` | Binds hook and child env to the profile | Set per call |
| P/`memory_service.py`:190, 232, 610; P/`cli.py`:74 | `NativeMemory(Path(configuration["root"]))` | Same | Config |
| P/`memory_administration.py`:88, 93, 118, 155, 185 | `root = Path(config['root']).absolute()`; authorization binds `root` | Mount and recovery authorization | Config. A root change invalidates grants |
| P/`memory_preferences.py`:93, 274, 298 | `Path(config['root']).absolute() != self.root` | Rejects a config whose root differs from the dashboard's | Hard-fail on mismatch |
| P/`fresh_store.py`:93, 103, 113, 207 | `selected['root']` | Store selection | Config |
| P/`fresh_store.py`:230-232 | `installed=home/'.claude'`; `user=home/'.config/LIFEOS/USER'` | Fresh-store staging | No |
| P/`memory_adoption.py`:171 | `str(memory.root)` in signature | Binds adoption to root | Follows `memory.root` |
| P/`mount_transaction.py`:385; P/`memory_ownership.py`:23, 47, 145; P/`ownership_setup.py`:34; P/`memory_import.py`:73 | `profile/'lifeos-memory.json'` | Config in profile | Profile |

### Dashboard (`dashboard/plugin_api.py`)

| file:line | Expression | Use | Override today |
|---|---|---|---|
| 52 | `INSTALLED_ROOT = Path.home() / ".claude"` | **Module-level global root** | None. Ignores the profile's `root`, `HOME` only |
| 53 | `HERMES_HOME = Path(os.environ.get("HERMES_HOME", str(Path.home()/".hermes")))` | Profile | Env |
| 55-58 | `INSTALL_CANDIDATE`, `HERMES_CANDIDATE`, `HOST_PATCH_ROOT`, `LIFEOS_UPDATE_ROOT` under `~/.local/share/lifeos-bridge/` and `~/.local/state/lifeos-hook-bridge/` | Install and update staging | No |
| 115 | `MemoryPreferences(HERMES_HOME/'lifeos-memory.json', INSTALLED_ROOT, ...)` | Passes global root | No |
| 146, 167-178, 432-435, 493-534, 545-568, 654-679, 743-753, 807, 871-889 | Uses of `INSTALLED_ROOT` (version, settings.json, install, update, baseline, mount) | All dashboard actions | No |
| 331 | `systemd-run --user ... --setenv=HOME={Path.home()}` | Fresh-store worker | `HOME` |
| 638 | `--setenv=HOME={INSTALLED_ROOT.parent}`, `HERMES_HOME`, `PULSE_URL` passthrough | Update worker | No |
| 608, 620, 788 | `systemctl --user is-active hermes-gateway.service` | Gateway check | Fixed unit name |
| `dist/index.js`:708, 806 | UI text only ("A .claude directory already exists", "create ~/.claude") | Messages | n/a |

### User-data path (`root.parent/'.config/LIFEOS/USER'`)

All derived from `root`, none configurable:

- P/`memory_access.py`:69, 168, 464
- P/`memory_diagnostics.py`:261
- P/`memory_pulse.py`:21
- P/`memory_pulse_adapters.py`:31, 120
- P/`memory_staging.py`:29
- P/`memory_sources.py`:149
- P/`memory_canonical.py`:21
- P/`memory_restore.py`:26, 38, 103
- P/`memory_knowledge.py`:29
- P/`memory_state.py`:21, 33
- P/`profile_backup.py`:180, 285
- P/`profile_backup_recovery.py`:21, 62, 84, 104
- P/`memory_telos.py`:22, 33, 43
- P/`memory_freshness_migration.py`:46
- P/`memory_freshness.py`:57
- P/`memory_freshness_cache.py`:21
- P/`memory_evidence.py`:38, 54
- P/`memory_distill.py`:23, 83, 101, 148
- P/`memory_seed.py`:40 (`config_dir == root.parent/'.config/LIFEOS'`)
- P/`memory_deny_hashes.py`:23, 43
- P/`memory_wiki.py`:133
- P/`memory_wisdom.py`:31, 123, 155
- P/`memory_backup.py`:59, 147
- P/`memory_backup_recovery.py`:42, 56, 68-71, 97
- P/`memory_graph.py`:37, 87
- P/`memory_interview.py`:22
- P/`memory_import.py`:210 (`self.installed.parent/...`)
- P/`memory_derived_sync.py`:24, 43
- P/`memory_learning.py`:30, 70
- P/`memory_context_audit.py`:23
- P/`memory_recurrence.py`:20
- P/`memory_publication.ts`:21 (`realpathSync(resolve(root,"../.config/LIFEOS/USER"))`)

Related layout assumptions:

- P/`memory_backup_recovery.py`:68-71 builds `stage/.claude` with `LIFEOS/USER` and `LIFEOS/MEMORY` symlinks into `../../.config/LIFEOS/USER`.
- P/`profile_backup_recovery.py`:84, 140 rebinds `root` to `native/.claude`.
- The install layout assumes `LIFEOS/USER` and `LIFEOS/MEMORY` inside the root are symlinks to the user dir.

### Install and update

| file:line | Expression | Use |
|---|---|---|
| P/`install_source.py`:258-259 | `installed.name != ".claude"` raises "must be a .claude directory" | **Hard requirement that the root be named `.claude`** |
| P/`install_source.py`:267-271 | `config_dir=installed.parent/'.config/LIFEOS'`; env `HOME=installed.parent`, `CLAUDE_CONFIG_DIR=installed`, `LIFEOS_DIR=installed/'LIFEOS'`, `LIFEOS_CONFIG_DIR=config_dir`, `PROJECTS_DIR=installed.parent/'Projects'` | Environment for native installer steps |
| P/`install_source.py`:300-310, 348-350 | Checks `settings.json` and `LIFEOS/HERMES/Mount.ts` under `installed` | Validation |
| P/`install_source.py`:62 | `cwd or Path.home()` for git | Incidental |
| P/`install_source.py`:659 | `HERMES_HOME=Path(manifest["config"]).parent` | Mount env |
| P/`update_worker.py`:206-220 | Sets `os.environ["HOME"]=reference_home` and installs to `reference_home/".claude"` | Reference install |
| P/`update_worker.py`:152; P/`update_transaction.py`:219, 242 | `installed/"settings.json"` | Settings read |
| P/`memory_hypotheses.py`:65 | `memory.root/'settings.json'` | Settings read |
| P/`version_drift.py`:16-24 | Path lists (`hooks/`, `settings.json`, `LIFEOS/PULSE/state/`, ...) | Relative to root |

### Mount

| file:line | Expression | Use |
|---|---|---|
| P/`memory_administration.py`:174-191 | `mount_environment`: `HOME=str(installed.parent)`, `HERMES_HOME=str(profile)` | **Passes a HOME override to Mount.ts** |
| P/`mount_transaction.py`:327-333 | `native=self.installed/'LIFEOS/HERMES/Mount.ts'`; `environment` limited to `HOME` and `HERMES_HOME` from `checked` | Mount run |
| P/`mount_transaction.py`:335 | `HERMES_WORKSPACE` default `installed.parent/'HermesWorkspace'` | Workspace |

## 2. Native source tree

### Resolver functions

**`getClaudeDir()` and `getLifeosDir()`** are in `N/hooks/lib/paths.ts` (the only hooks paths file; the other `paths.ts` is `N/LIFEOS/PULSE/Conduit/paths.ts`).

- **`getClaudeDir()`** (lines 65-73) honors only `CLAUDE_PLUGIN_ROOT`, else `homedir()/.claude`. It does not honor `CLAUDE_CONFIG_DIR`.
- **`getLifeosDir()`** (lines 43-55) honors `CLAUDE_PLUGIN_ROOT`, then `LIFEOS_DIR` (expanded), else `homedir()/.claude/LIFEOS`.
- **`expandPath()`** (lines 18-26) expands `$HOME`, `${HOME}` and `~` through `homedir()`.
- **`getSettingsPath`, `getEnvPath`, `getHooksDir`, `getSkillsDir`** all build on `getClaudeDir()`.

Other resolvers:

- **Conduit** (`N/LIFEOS/PULSE/Conduit/paths.ts`:13) uses `CLAUDE_ROOT = process.env.CLAUDE_CONFIG_DIR || join(homedir(), ".claude")`. This is the only central `CLAUDE_CONFIG_DIR` consumer.
- **LifeosConfig** (`N/LIFEOS/TOOLS/LifeosConfig.ts`:93-94, 142, 205, 208) uses `DEFAULT_HOME = process.env.HOME || homedir()` and `resolve(DEFAULT_HOME, ".claude/LIFEOS/USER/CONFIG/LIFEOS_CONFIG.toml")`. User dir defaults to `.claude/LIFEOS/USER` unless `paths.userDir` is set in that TOML; `paths.projectsDir` is likewise configurable.
- **Settings env** (`N/settings.system.json`:5-9) sets `LIFEOS_DIR=$HOME/.claude/LIFEOS` and `LIFEOS_CONFIG_DIR=$HOME/.config/LIFEOS`. The bridge expands `$HOME` using `Path.home()` (P/`bridge.py`:834).
- **`CLAUDE_CONFIG_DIR`** is honored in `N/LIFEOS/TOOLS/Doctor.ts`:46, `N/LIFEOS/PULSE/modules/atlas.ts`:21 and `threatmodel.ts`:22, plus the skills install tools (`N/skills/LifeOS/Tools/*`, which take `--config-root`).
- **`LIFEOS_ROOT`** (a different variable, with a `~/.claude` default) is honored only in `N/LIFEOS/HERMES/Heartbeat/Tick.ts`:26 and `ArtistScan.ts`:26.
- **`LIFEOS_CONFIG_DIR`** is mostly set by installers and in settings; few runtime readers.

### Hooks (`N/hooks`)

**Honor `LIFEOS_DIR` (with a `~/.claude/LIFEOS` fallback):**

- `DriftReminder.hook.ts`:73
- `FormatGate.hook.ts`:49
- `ISACloseGate.hook.ts`:39
- `ISAFoldGate.hook.ts`:40
- `LastResponseCache.hook.ts`:47
- `VerificationGate.hook.ts`:60
- `SessionCleanup.hook.ts`:58
- `WritingGate.hook.ts`:49
- `WorkCompletionLearning.hook.ts`:74
- `SatisfactionCapture.hook.ts`:80
- `PromptProcessing.hook.ts`:85
- `lib/work-config.ts`:49

**Use `getLifeosDir()` or `getClaudeDir()`** (so they inherit `LIFEOS_DIR`, but `getClaudeDir()` stays `~/.claude`):

- `KnowledgeWriteGuard`
- `KittyEnvPersist`
- `LoadContext` (lines 44, 198, 472)
- `handlers/DocCrossRefIntegrity`, `MemoryDirIntegrity`, `KnowledgeConformance`
- `handlers/RebuildArchSummary`, `UpdateCounts` (line 115)
- `lib/change-detection.ts`

**Hard-coded `homedir()/.claude`, ignoring all env vars (only `HOME` moves it):**

- `AgentInvocation.hook.ts`:92 (agents dir)
- `DeployRegistrationGate.hook.ts`:34-36
- `MemoryReviewFire.hook.ts`:47
- `PublicPushGate.hook.ts`:31-32
- `SystemFileGuard.hook.ts`:30
- `lib/system-file-guard-core.ts`:20
- `BashSystemWriteGuard.hook.ts`:33
- `EgressClassGuard.hook.ts`:27
- `AlgorithmNudge.hook.ts`:71, 459
- `ConfigEvalFire.hook.ts`:25
- `MemoryHealthGate.hook.ts`:22
- `HookHealer.hook.ts`:40
- `ISARenderOnStop.hook.ts`:26-27, 112
- `PromptProcessing.hook.ts`:862
- `ISASync.hook.ts`:158, 186, 203
- `ReminderRouter.hook.ts`:31
- `SystemChangeSurface.hook.ts`:57
- `Safety.hook.ts`:57-63
- `TimeContext.hook.ts`:24
- `ModelRungGuard.hook.ts`:44
- `MemoryTurnStart.hook.ts`:49
- `ISAStaleWriteGuard.hook.ts`:60
- `VersionDrift.hook.ts`:25
- `MemoryDeltaSurface.hook.ts`:40
- `LoadMemory.hook.ts`:30
- `WritingGate.hook.ts`:130 (`.env`)
- `CheckpointPerISC.hook.ts`:34, 212, 306, 308
- `lib/identity.ts`:29, 39
- `lib/notifications.ts`:13
- `lib/safety-classifier.ts`:35
- `handlers/UpdateCounts.ts`:43
- `lib/paths.ts`:54, 72 (the fallbacks)

`AtlasEventCapture.hook.ts`:20 uses `~/.local/state/lifeos/atlas` (unrelated to the root).

### TOOLS (`N/LIFEOS/TOOLS`)

- About 436 matching lines across about 160 files; roughly 132 files have no env check on the same line. Roughly 30 files honor `LIFEOS_DIR` (for example AskFidelity, ApproveCurrentStateEntries, ArchDecisionHarvest, CommitmentSweep, ComputeGap, MigrateScan, CreateUpdate, WorkSweep, UsageAggregator, StateEvidence). Doctor honors `CLAUDE_CONFIG_DIR`.
- Hard-coded examples: `CostTracker.ts`:38, `CrossVendorAudit.ts`:26, `IntegrityMaintenance.ts`:113 (`homedir()+'/.claude/LIFEOS'`).
- `GeminiSearch.ts`:66 and `GrokQuery.ts`:65 state that the canonical `.env` is `~/.claude/.env`, never `$LIFEOS_CONFIG_DIR/.env`.
- **`TOOLS/lib/MemoryAccess.ts`**:19, 35, 95, 178 is the native memory-access bridge. It hard-codes `resolve(homedir(), ".claude/LIFEOS/USER/CONFIG", ...)`, including `memory-access.json`, and compares the root with `realpath(homedir()/.claude)`. This reads the connector from the real `HOME`, not from the selected root.

### PULSE (`N/LIFEOS/PULSE`)

- About 223 matching lines; about 86 files have hard-coded paths with no env check. Honoring files include `Conduit/paths.ts`, `modules/atlas.ts`, `modules/threatmodel.ts`, `modules/work.ts`:45, `modules/content.ts`:163 and `Observability/observability.ts`:2409.
- Hard-coded `join(HOME, ".claude", "LIFEOS")`: `pulse.ts`:24, `setup.ts`:23, `Observability/observability.ts`:78, `Performance/module.ts`:18, `modules/wiki.ts`:42. `pulse.ts`:22 takes `HOME` from `process.env.HOME ?? ...`.
- `pulse.ts`:29 loads `HOME/.claude/.env`.
- **Service definitions.** `com.lifeos.pulse.service` (macOS equivalent `com.lifeos.pulse.plist`):
  - `WorkingDirectory=__HOME__/.claude/LIFEOS/PULSE`
  - `ExecStart=__BUN_PATH__ run pulse.ts`
  - `Environment=HOME=__HOME__`
  - logs under `__HOME__/.claude/LIFEOS/PULSE/logs`
- `manage.sh`:5 hard-codes `PULSE_DIR="$HOME/.claude/LIFEOS/PULSE"`; it installs to `$HOME/.config/systemd/user/com.lifeos.pulse.service` using `sed s|__HOME__|$HOME|`.
- `com.lifeos.deriver.plist` hard-codes `__HOME__/.claude/LIFEOS/TOOLS/LearningPatternSynthesis.ts`.
- `start-pulse.sh`:10 uses `${HOME}/.bun/bin/bun`.

### ATLAS (`N/LIFEOS/ATLAS`)

- `collectors/InfraInventory.ts`:12, `Gear.ts`:10, `Cloudflare.ts`:16, `Projects.ts`:11, `Secrets.ts`:32-34.
- `InstallAtlas.ts`:37-43: the template paths are hard-coded `HOME/.claude/LIFEOS/ATLAS`.
- `Store.ts`:19 honors `ATLAS_DIR`.

### HERMES

- **`Mount.ts`**:38-43:
  - `HOME = homedir()`.
  - `HERMES_HOME = process.env.HERMES_HOME || join(HOME, ".hermes")`.
  - `MOUNT_DESTINATION = process.env.LIFEOS_MOUNT_DESTINATION ?? HERMES_HOME`.
  - `WORKSPACE = process.env.HERMES_WORKSPACE || join(HOME, "HermesWorkspace")`.
  - It has no `CLAUDE_CONFIG_DIR` or `LIFEOS_DIR` reads.
- **Install root in `Mount.ts`:** it comes from `RenderSoul.ts` via `INSTALL_ROOT`.
  - **`RenderSoul.ts`**:37-38: `INSTALL_ROOT = join(LIFEOS_ROOT, "..")`, derived from the script's own file location, so it is self-locating. `HOME = homedir()` at line 34 is used only to scrub paths (lines 150, 193); the "absolute home path survived scrubbing" check can fail if the root is outside `HOME`.
- **`memoryAccess()`** (from `TOOLS/lib/MemoryAccess.ts`, imported at Mount.ts:35) reads the hard-coded `~/.claude` as above.
- `Heartbeat/Tick.ts`:26 and `ArtistScan.ts`:26 honor `LIFEOS_ROOT`.
- `Health.ts`:78 and `LogAnalysis.ts`:25 honor `HERMES_HOME`.
- `Policy.ts`:68-69, 125, 146: deny globs `**/.claude/settings.json` and `*.claude/settings*`. These depend on the root being named `.claude`.
- `plugin/test_guard.py` uses `~/.claude` in fixtures.

### Skills (`N/skills`)

- About 137 matching lines; 50 files without env checks.
- The `skills/LifeOS/Tools/*` install tools honor `--config-root`/`--config-dir` arguments plus `CLAUDE_CONFIG_DIR`/`LIFEOS_DIR` (InstallEngine, InstallSettings, InstallHooks, DeployCore, DeployComponents, SeedPulse, ScaffoldUser, LinkUser, OverlaySystem, ActivateImports).
- Also honoring: `Cortex/Tools/ContextSearch.ts`, `Daemon/Tools/DaemonAggregator.ts`, `Art/Tools/Generate.ts`.
- Hard-coded: the rest of `skills/**/Tools` (Art, Interceptor, LocalIntelligence, Evals, Webdesign, Apify examples and others).
- `skills/Telos/DashboardTemplate` also has hits.

## 3. How the bridge builds hook environments

- **Base environment.** P/`bridge.py`:619: `self.base_environment = dict(os.environ)`. It carries the Hermes process's `HOME`, not the root's parent, and sets no `CLAUDE_CONFIG_DIR`.
- **`_apply_settings`.** P/`bridge.py`:829-839:

```python
environment = dict(self.base_environment)
for key, value in settings.get("env", {}).items():
    if isinstance(value, str):
        environment[key] = value.replace("${HOME}", str(Path.home())).replace("$HOME", str(Path.home()))
environment.setdefault("LIFEOS_DIR", str(self.root / "LIFEOS"))
environment["PATH"] = (f"{Path(__file__).parent / 'bin'}:{Path.home() / '.bun/bin'}:"
                       f"{Path.home() / '.local/bin'}:{environment.get('PATH', '')}")
```

- **Consequences.** Settings `env` (for example `LIFEOS_DIR=$HOME/.claude/LIFEOS`) is expanded with the Hermes process's `Path.home()`, not with `root.parent`. `LIFEOS_DIR` falls back to `root/LIFEOS` only if settings does not define it. `LIFEOS_CONFIG_DIR` comes from settings. `HOME` and `CLAUDE_CONFIG_DIR` are never overridden for hooks.
- **Per-event environment** (P/`bridge.py`:1070-1090). Project `.claude/settings*.json` env is expanded with `Path.home()` (line 1083). Then `LIFEOS_NOTIFICATION_CHANNEL`, memory binding via `MemoryRuntime(...).bind_environment` (line 1107), and `LIFEOS_VERSION_DRIFT_*` (lines 1272-1280) are added.
- **Commands run as written in settings.** Hook commands in settings reference `$HOME/.claude/hooks/...` and are executed with the unmodified `HOME`. Selecting another root therefore means rewriting the commands or moving `HOME` for hooks.
- **Subprocess environments that do override `HOME`:**
  - P/`memory_access.py`:140-143 sets `HOME=root.parent`, `LIFEOS_DIR=root/LIFEOS`, `LIFEOS_CONFIG_DIR=root/LIFEOS/USER/CONFIG` for the native memory worker. Note this `LIFEOS_CONFIG_DIR` differs from the installer's `root.parent/.config/LIFEOS`.
  - P/`memory_administration.py`:176-178 sets `HOME=installed.parent`, `HERMES_HOME=profile` for mount.
  - P/`install_source.py`:268-270 sets `HOME`, `CLAUDE_CONFIG_DIR`, `LIFEOS_DIR`, `LIFEOS_CONFIG_DIR`, `PROJECTS_DIR`.
  - P/`dashboard/plugin_api.py`:638 sets `systemd-run --setenv=HOME={INSTALLED_ROOT.parent}`.

## 4. Pulse service

- **Plugin side.** P/`profile_services.py`:20-21 hard-codes `UNITS = {'gateway': 'hermes-gateway.service', 'dashboard': 'hermes-dashboard.service', 'pulse': 'com.lifeos.pulse.service'}`. The unit names cannot vary per root; a custom `units` mapping must still have three distinct `*.service` names.
- **Expected working directories** (P/`profile_services.py`:83-84, 158-161):
  - `self.directories = {'gateway': self.profile, 'dashboard': self.installed.parent.resolve(), 'pulse': self.physical_root / 'LIFEOS/PULSE'}`.
  - The plugin reads `systemctl --user show` properties (`WorkingDirectory`, `FragmentPath`, `ExecStart`, ...). It compares `WorkingDirectory` to `directories[role]`, so the Pulse unit must run from the selected root's `LIFEOS/PULSE`.
  - It stops and starts the units but does not create or rewrite them.
- **Instantiation.** `ProfileServices(profile, installed, ...)` is built in P/`ownership_setup.py`:40, 60.
- **Unit definition is native-owned.** `N/LIFEOS/PULSE/manage.sh` renders `com.lifeos.pulse.service` from the template into `~/.config/systemd/user/`, substituting `__HOME__` and `__BUN_PATH__`. So Pulse's `WorkingDirectory`, log paths and `Environment=HOME` are fixed at `$HOME/.claude/LIFEOS/PULSE`. There is one unit name per user, not per profile or root.
- **No plugin code starts Pulse.** `manage.sh` and `start-pulse.sh` are not referenced in the plugin.
- **Plugin interaction with Pulse is HTTP.** P/`memory_http.py`:38-52 requires a loopback dashboard URL and port. `PULSE_URL` is passed through at P/`dashboard/plugin_api.py`:640. P/`memory_pulse.py` and `memory_pulse_adapters.py` read snapshots through `memory._native('pulse_snapshot')` and `root.parent/'.config/LIFEOS/USER'` paths. P/`version_drift.py`:24 treats `LIFEOS/PULSE/state/` as runtime.

## Readers that would ignore a selected root today

1. **`dashboard/plugin_api.py`:52 `INSTALLED_ROOT`.** It ignores the profile's `root` and drives install, update, mount, baseline and version checks, plus the `HOME` given to workers (638). It must read `lifeos-memory.json` or the new setting file. It also cross-checks against `memory_preferences.py`:93.
2. **`__init__.py`:25.** The settings path is `LIFEOS_HOOK_SETTINGS` or `~/.claude/settings.json`; the root is derived from it. The profile setting must feed this.
3. **`install_source.py`:258.** A root not named `.claude` is rejected, and `root.parent` is assumed to be "home".
4. **`root.parent/'.config/LIFEOS/USER'` throughout** (30+ memory modules, `memory_publication.ts`:21). The user dir is bound to `root.parent`. Different roots under the same parent would collide.
5. **`bridge.py` hook environment** (829-839, 1083). `HOME` is not set to `root.parent` and `$HOME` is expanded with `Path.home()`. Native hooks with hard-coded `homedir()/.claude` (about 40 listed above) read the wrong root, including Safety, SystemFileGuard, BashSystemWriteGuard, MemoryTurnStart and LoadMemory. `LIFEOS_DIR` follows only because `setdefault`/settings supply it.
6. **`bridge.py`:187, 202.** Recognition of VersionDrift and CheckpointPerISC by the literal `.claude/hooks/...` string and path parts. A differently named root defeats both.
7. **`carrier_probe.py`:62.** Hard-coded `~/.claude/LIFEOS/MEMORY/STATE`.
8. **`version_drift.py`:37.** The baseline is per user, not per root.
9. **`fresh_store.py`:230-232 and `update_worker.py`:206-220.** They force `home/'.claude'`.
10. **`N/hooks/lib/paths.ts` `getClaudeDir()`.** It ignores `CLAUDE_CONFIG_DIR` and `LIFEOS_DIR`; only `CLAUDE_PLUGIN_ROOT` or `HOME` moves it. `getLifeosDir()` and `getClaudeDir()` can disagree if only `LIFEOS_DIR` is set.
11. **`N/LIFEOS/TOOLS/lib/MemoryAccess.ts`:19, 35, 95, 178.** The native memory connector (`memory-access.json`) is always `homedir()/.claude/LIFEOS/USER/CONFIG`, so Mount and memory tools read the real-home connector. With `HOME` overridden (as `memory_access.py`:141 does) it follows `HOME`.
12. **`N/LIFEOS/HERMES/Mount.ts` and `RenderSoul.ts`.** `HOME = homedir()` is used for scrubbing; Mount's workspace defaults to `$HOME/HermesWorkspace`. The scrub check can throw if the selected root is outside `HOME`.
13. **Native Pulse.** `pulse.ts`, `setup.ts`, `manage.sh`, the unit and plist templates, the deriver plist, `start-pulse.sh`, and Conduit (honors `CLAUDE_CONFIG_DIR` only). The unit name and `WorkingDirectory` are fixed at `$HOME/.claude/LIFEOS/PULSE`, and `profile_services.py` checks that working directory. A different root needs its own unit and a changed `UNITS` binding.
14. **`N/LIFEOS/TOOLS/LifeosConfig.ts`:94, 142, 205.** The `LIFEOS_CONFIG.toml` and user dir are `HOME`-based. Only the TOML `paths.userDir` can move the user dir.
15. **About 130 TOOLS files, about 85 PULSE files and 50 skills files** with hard-coded `~/.claude`. These follow `HOME` only.
16. **`HookHealer`, `Safety` (`safety-classifier.ts`:35), `SystemFileGuard`, `BashSystemWriteGuard`.** They treat only `HOME/.claude` as the protected system root, so a selected root would be unprotected.
