# PR #3 runtime and host patch review

- Date: 2026-10-05
- Role: independent runtime code reviewer
- Model: Claude Opus (claude-opus-5-5)
- Question: Does PR #3 (branch feature/hook-compatibility-evidence, head 71987ce, base origin/main)
  contain real defects in `lifeos_hook_bridge/` and `patches/`: correctness, security, data loss,
  locking, or hidden failures?
- Method: read code only through `git show 71987ce:` and `git diff origin/main...71987ce`. No test
  suites were run. I ran small read-only snippets and applied the Hermes patches to an exported
  copy of the supported Hermes commit in /tmp. Raw data: `raw-notes.md` in this directory.

## Summary

I found no authorization gap, path traversal, or overwrite of live LifeOS or Hermes data in the
priority files. The new dashboard routes all require an authenticated dashboard session, and the
owner binding is checked again inside the operation. Every snapshot, recovery, and fresh-store
writer refuses an existing destination and stays outside the live trees. The Hermes patches apply
cleanly, in install order, to the supported Hermes commit.

The real problems are functional and availability defects, ranked below.

## Findings, most severe first

### 1. Profile backup cannot finish on the default Hermes install layout (high, functional)

- Where: `lifeos_hook_bridge/profile_backup.py:24-53` (`_entries`), with limits from
  `memory_backup.py:19-21`.
- Defect: `_entries` walks the whole Hermes profile directory, and the default Hermes installer puts
  its checkout and environments inside that directory.
- Scenario: The Hermes installer sets `INSTALL_DIR=$HERMES_HOME/hermes-agent`
  (`scripts/install.sh:79` in the upstream checkout). A local Hermes worktree without git objects is
  375 MB and has 24,842 files. `TOTAL_LIMIT` is 256 MiB. So `lifeos-backup --scope profile --create`
  fails with "exceeds its byte limit". An interpreter symlink that points outside the profile fails
  earlier, with "external profile link". `OwnershipSetup.prepare` calls `profile_backup.create`, so
  ownership setup is also blocked on this layout. For the default profile `~/.hermes`, the walk also
  includes every named profile under `~/.hermes/profiles/`.
- Confidence: plausible-high. I confirmed the installer layout and measured the tree size. I could
  not reproduce the failure, because this machine's `~/.hermes` has no checkout. Tests with a
  synthetic profile would not catch it.

### 2. A fresh-store preparation blocks client revocation for up to about 30 minutes (medium, security availability)

- Where: `fresh_store.py:158`, `memory_service.py:154-165` (`_lock`, a blocking `flock`), and
  `memory_sharing.py:142,151,165`.
- Defect: `FreshStore.prepare` holds `MemoryConfiguration._lock()` for the whole native
  install. That is six Bun steps with a 300 s timeout each, plus `bun install`. Every
  `MemoryConfiguration.update()` waits on the same blocking lock.
- Scenario: The owner starts a fresh-store preparation, then tries to revoke a compromised client
  connection or turn off sharing. `MemorySharing.revoke` and `MemoryPreferences.sharing` call
  `configuration.update()`, which hangs in a dashboard worker thread until preparation finishes. The
  revocation is delayed by minutes, and each stuck request also holds a threadpool slot.
  `prepare` never changes the configuration, so it only needs to verify the owner before and after,
  not hold the lock.
- Confidence: confirmed by reading.

### 3. Recovering ownership setup can get stuck with services stopped (medium, recovery path; currently unreachable)

- Where: `ownership_setup.py:182-197` and `memory_ownership.py:217-219`.
- Defect: When the ownership journal is already `rolled_back` with the same signature,
  `OwnershipSetup.recover` still sets `rollback_required=True` and calls `ownership.rollback()`.
  That call requires `config.yaml` and `lifeos-memory.json` to be byte-identical to the
  pre-setup state. `recover` calls `services.quiesce()` before the rollback.
