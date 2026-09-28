# Remote turns and desktop terminal state

Date: 2026-09-28. LifeOS base: `5e2f2e8`. Test host: isolated `.212` account.

The bridge already set `LIFEOS_NOTIFICATION_CHANNEL=discord` for a Discord turn, but LifeOS's KittyEnvPersist hook and shared tab setter did not consult it. A disposable home with fake Kitty variables showed that a remote SessionStart wrote `kitty-env.json` and a per-session Kitty record. A direct tab setter call under the same remote channel wrote a tab title record. No real terminal command succeeded in the probe.

Two regression assertions failed against the unpatched LifeOS files. The compatibility patch makes KittyEnvPersist exit for a non-desktop notification channel and makes `setTabState()` return before terminal or state work for that channel. Desktop characterization checks still pass: a CLI session persists Kitty state, and a desktop tab setter call writes its state. Four native tests passed against the patched files locally and on `.212`.

All six LifeOS patches applied in order to a fresh worktree at `5e2f2e8`, with `git apply --check` before each application and a clean final `git diff --check`. The installed `.212` files match the source checksums. The `.212` LifeOS source commit is `621456a` on `feature/hermes-task-hook`; the full plugin suite passed 97 tests without skips. Production `.211` and `.213` were not changed.
