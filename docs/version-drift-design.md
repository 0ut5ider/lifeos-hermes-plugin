# VersionDrift baseline without a Git repository in Hermes home

## Observed constraint

The installed `VersionDrift.hook.ts` calls three Git operations from `$HOME/.claude`: list `vX.Y.Z` tags, get a tag commit time, and list changed core paths since that tag. On the isolated `.212` account, `$HOME/.claude` links to the live `$HOME/.hermes` directory. The installed tree has no Git repository. The source checkout also has no semantic-version tags. The hook consequently stays silent.

Initializing Git in the shared Hermes home would put credentials, sessions, caches, and runtime files under a repository worktree. It also includes about 76,558 files under `skills/` and 29,359 under `LIFEOS/PULSE/` because those trees contain generated dependencies. A naive baseline would be large and easy to populate incorrectly. The LifeOS source install contains about 1,816 system files across the hook's core paths before generated dependencies.

## Proposed plugin contract

1. A plugin command creates a local baseline from the installed LifeOS source manifest and its deployed system files. It records the installed `LIFEOS/VERSION`, the baseline time, the source commit, and content hashes for an explicit file list. It stores the baseline outside `$HOME/.hermes` Git state with mode `0600`. It never records `USER/`, `LIFEOS/MEMORY/`, credentials, sessions, caches, or generated dependency trees.
2. Only while running the installed `VersionDrift.hook.ts`, the bridge prepends a plugin-owned `git` adapter to `PATH`. The adapter answers that hook's three fixed read-only Git queries from the baseline and current file hashes. It delegates any other Git command to the system Git binary. Other LifeOS hooks and Hermes tools keep the normal `PATH`.
3. The adapter reports changed tracked paths, deleted paths, and new eligible LifeOS system files. It keeps the native hook's count, age, cooldown, and prompt text unchanged. A source update prepares a new baseline only after the updated files and native hook tests pass; it never silently resets accumulated drift.
4. The dashboard shows the current baseline version, source commit, and changed-file count. A user can create or renew the baseline through a separate action after reviewing the proposed file list. This action does not update Hermes or LifeOS.

## Verification required before deployment

- Test the adapter against the real native VersionDrift hook in a disposable home, including one changed file, ten changed files, a deleted file, a new file, a version bump in flight, and the one-hour cooldown.
- Confirm that ordinary `git` calls from other hooks and Hermes tools use system Git.
- Confirm the adapter handles an invalid or missing baseline by failing visibly without manufacturing a tag.
- Check the file list for secrets by path and file type, and test that runtime and dependency directories never enter the baseline.
- Measure the scan duration against the native hook's ten-second timeout on `.212`.

No baseline, Git repository, adapter, or installed configuration has been created as part of this design note.
