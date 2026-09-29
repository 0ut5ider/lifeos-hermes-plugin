# Set up the LifeOS VersionDrift baseline

The native LifeOS `VersionDrift.hook.ts` expects a semantic-version Git tag in `~/.claude`. In a Hermes installation, `~/.claude` can be the live Hermes home without a Git repository. The bridge gives only this hook three read-only Git answers from a separate baseline. It does not initialize Git in Hermes home.

## Create a baseline

1. Install LifeOS and keep its Git source checkout available. The source path must point to its `LifeOS/install` directory. Its `LIFEOS/VERSION` must match the deployed `~/.claude/LIFEOS/VERSION`.
2. Open **LifeOS Bridge** in the Hermes dashboard. Enter the absolute source install path in **LifeOS source install path**.
3. Select **Preview baseline files**. Review the version, source commit, file count, and expandable file list.
4. Select **Create reviewed baseline**. The server hashes the installed files again and refuses the request if they changed since preview.
5. Select **Save settings** if you want the source path to remain in the form after reloading the page. The baseline action and model settings save are separate.

The command-line equivalent is:

```sh
~/.hermes/plugins/lifeos-hook-bridge/bin/version-drift-baseline \
  --source ~/workspace/LifeOS/LifeOS/install --installed ~/.claude
~/.hermes/plugins/lifeos-hook-bridge/bin/version-drift-baseline \
  --source ~/workspace/LifeOS/LifeOS/install --installed ~/.claude --apply
```

The default baseline is `~/.local/state/lifeos-hook-bridge/version-drift-baseline.json`. The plugin creates its directory with mode `0700` and the file with mode `0600`. It stores paths, hashes, the LifeOS version, source checkout path, source commit, and baseline time. It stores no file contents. Keep the source checkout available: the adapter reads its tracked file manifest when it scans for new LifeOS skills. The source manifest supplies the tracked file list; the plugin excludes runtime dependency directories and does not include `USER/` or `LIFEOS/MEMORY/`. An adapter failure writes a private diagnostic next to the baseline and appears on the dashboard page.

The baseline also excludes `LIFEOS/PULSE/state/`. Pulse writes daemon status, indexes, and caches there during normal operation. These files are runtime data. Changes to Pulse source files still count as system drift.

## Update and renewal

Baselines created before schema 2 do not contain the source checkout path. After upgrading this plugin, review the candidate file list and renew the baseline through the dashboard or with `--apply --renew`. Until renewal, the native hook receives no synthetic Git tag and the dashboard reports the schema error.

The baseline does not renew when LifeOS or Hermes updates. The dashboard marks an installed LifeOS version that differs from its baseline. Review the changed-file count and run the updated native hook tests before renewal. Preview the candidate file list again, then select **Renew reviewed baseline**. The command line requires `--apply --renew` to replace an existing baseline. A missing or unreadable baseline never creates a synthetic tag.

Only files inside LifeOS-owned skill roots recorded in the baseline or currently tracked by the source checkout count as new skill files. This avoids counting unrelated Hermes skills in the shared home. A newly tracked top-level LifeOS skill is counted as soon as it is installed. Changed tracked files, deleted tracked files, and new eligible files in other core directories are also counted.

The installed LifeOS registration runs VersionDrift asynchronously. Its warning reaches the next prompt after the hook finishes. The hook's count threshold, age threshold, one-hour cooldown, and warning text remain native LifeOS behavior. To disable the adapter without deleting LifeOS files, remove the baseline file; the hook becomes silent and the dashboard reports a missing baseline. Do not delete the shared Hermes home.

On the isolated `.212` installation, the reviewed baseline held 1,796 files. A fresh scan reported zero changes and took 0.346 seconds. The installed Git adapter's diff query took 0.368 seconds. Both are below the hook's ten-second timeout. The native hook passed tests for one old change, ten fresh changes, cooldown, a version bump in flight, and asynchronous delivery in a disposable home. Production `.211` and `.213` were not changed.
