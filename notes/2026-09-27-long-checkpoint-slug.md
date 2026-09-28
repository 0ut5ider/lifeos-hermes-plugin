# Checkpoint for a long project slug

Date: 2026-09-27

Hypothesis: the compatibility patch's full ISC and project slug prefix can exceed the 49-character subject limit. The hook then skips a valid checkpoint even when an opted-in Git repository has new work.

On isolated `.212`, a disposable Git worktree, temporary home, and project slug `checkpoint-project-with-a-very-long-descriptive-slug-for-parity` reproduced the issue. The installed native `CheckpointPerISC` hook returned exit zero but logged that the subject prefix was too long. It created no commit and left `committed_iscs` empty. The first fixture had no ISC ID and returned before that branch; adding `ISC-1:` exposed the actual failure.

The hook now uses a short conventional subject when the full prefix is too long. It retains `ISC-1 (<slug>): <description>` in the commit body. `Checkpoint.ts` searches the full commit message with `git log --grep`, so its lookup still finds the commit. The native regression test passed on `.212`: a commit was created, its subject was under 50 characters, `committed_iscs` contained `ISC-1`, and `Checkpoint.ts show` printed its SHA.

The updated LifeOS compatibility change is committed on the isolated branch as `b7f0152`. The public patch was regenerated from base `5e2f2e8`, and reverse application checked against the installed branch. No production repository or LifeOS data was modified.
