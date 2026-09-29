# Partial Hermes patch and LifeOS Edit hooks

Date: 2026-09-29. The isolated `.212` account used Hermes source `758ad514e` with the tested patch bundle.

A two-file V4A patch was passed to the real `tools.patch_parser` with an in-memory file backend. The first write succeeded. The second write returned `forced second write failure`. Hermes returned `success: false`, `files_modified: ['first.txt']`, and an apply-phase error. The backend held `new-a` in `first.txt` and the original `old-b` in `second.txt`.

The bridge classified that one tool call as `PostToolUseFailure` and emitted no `Edit` PostToolUse event. Thus an installed LifeOS hook that updates state after an Edit could not see the file that changed. A regression confirmed that its PostToolUse recorder did not run.

The bridge now reports an `Edit` PostToolUse event for each operation in Hermes's applied-file lists and one PostToolUseFailure for the overall patch. A failed validation with no applied files reports only failure. The seven pinned LifeOS `MultiEdit` handlers each also register for `Edit`, so the per-file events reach the same installed handler scripts through their `Edit` registrations. A partially applied repeated target has no operation index in Hermes's result. The bridge sends one path-only `Edit` with empty changed-line strings in that case, leaving line-count parity open.

An installed `.212` ComplexityRatchet test used the real Hermes parser, then refused the second write. Its native hook counted 249 net added lines from the first file, and the transcript recorded one successful `Edit` result and one failed patch result. The broader bridge module passed 179 tests.

A second disposable worktree test found a safety consequence. When the first applied path was an ISA with a checked criterion, the installed CheckpointPerISC hook committed the worktree even though the overall patch failed. The commit changed HEAD from `5e2f2e8` to `d5c71d0` in the red test. The bridge now defers this commit-producing hook for partial results. The green test left HEAD unchanged after the failed patch, then invoked the same hook on a successful result and confirmed a new commit plus `ISC-1` in checkpoint state.

The initial full plugin suite failed one source-preparation fixture because the staged test copy had no `.git` directory. After the Git metadata was supplied and the checkpoint deferral change was made, the complete suite ran 382 tests. It passed with 65 optional skips. The native checkpoint test used the installed `$HOME/.claude/hooks/CheckpointPerISC.hook.ts` command through a disposable home-directory symlink.

The probes used synthetic files and a disposable Git worktree. They did not change the installed LifeOS files. Raw prompt text and private data were not involved.
