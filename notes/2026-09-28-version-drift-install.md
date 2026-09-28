# VersionDrift cannot use the current deployed root

Date: 2026-09-28. The installed LifeOS `VersionDrift.hook.ts` runs `git -C $HOME/.claude tag -l v...` and `git diff` from the latest semantic tag. The fresh `.212` LifeOS install has `LIFEOS/VERSION` at `7.40.4`, but the source checkout has no semantic tags. The hook was silent in the deployed tree. A separate tagged disposable worktree made the native hook emit its warning, so dispatch itself works.

A read-only check found that `$HOME/.claude` on the `lifeos-hermes` account is a symlink to `$HOME/.hermes`. The target contains Hermes configuration, cache, credentials, sessions, plugin code, and other changing runtime state. Initializing Git at `$HOME/.claude` would put that shared runtime directory under Git. A broad add or a mistaken ignore rule could stage sensitive or transient files. This rules out a naive `git init ~/.claude` fix.

The version baseline needs a separate Git directory or a LifeOS hook change that can read a purpose-built baseline. Either design must track only installed LifeOS system files, preserve `USER/` and `LIFEOS/MEMORY/`, and integrate with updates and tags. No Git repository was initialized and no deployed files changed during this inspection. The safe design and verification remain open.
