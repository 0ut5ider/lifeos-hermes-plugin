# Supplementary qualification provenance

The [supplementary receipt](../QUALIFICATION-PROVENANCE.json) adds provenance to the immutable initial certificate. The initial certificate SHA-256 remains d4b002d377ccfda5375bd6cfb4fdb1bbc49f5e8cc9c1be2fa7df54386f65ef58. No program, test assertion, or qualification result changes.

The receipt binds the [complete integration log](archive-integration-70fa8390.stderr.gz). Its decompressed SHA-256 is f3d817c84afedccd8b8da7180182e1f762126d6a625107d7e67c5e183a9585fc (213,465 bytes). Its compressed SHA-256 is a34f741d6a10f7bb9d74803e2710aa38edc6a837cc7b4a9fcb2d09727bfce2d8. The log records 1,129 executed cases, 1,126 passes, two errors, and one failure. There are no skips.

| Case | Unittest result | Measured cause | Passing replay |
| --- | --- | --- | --- |
| test_profile_backup.ProfileBackupScopeTests.test_regenerable_and_runtime_entries_are_excluded_and_recorded | ERROR | AF_UNIX path too long | All 35 backup cases under a short private temporary path |
| test_removal_consumers.RemovalConsumersTests.test_running_bun_outside_reviewed_service_groups_refuses | ERROR | PermissionError reading /proc/814420/exe | Eight isolated service-account cases |
| test_removal_coordinator.RemovalCoordinatorTests.test_exact_running_coordinator_is_admitted | FAIL | The account process boundary refuses sshd-session inspection | Eight isolated service-account cases |

The initial certificate uses "two named workstation failures" collectively for the process-inspection cases. Strict unittest terminology is one error and one failure for those two cases. The socket error is the third non-passing result. The table above names each case and separates the causes.

## Recorded socket replays

The supplemental replays capture their exact command, working directory, TMPDIR, device identity, timestamps, output hash, and exit status. The long path is /home/outsider/.cache/lifeos-release-0.7.3-20261016/qualification-tmp. The short path is /home/outsider/.cache/q73-20261016. Their device identifiers match. This filesystem measurement is captured again with these replays; it is not inferred from the earlier unrecorded commands.

The [recorded long-path replay](socket-provenance-long.txt.gz) reproduces AF_UNIX path too long. The [recorded short-path replay](socket-provenance-short.txt.gz) passes all 35 unchanged backup cases. The receipt binds both outputs and their exact invocation metadata.

## Complete boundary source

The isolated replay uses the source tarball from commit 99e18c44f1c09a894125299f5469f256122244f7, before the test-only process-exit repair. The receipt records its SHA-256 and reproduces it with git archive over tests, lifeos_hook_bridge, and optional. All 787 regular files appear in the [source map](boundary-source-map.json.gz).

A complete map comparison against the qualified 70fa8390 archive finds one difference: tests/test_memory_owner_job_processes.py. That test module is not part of, or imported by, the eight boundary cases. Every plugin and manager source file matches the qualified archive. This includes removal_preparation.py and release_programs.py, which the initial six-file receipt did not hash separately.

The [actual 0.7.3 replay operator](account-boundary-operator.py.gz) copies Hermes from the earlier 0.7.3-99e18c44 package. The cleanup-era operator used 0.7.2, but it is not the operator for this replay. All 18,270 Hermes program files in the earlier candidate match the qualified 0.7.3 archive. Native Git metadata is excluded from that program comparison.

The [raw boundary output](boundary-replay.stderr.gz) records eight tests, OK, and no skips. The original receipt confirms that the disposable account and its home are removed. The supplementary receipt binds the complete source map, actual operator, and raw output. It supplements the original six-file receipt without replacing it.
