# Updating the Hermes and LifeOS bridge

The current bridge is a tested combination of three independent code bases. The plugin does not yet update Hermes or LifeOS. Its source preparation command builds the pinned combination from known base commits; it is not an updater for a later release.

| Component | Current test source | Update risk |
| --- | --- | --- |
| Hermes | Base `758ad514eb0e800547e015edf05aa18f78b78d82` plus seventeen patches | Stock plugin events do not provide every LifeOS control. A normal source update can switch away from the patched feature branch or leave untested patch merges. |
| LifeOS | Base `5e2f2e8c0abde612da0e99c16c0d07d4ec21b88c` plus nine patches | Hook files and registrations can change. The current `DeployCore.ts` uses `copyMissing`, which does not replace an already installed system file. Repeating the install commands alone cannot prove deployed hooks match a new source release. |
| Bridge plugin | Public Git commit pinned during install | A plugin update cannot restore missing Hermes events or port LifeOS source changes. Hermes refuses automatic updates of a pinned plugin. |

## Rule for the current `.212` test installation

Do not use the Hermes dashboard Update button or `hermes update` to advance this patched test install. Do not run a LifeOS update over its deployed hook tree. The test account now sets `updates.auto_switch_parked_branch: false` in `~/.hermes/config.yaml`. Hermes documents that this prevents a clean parked feature branch from being switched to the update target. This guards one failure mode only. The setting can be reverted with `hermes config set --force updates.auto_switch_parked_branch true`; the prior config is backed up at `~/.hermes/config.yaml.before-update-guard-20260928`.

## Required update workflow

1. Choose exact upstream Hermes and LifeOS commits and one exact bridge plugin commit. Record the three revisions as a tested compatibility set.
2. Prepare new source trees away from the running install. Port each required change to those revisions. Stop if any patch conflicts or if an upstream change makes a patch unnecessary.
3. Compare the new LifeOS hook registration manifest and deployed system files. Check every registration against the bridge event map. Snapshot the system files that `OverlaySystem.ts` will change before applying its update. Do not advance the LifeOS version marker while files remain stale.
4. Run the bridge suite, Hermes core tests, native LifeOS hook tests, and live `.212` checks for the affected events, including the local model routes and Discord watchdog path when those parts change.
5. Back up the running code, Hermes profile, and LifeOS data separately. Keep user-owned `USER/` and `LIFEOS/MEMORY/` content out of system-file replacement. Hermes's quick update snapshot covers selected state files, not application code.
6. Install the tested source and plugin revisions, restart the gateway, and verify the running code, hook registrations, and model route. If a gate fails, restore the code and data snapshots before accepting another message.

The preparation command covers the pinned source pair in step 2. A LifeOS system-file snapshot and restore tool now covers part of step 5, and `OverlaySystem.ts` performs the LifeOS file replacement in step 6. The `.212` clean account passed an overlay, rollback, and reapply rehearsal while preserving synthetic `USER` and memory files. It also exposed a generated timestamp change that requires `--preserve-divergent` on rollback; the divergent file is archived before restoration. Hermes code, plugin code, model settings, and the running gateway still need a coordinated staged update and rollback test. See [the rehearsal](../notes/2026-09-28-overlay-rollback-rehearsal.md).

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

A future LifeOS Bridge **Check for updates** control should show compatible versions and test results. **Apply update** should be available only for a tested compatibility set with a recoverable snapshot. The button must not blindly call `hermes update` or repeat `DeployCore.ts --apply`.

The long-term way to reduce this maintenance cost is to contribute the generic Hermes hook events upstream and make the LifeOS handlers accept Hermes event data upstream. Until both sides contain those changes, the compatibility set and staged verification remain necessary.