- Scenario:
  1. `apply` commits, then `services.resume()` fails. The setup state stays `applying`.
  2. `recover` rolls back, then `resume()` fails again. The setup state stays `returning`.
  3. Hermes or the user edits `config.yaml`.
  4. Every later `recover` stops the gateway, dashboard, and PULSE, then raises "Ownership recovery
     preserves later configuration edits". Services stay down, and the journal can never reach
     `returned`.
- Confidence: confirmed by reading. `git grep` finds no dashboard or CLI caller of `OwnershipSetup`
  at 71987ce, so this is latent. Note also that `ProfileServices` stops `hermes-dashboard.service`.
  A future dashboard route that calls `OwnershipSetup` would kill its own process partway through.

### 4. The required-middleware registration fails open on any other host API version (medium, fail-open)

- Where: `memory_provider.py:102-110`.
- Defect: If `REQUIRED_MIDDLEWARE_API_VERSION` imports but is not `1`, `register_provider`
  registers neither `llm_admission` nor `llm_execution`, and it raises nothing, even when the
  memory runtime is enabled. The `ImportError` branch does raise.
- Scenario: A Hermes update bumps the constant to 2. The plugin loads normally, but model requests
  no longer pass through the memory admission and projection checks. Retired facts can then reach
  the model without an error.
- Confidence: confirmed by reading. The pinned `SUPPORTED_HERMES_COMMIT` limits exposure today.
- Fix direction: apply the same `if provider.runtime.enabled(): raise` rule in an `else` branch.

### 5. The Bun wrapper enforces frozen locks only for the literal `bun install` (medium-low, supply chain)

