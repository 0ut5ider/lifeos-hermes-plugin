# Raw notes: PR #3 runtime review (2026-10-05)

All code was read with `git show 71987ce:<path>` and `git diff origin/main...71987ce -- <path>`.
The working tree was not read or modified.

## Commands run and output

### 1. Changed files (runtime and patches)

`git diff origin/main...71987ce --stat -- lifeos_hook_bridge patches`:
70 files, 20950 insertions, 1530 deletions. Largest: lifeos-memory-access.patch (6091 lines, two
identical copies), memory_import.py (501), memory_native.ts (380), memory_pulse_adapters.py (332),
profile_services.py (306).

### 2. os.chmod(follow_symlinks=False) on Linux (relevant to fresh_store.py:207-209)

```
3.14.7 regular ok
symlink NotImplementedError chmod: follow_symlinks unavailable on this platform
3.11.16 regular ok
symlink NotImplementedError chmod: follow_symlinks unavailable on this platform
```
Conclusion: regular files work. fresh_store only reaches the loop after `_files(user)` rejected
non-regular entries, so no symlink can reach it. Not a defect.

### 3. Hermes host patches apply cleanly to the supported Hermes commit

Exported 758ad514eb0e800547e015edf05aa18f78b78d82 from
/home/outsider/Projects/Hermes_agent/upstream/final-gate-baseline with `git archive` into
/tmp/pr3-hermes-eUDh, then applied the 71987ce copies of HERMES_PATCHES in install order:
```
OK hermes-plugin-events
OK hermes-turn-gates
OK hermes-command-policy
OK hermes-session-lifecycle
OK hermes-child-routing
OK hermes-strict-inference
OK hermes-remote-files
OK hermes-cron-bootstrap
OK hermes-required-middleware
```
`patches/*.patch` and `lifeos_hook_bridge/patches/*.patch` are byte-identical for
hermes-required-middleware, lifeos-memory-access, hermes-plugin-events (diff exit 0).

In the patched tree, `hermes_cli/plugins_dispatch.py:621 invoke_middleware` re-raises for
callbacks marked `_hermes_required_middleware`, so a required `llm_admission` failure does stop
dispatch. `register_middleware(..., required=True)` refuses async callbacks.

### 4. Hermes default install layout (relevant to profile_backup.py)

`upstream/final-gate-baseline/scripts/install.sh:79`:
`INSTALL_DIR="${INSTALL_DIR:-$HERMES_HOME/hermes-agent}"`
The checkout lives inside HERMES_HOME by default. `du -sh` of a local Hermes worktree
(final-gate-baseline, no .git objects): 375M, `find -type f | wc -l`: 24842.
memory_backup.TOTAL_LIMIT = 256 MiB, ENTRY_LIMIT = 100000.
PM builds environments under `<project>/venv` or `<generation>/venv` (pm/operations.py:152,210,240).

Local machine ~/.hermes has no hermes-agent checkout (installed differently), so the failure is
not reproduced here; it applies to the default installer layout.

### 5. Hermes profile listing

hermes_cli/profiles.py:406 filters profile dirs with `_PROFILE_ID_RE` and an identity check, so a
`~/.hermes/profiles/.local` directory created by fresh_store/_base or prepare_import would not be
listed as a profile. It would still sit inside the Hermes root.

## Per-file notes

### installation_lock.py
- Lease checks owner pid+thread, dev/ino of lock file and profile, private modes. Looks correct.
- Lease path has no try/finally around `yield`; post-check is skipped on exception. Harmless.
- No defect found.

### fresh_store.py
- status() probes the lock by acquiring it non-blocking (lines 142-146). A concurrent
  dashboard `_installation_action` (non-wait) can get a spurious 409 during the probe.
  The update worker uses wait=True, so it only waits.
- `busy` is global, so every unfinished store shows "preparing" while any unrelated
  installation op runs; old crashed stores show "interrupted" otherwise.
- prepare() holds installation_lock and MemoryConfiguration._lock() for the full install
  (6 Bun steps x 300 s timeout + bun install). configuration._lock() is a blocking flock used
  by MemoryConfiguration.update(), which MemorySharing.revoke/enroll and sharing() use.
- No cleanup of failed preparations; no count cap; each store is a full LifeOS install.
- _base() uses profile.parent; for HERMES_HOME=~/.hermes/profiles/<n> output lands in
  ~/.hermes/profiles/.local/state/...
