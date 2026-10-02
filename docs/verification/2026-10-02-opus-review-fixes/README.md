# Corrections to the Opus PR review

Date: 2026-10-02

The [Opus review](../../agents/2026-10-02-opus55-pr1-review/opus55-pr1-review.md) identifies two behavior defects and two development or retention concerns.

## F1: Preserve later Hermes profile changes

The update manifest records the contents, permissions, types, and file set of the Hermes mount targets after an update. The restore route checks that record before it changes the job. The worker checks it again after stopping the gateway and before the LifeOS directory swap.

A changed profile refuses automatic restoration. A refusal after the gateway stops starts the gateway again. An older snapshot without the profile record cannot establish safe restoration and is refused.

The restore operation moves the current profile files and baseline into private `.lifeos-restore-*` directories beside the targets. The snapshot's `mount-before-restore/<operation>/archive-manifest.json` records those paths before each move. This preserves a write that races with the final check and supports targets on a filesystem separate from the version snapshot. A successful version restore records the index directory in `profile_archive`. Update rollback and interrupted recovery also preserve the profile versions that they replace. These update archives remain part of the version transaction, separate from temporary mount preparation copies.

Regression cases cover changed configuration, new environment files, removed prompts, plugin changes, empty directories, permissions, missing metadata, and a change while the gateway stops. A forced rename-boundary write verifies the private archive.

The [first Sol review](../../agents/2026-10-02-sol-review-fixes/sol-review-fixes.md) found three additional restore boundaries. A profile check after the program swap left the gateway stopped. Archive moves across filesystems failed with `EXDEV`. Worker error handling hid the authenticated recovery action. The correction removes the late content check, retains the two checks before the swap, and archives any later writes. Archive moves remain on each target filesystem. Worker failures preserve unfinished swaps as `interrupted` and harmless restore refusals as `applied`.

Further regressions exercise a write after the program swap, real `/tmp` and `/dev/shm` filesystems through restore, failed update rollback and interrupted recovery, and a process killed after a profile archive rename. A local authenticated route test checks that the worker error status permits a fresh owner-authorized recovery. File and directory synchronization supports publication ordering; these tests do not simulate power loss.

## F2: Check the complete direct child request

Direct child inference constructs the complete model request before admission. Admission checks the system prompt and generated user content as auxiliary input. The child sends no request when either contains a removed or superseded claim.

The regression uses a real local HTTP endpoint and a genuine forget operation. The existing positive route test still covers an approved child call. No real model receives synthetic test content.

## F3: Restrict environment capture

The development recorder retains environment variable names. Values are recorded only for `HOME`, `HERMES_HOME`, `PATH`, `PWD`, `LANG`, `LC_ALL`, `LC_CTYPE`, `TZ`, `BUN_CONFIG_NO_AUTO_INSTALL`, and `LIFEOS_CHILD_EFFORT`.

Other values become `[REDACTED]`. The recorder learns these hidden values before encoding the artifact and filters later echoes. Ordinary prompts remain intact. Arbitrary prose and unrelated encodings still have the documented filtering limits.

A real hook test compares native and recorded behavior while the hook echoes an unknown environment credential. The recorder remains outside the public plugin installation.

## F4: Remove unneeded mount preparation copies

The mount lock protects snapshot cleanup. A committed or rolled-back mount removes its snapshot payload. The credential-free journal remains available for status. A pending publication or restoration retains its recovery copies.

New snapshots have a private installation-bound identity record. A later operation can remove an abandoned preparation snapshot after process death. Cleanup preserves unknown directories, link targets, foreign identity records, and pending recovery snapshots. The current journal can also identify a completed snapshot created before the identity record existed. Unmarked historical directories that the journal does not identify require operator inspection.

Process-kill tests cover a pending publication, interrupted restoration, and preparation before journal publication. Repeat mounts and failed validation verify cleanup after terminal outcomes.

## Verification

`before.txt` records seven tests with 16 expected failures before the corrections. `recorder-before.txt` records the environment-filter regression failing for both supported mapping names.

The initial focused selection passes 47 cases. The final initial correction gate passes 349 cases, 32 development recorder cases, and 11 dashboard JavaScript cases. The Sol review records 133 repository test executions and 27 probe scenarios, including three defect reproductions. The primary independently reproduces those three defects and reruns the 24 positive probe scenarios. Its added four-test selection initially reports eight failures and two errors across subcases.

After the Sol corrections, 37 transaction, worker, and administrative dashboard cases pass. The additional process-death archive test passes. One initial run omitted `LIFEOS_MEMORY_SOURCE` and reported six native mount fixture failures. The corrected environment uses the prepared source and passes. Both outputs remain in the primary validation directory. The final regression gate and closure review will record their results separately.

The tests use disposable local data and pinned source fixtures. No server is deployed or modified. This correction batch does not activate memory ownership or establish complete memory or hook acceptance.
