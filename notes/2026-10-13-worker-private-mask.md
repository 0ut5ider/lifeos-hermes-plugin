# Native worker mask during release qualification

2026-10-13. Clean 0.4.2 installation selects the frozen package. Fresh ownership activation then refuses its profile backup because files have shared write permissions. The ownership coordinator cancels the incomplete operation and restores the dashboard.

The owner dashboard service reports `UMask=0077`. A real transient service under the same user manager reports an inherited mask of `0002`. The detached release worker does not inherit the dashboard service mask. Its native mount creates `mount-plan.json` and `.env` with mode `0664` at 23:03:16 UTC. The profile backup requires files without shared write access. This establishes a release worker defect, separate from the earlier test-unit working directory and file mask errors.

The regression runs the actual worker entrypoint with a shared service mask. A traced dispatch boundary starts a real child process that creates a file and directory. Before the fix, the file has mode `0664`, and the test fails against `0600`. The worker entrypoint now selects mask `0077` before dispatch. The file then has mode `0600`, and the directory has mode `0700`. All 45 focused operation, command, preparation, and fresh-install controls pass without skips.

The original sealed 0.4.2 archive remains an unpublished historical candidate. Qualification must build a new archive and repeat fresh installation and ownership acceptance. The next clean guest must use a private dashboard mask before its first native startup. No production release or daily deployment occurs during this correction.