- Identity rendering replaces every "LifeOS" and every word "User" in DA_IDENTITY.md /
  PRINCIPAL_IDENTITY.md. Template not available locally to confirm impact.
- _config_names: tested mentally against display_name/full_name/names prefixes; anchoring is
  correct. Multiline values fail closed (tomllib error -> 409).
- Response returns absolute paths and full file inventory to the authenticated owner.

### install_source.py
- HOME/CLAUDE_CONFIG_DIR/LIFEOS_* now point at installed.parent; isolates fresh installs.
- _install_step kills the process group on timeout/interrupt. `process.communicate()` after
  SIGKILL can still block if a daemonized grandchild (setsid) holds the pipes. Low.
- On failure only `installed` moves to `failed`; the scaffolded `installed.parent/.config/LIFEOS`
  stays. For fresh stores that is inside the destination. For the main install it is the real
  ~/.config/LIFEOS (pre-existing behavior, not new).

### native_dependencies.py
- Wrapper intercepts only when argv[0] after `--` is exactly `install`. `bun i`, `bun add`,
  `bun update`, `bun --silent install`, `bun pm ...` pass straight to the real Bun without lock
  verification. Also any tool that spawns Bun by absolute path (process.execPath) bypasses PATH.
- Catalog validation and lock seeding look correct.

### dashboard/plugin_api.py
- New routes all depend on _memory_account; owner binding is checked again in
  MemoryPreferences._configuration and FreshStore/MemoryImport._owner.
- POST bodies are fixed-key; origin check is the existing router dependency.
- prepare_fresh runs in threadpool. OK.
- Error mapping: IncompatibleLifeOS converted; NotImplementedError is RuntimeError -> 409.

### memory_preferences.py
- prepare_import destination uses the same profile.parent pattern as fresh_store.
- No other defect found.

### memory_import.py
- Careful: signature over review, re-review before rename, per-item request IDs,
  replay returns stored receipt without re-running record_result (checked memory_access
  _operation), so apply retries do not hit the imports primary key.
- _filter_history(reviewed=True) skips the time check, so preview/prepare signatures are stable.
- No defect found.

### memory_backup.py / memory_backup_recovery.py
- _collect -> _read opens non-regular files without O_NONBLOCK before the S_ISREG check. A FIFO
  under USER would block forever while the memory transaction lock is held. Low; same-uid only.
- Recovery restores arbitrary modes up to 0o777 from the manifest. Low.

### profile_backup.py
- Walks the whole HERMES_HOME (see raw data 4). Default layout includes hermes-agent checkout.
- `_databases` takes BEGIN IMMEDIATE on every SQLite file in the profile for the whole
  collection; the CLI path does not drain services, so a running gateway's writes block on
  state.db and can hit their busy timeout.
- For the default profile (~/.hermes) the walk also includes ~/.hermes/profiles/* (all named
  profiles).

### profile_backup_recovery.py
- Link targets validated lexically in inspect; links created after files, so no write through a
  restored link. No defect found.

### ownership_setup.py / memory_ownership.py / profile_services.py
- Not reachable from dashboard or CLI at 71987ce (git grep finds no caller outside tests).
- recover() with ownership state 'rolled_back' and matching signature still calls
  ownership.rollback(); rollback() then requires current files == 'before'. Any later
  config.yaml edit makes recovery fail after services.quiesce() already stopped services.
- prepare()/apply() leave services drained on any exception (by design: journal + recover).
- ProfileServices drains hermes-dashboard.service. If a future dashboard route calls
  OwnershipSetup, the dashboard would stop itself mid-operation.

### plugin.yaml / memory_provider.py
- provides_middleware declared. register_provider registers required middleware only when
  REQUIRED_MIDDLEWARE_API_VERSION == 1; any other value registers nothing and raises nothing,
  even with runtime enabled.

### hermes-required-middleware.patch
- turn_request_assembly: stops stripping user-role content. Neutral for providers; user
  whitespace-only content was already invalid after stripping.
- Applies cleanly (raw data 3).

### memory_hermes_soul.py (skimmed)
- Overwrites profile SOUL.md and workspace .hermes.md; the original is retained only in the
  crash journal, which is deleted on success. Checked afterwards: mount_transaction.py:18 FILES
  includes SOUL.md, so the mount snapshot keeps the pre-LifeOS original and the mount already
  replaces SOUL.md. Not reported as a defect.
