# Updating the Hermes and LifeOS bridge

The current bridge is a tested combination of three independent code bases. The plugin installs LifeOS into a new account, updates an installed LifeOS from a tested candidate, and can apply or restore its tested Hermes patch set. No later upstream revision has passed the compatibility gate. The source preparation command builds the pinned combination from known base commits.

| Component | Current test source | Update risk |
| --- | --- | --- |
| Hermes | Base `758ad514eb0e800547e015edf05aa18f78b78d82` plus eight patch groups | Stock plugin events do not provide every LifeOS control. A normal source update can switch away from the patched feature branch or leave untested patch merges. |
| LifeOS | Base `5e2f2e8c0abde612da0e99c16c0d07d4ec21b88c` plus nine patches | Hook files and registrations can change. The current `DeployCore.ts` uses `copyMissing`, which does not replace an already installed system file. Repeating the install commands alone cannot prove deployed hooks match a new source release. |
| Bridge plugin | Public Git commit pinned during install | A plugin update cannot restore missing Hermes events or port LifeOS source changes. Hermes refuses automatic updates of a pinned plugin. |

## Rule for the current `.212` test installation

Do not use the Hermes dashboard Update button or `hermes update` to advance this patched test install. Do not run a LifeOS update over its deployed hook tree. The test account now sets `updates.auto_switch_parked_branch: false` in `~/.hermes/config.yaml`. Hermes documents that this prevents a clean parked feature branch from being switched to the update target. This guards one failure mode only. The setting can be reverted with `hermes config set --force updates.auto_switch_parked_branch true`; the prior config is backed up at `~/.hermes/config.yaml.before-update-guard-20260928`.

The original `lifeos-hermes` account uses a shared root: `~/.claude` links to `~/.hermes`. The LifeOS update worker requires separate roots and refuses this layout. The 2026-09-29 release uses a private operator transaction for the shared root. It preserves generated identity files, unchanged hook registrations, model settings, credentials, and user data. Its snapshot and checks are recorded in [the release note](../notes/2026-09-29-release-212.md). Use the separate-root layout in [the clean install guide](clean-install.md) for a new server. The `.211` and `.213` installations are outside this deployment plan.

## Required update workflow

1. Choose exact upstream Hermes and LifeOS commits and one exact bridge plugin commit. Record the three revisions as a tested compatibility set.
2. Prepare new source trees away from the running install. Port each required change to those revisions. Stop if any patch conflicts or if an upstream change makes a patch unnecessary.
3. Compare the new LifeOS hook registration manifest and deployed system files. Check every registration against the bridge event map. Snapshot the system files that `OverlaySystem.ts` will change before applying its update. Do not advance the LifeOS version marker while files remain stale.
4. Run the bridge suite, Hermes core tests, native LifeOS hook tests, and live `.212` checks for the affected events, including the local model routes and Discord watchdog path when those parts change.
5. Back up the running code, Hermes profile, and LifeOS data separately. Keep user-owned `USER/` and `LIFEOS/MEMORY/` content out of system-file replacement. Hermes's quick update snapshot covers selected state files, not application code.
6. Install the tested source and plugin revisions, restart the gateway, and verify the running code, hook registrations, and model route. If a gate fails, restore the code and data snapshots before accepting another message.

The LifeOS settings page starts a detached update worker for a prepared candidate. The worker makes a fresh reference install, checks managed-file ownership, stages source files and dependencies, replaces exact LifeOS-owned hook registrations, and snapshots Hermes mount files and the VersionDrift baseline. It stops the gateway, swaps the staged tree, remounts LifeOS, renews the baseline, restarts the gateway, and checks the native hooks and running service. A failure after stop restores the prior tree, mount files, and baseline. An interrupted swap has a recovery action. The [service-backed update rehearsal](../notes/2026-09-29-lifeos-update-transaction.md) passed apply, restore, and forced-failure rollback on the pinned revision. A newer upstream revision and authenticated page click have not been tested.

The update worker keeps the prior candidate source because the baseline refers to it. A later supported candidate uses a new directory and a plugin-owned selection file. A changed `CLAUDE.template.md` or `settings.system.json` requires a reviewed migration before the worker will stop the gateway. A normal Hermes source update is separate from this LifeOS worker.

The older `scripts/release_transaction.py` stages Hermes code, bridge code, Hermes config, and LifeOS system files as one transaction. It does not install LifeOS dependencies, change hook registrations, or renew the VersionDrift baseline. Keep it for the Hermes and plugin release gate, with those limits. See the [system-file rehearsal](../notes/2026-09-28-overlay-rollback-rehearsal.md), [coordinated rehearsal](../notes/2026-09-28-release-transaction-rehearsal.md), and [service rehearsal](../notes/2026-09-29-service-release-rehearsal.md).

The transaction command has three actions: `stage`, `apply`, and `restore`. Stage requires separate current and candidate paths for Hermes and the bridge, a LifeOS payload, the installed LifeOS root, and Hermes config. Apply requires an executable verifier and either a named gateway service or `--no-gateway` for an account with no running gateway. It refuses changed candidate Hermes code, bridge code, or LifeOS payload before stopping the service. The snapshot is private and can contain a copy of Hermes config, so keep it in the target account's home directory. The current rehearsal command does not install new dependencies or change LifeOS hook registrations in `settings.json`.

For a prepared LifeOS source and a stopped test gateway, use the following LifeOS file sequence. Inspect the dry run and keep the snapshot until the updated install passes its checks:

```sh
python scripts/system_overlay_snapshot.py snapshot \
  "$LIFEOS_SRC/LifeOS/install" "$HOME/.claude" "$HOME/workspace/lifeos-overlay-snapshot"
bun "$LIFEOS_SRC/LifeOS/Tools/OverlaySystem.ts" \
  --config-root "$HOME/.claude" --skill-root "$LIFEOS_SRC/LifeOS"
bun "$LIFEOS_SRC/LifeOS/Tools/OverlaySystem.ts" \
  --config-root "$HOME/.claude" --skill-root "$LIFEOS_SRC/LifeOS" --apply
python scripts/system_overlay_snapshot.py verify \
  "$HOME/workspace/lifeos-overlay-snapshot" "$HOME/.claude"
```

To restore the prior LifeOS system files, run `python scripts/system_overlay_snapshot.py restore "$HOME/workspace/lifeos-overlay-snapshot" "$HOME/.claude"`. If an installed file changed after the overlay, restoration refuses it. Inspect the change, then add `--preserve-divergent` to save that file in the snapshot's `divergent/` directory before restoration. The tool does not update `settings.json`; hook registration changes require a separate verified step.

The LifeOS Bridge page offers **Prepare latest LifeOS update** and **Apply prepared LifeOS update** for the tested revision. It does not call `hermes update` or repeat `DeployCore.ts --apply` over the live tree. Its registration replacement accounts for the native installer's empty-matcher grouping, preserves unrelated hooks, and refuses edited or duplicate old hooks. [The ownership probe](../notes/2026-09-29-update-tool-ownership.md) records the 74-hook check.

The long-term way to reduce this maintenance cost is to contribute the generic Hermes hook events upstream and make the LifeOS handlers accept Hermes event data upstream. Until both sides contain those changes, the compatibility set and staged verification remain necessary.
