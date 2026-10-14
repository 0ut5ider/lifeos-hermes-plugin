# Whole-guest backup size during release qualification

2026-10-13. The selected 0.4.2 runtime map covers 64,268 artifacts and 1,472,748,311 regular-file bytes. The whole development guest backup processes 272.427 GiB. The active runtime closure does not describe the size of the full guest backup.

The Proxmox inventory reports 168,804,876,288 used bytes before backup completion. Its allocated-space figure does not predict the logical bytes that the backup processes. A metadata-only aggregate size check reaches its 60-second limit and returns no total. The backup's own completion report supplies the measured total. I did not measure which file groups explain the difference.

The snapshot backup runs with the source application writers drained. It finishes successfully in 2,968.66 client seconds. It reuses 256.786 GiB, or 94.3%, and backs up 15.641 GiB of new data. That new data compresses to 4.623 GiB. The workflow resumes all three development services before starting the separate restore. The restore is still running at this checkpoint.

The safe [backup receipt](../docs/verification/2026-10-13-release-0.4.2/candidate-87205092/off-server-backup.json) binds the result to `PBS-01:backup/ct/101/2026-10-14T00:38:27Z`. The private artifact map stays on the guest. Release publication still requires the actual disconnected restore, all three Atlas cases, and successful workflow completion.
