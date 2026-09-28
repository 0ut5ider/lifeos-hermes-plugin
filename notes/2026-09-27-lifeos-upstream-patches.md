# LifeOS patches against current upstream

Date: 2026-09-27. Public upstream: `danielmiessler/LifeOS` HEAD `5e2f2e8c0abde612da0e99c16c0d07d4ec21b88c` at the time of the check.

The four compatibility patches applied in the documented order to a fresh upstream checkout. Each passed `git apply --check` before application, and `git diff --check` found no whitespace errors afterward. The patches changed TaskGovernance, AgentWatchdog, EventLogger, and CheckpointPerISC.

Five native tests passed against the patched task, watchdog, and terminal audit files. The long-slug checkpoint test also passed with its hook and lookup tool linked from the fresh checkout into a disposable home. The test created and removed a disposable Git worktree. No production LifeOS files were changed.

This verifies source compatibility and six native behaviors. A fifth [FailureCapture patch](../patches/lifeos-failure-capture.patch) subsequently applied in the same sequence to a fresh worktree at `5e2f2e8`, with `git apply --check` for every patch and a clean `git diff --check`. Its native transcript regression passed against patched source and the installed `.212` file. See [the failure capture record](2026-09-27-failure-capture-tool-results.md). These checks do not test a complete fresh LifeOS installation or automatic deployment of the patched files. The isolated `.212` account runs an installation made from the same base revision.

A sixth [remote desktop gate patch](../patches/lifeos-remote-desktop-gate.patch) applied after the fifth in another fresh worktree at `5e2f2e8`. Its four native tests passed on `.212`. See [the remote terminal record](2026-09-28-remote-terminal-state.md).
