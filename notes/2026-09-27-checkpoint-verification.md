# Checkpoint verification probe

Date: 2026-09-27

The installed LifeOS `CheckpointPerISC` hook committed with `--no-verify`, so it bypassed the repository's pre-commit hook. It also marked a criterion checkpointed after a failed commit or when an opted-in repository was missing. The hook was not run against a writable test repository while it still bypassed verification.

The [compatibility patch](../patches/lifeos-checkpoint-verification.patch) removes `--no-verify`. It creates a conventional subject shorter than 50 characters and includes the original ISC marker so LifeOS `Checkpoint.ts` can still find the commit. A failed commit or unavailable opted-in repository leaves the criterion pending. The patch applies cleanly to LifeOS base `5e2f2e8`.

In the isolated `.212` account, a temporary Git worktree held an untracked proof file. A temporary home held the ISA and one-repository allowlist. The worktree used a pre-commit hook that wrote a marker and then failed on the first attempt. The first native hook invocation ran pre-commit, created no checkpoint commit, and left `committed_iscs` empty. After removing the rejection flag, the second invocation ran pre-commit, committed the proof file, and recorded `ISC-1`. The subject was `chore(checkpoint): ISC-1 (checkprobe): The checkp`, which is under 50 characters. Another native probe showed that a missing opted-in repository leaves `committed_iscs` empty.

Finally, the installed native hook ran through the Hermes bridge's Write PostToolUse path in a second temporary worktree. The pre-commit hook ran, the worktree received a checkpoint commit, and `committed_iscs` contained `ISC-1`. Both worktrees and temporary homes were removed after their probes. No production repository or LifeOS data was touched.

An exceptionally long project slug can make the required subject prefix at least 50 characters. The patch reports that case and leaves the criterion pending. A failed pre-commit may leave files staged, which is normal Git behavior and preserves the operator's ability to inspect them.