- Where: `native_dependencies.py:137-146`.
- Defect: The wrapper checks only `arguments[:1]==['install']`. These pass straight to the real Bun
  with no lock check: `bun i` (Bun's alias), `bun add`, `bun update`, `bun pm ...`, and
  `bun --silent install` (a global flag before the subcommand). Any LifeOS tool that starts Bun
  through `process.execPath` skips the PATH wrapper entirely.
- Scenario: An upstream install step runs `bun i` in a package directory. Bun resolves fresh
  versions and rewrites `bun.lock`, which defeats the release-lock catalog.
- Confidence: plausible. I could not read the LifeOS installer source (no candidate on this
  machine), so I do not know which form the install steps use.
- Fix direction: route every invocation through `_lock`, or reject any argument vector that names
  an install-like subcommand.

### 6. The fresh-store status probe can make other installation actions fail (low)

- Where: `fresh_store.py:142-146`.
- Defect: `status()` detects "busy" by taking the installation lock without waiting. While it holds
  the lock, a dashboard `_installation_action` (also non-waiting, `plugin_api.py:156`) gets
  HTTP 409 "Another installation operation is running".
- Scenario: The UI polls fresh status while the owner clicks remount or install. The click fails
  at random.
- Side effect: `busy` is global. While any unrelated installation operation runs, every unfinished
  store (including stores that crashed long ago) shows as `preparing`.
- Confidence: confirmed by reading.

### 7. Failed fresh preparations accumulate without limit (low, disk)

- Where: `fresh_store.py:165-177`.
- Defect: Each `prepare` creates a new UUID directory with a full LifeOS install, including the Bun
  dependencies. A failure leaves `failed-install/` and `review.json` behind. No route deletes or
  caps these directories.
- Scenario: Repeated failed attempts from the dashboard fill
  `~/.local/state/lifeos-hook-bridge/fresh-stores/<id>/`. A stray non-UUID entry in that directory
  makes `status()` return 409 every time (`_store` raises).
- Confidence: confirmed by reading.

### 8. State paths derived from `profile.parent` are wrong for named profiles (low)

- Where: `fresh_store.py:103-105` and `memory_preferences.py:162-164`.
- Defect: Both build `profile.parent/.local/state/...`. This is `~/.local/state` only when
  `HERMES_HOME=~/.hermes`.
- Scenario: With `HERMES_HOME=~/.hermes/profiles/work`, snapshots land in
  `~/.hermes/profiles/.local/state/...`, inside the Hermes root. Hermes does not list that
  directory as a profile, because `_PROFILE_ID_RE` filters it out. But a default-profile backup
  (finding 1) then picks up full LifeOS installs from other profiles.
- Confidence: confirmed by reading.

### 9. Identity rendering may over-replace template text (low, correctness)

- Where: `fresh_store.py:201-205`.
- Defect: DA_IDENTITY.md gets every `LifeOS` replaced with the assistant name, and both identity
  files get every whole-word `User` replaced with the principal name.
- Scenario: Template prose like "LifeOS skills" or a heading like "User Preferences" becomes
  "Ada skills" or "Adrian Preferences".
- Confidence: plausible. The shipped template was not available to check. The originals are kept
  in `identity-originals/`, so nothing is lost.

### 10. Error handling hides the cause of backup failures (low, diagnosability)

- Where: `cli.py:84-88` (`run_backup`).
- Defect: Every `ValueError`, `OSError`, `RuntimeError`, `sqlite3.Error`, or timeout prints the same
  generic message.
- Scenario: Finding 1's byte-limit refusal and a permissions error look identical, so the user
  cannot tell which limit or file blocked the backup.
- Confidence: confirmed by reading.

### 11. Minor robustness notes (low)

- `memory_backup.py:39-48` `_read` opens before it checks `S_ISREG`, without `O_NONBLOCK`. A FIFO
  under the USER tree makes `_collect` block forever while it holds the memory transaction lock.
  Only a process with the same uid can create one.
- `profile_backup.py:56-82` holds `BEGIN IMMEDIATE` on every SQLite file in the profile for the
  whole collection. The CLI path does not stop services first, so a running gateway's writes to
  `state.db` wait and can hit their busy timeout during a backup.
- `install_source.py:241-247`: after `killpg`, `process.communicate()` can still block if a step
  started a `setsid` daemon that inherited the pipes.
- `prepare_fresh` returns absolute paths and the full user-file inventory to the authenticated
  owner. This matches existing routes. I note it but do not count it as a leak.

## Files with no defects found

- `installation_lock.py`: the lease checks are correct. The lock order (installation, then
  configuration) is consistent across all call sites I checked.
- `dashboard/plugin_api.py` (routes added in this range): authentication, fixed request keys, and
  error mapping are all correct.
- `memory_preferences.py`: none, apart from finding 8.
- `memory_import.py`: the signatures are stable. Replay of a stored receipt does not call
  `record_result` again, so retrying `apply` does not hit the `imports` primary key.
- `memory_backup_recovery.py`, `profile_backup_recovery.py`: links are created after files, so
  nothing is written through a restored link. Destinations are checked against the live trees.
- `sqlite_snapshot.py`.
- `patches/hermes-required-middleware.patch`: it applies cleanly. In the patched tree,
  `invoke_middleware` re-raises for required callbacks. Stopping the strip of user-role content
  causes no regression that I can see.
- `plugin.yaml`: none, apart from finding 4.
- `memory_hermes_soul.py` (skimmed): it overwrites SOUL.md, but the mount snapshot
  (`mount_transaction.py:18`) already keeps the original.

## Files not reviewed or only skimmed

These are not reviewed: `memory_native.ts` (380-line diff), `patches/lifeos-memory-access.patch`
(6091 lines), `patches/hermes-plugin-events.patch` (content not read, but it applies cleanly),
`memory_runtime.py` (diff skimmed only), `memory_pulse_adapters.py`, `memory_freshness*.py`,
`memory_distill.py`, `memory_hypotheses.py`, `memory_wisdom.py`, `memory_interview*.py`,
`memory_learning.py`, `memory_recurrence.py`, `memory_seed.py`, `memory_state.py`,
`memory_telos.py`, `memory_graph.py`, `memory_evidence.py`, `memory_deny_hashes.py`,
`memory_derived_sync.py`, `memory_counts.py`, `memory_context_audit.py`, `memory_lineage.py`,
`memory_sources.py`, `memory_source_review.py`, `memory_publication.ts`, `memory_prompt.py`,
`memory_history.py`, `memory_http.py`, and the dependency `.lock` files. For the lock files I
checked only that the catalog validates their hashes.
