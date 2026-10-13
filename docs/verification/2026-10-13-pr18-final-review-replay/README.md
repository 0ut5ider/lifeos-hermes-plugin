# PR18 final review and default GitHub installation replay

The review covers the complete PR18 product diff and the final review corrections at b9d353cdf1cca571194d1f60c269efdc97880fe5.

The first review identifies two defects. The running dashboard profile is not bound to the selected installation. Synchronous preparation does not hold the dashboard preparation lease. The recorded failing probes reproduce both defects before correction.

The next review identifies redundant decoding of effective systemd percent signs. The primary real unit test also finds that systemctl omits empty EnvironmentFiles. The parser preserves the effective path and rejects nonempty environment files.

The actual CT106 trial identifies the official bundled Hermes launcher as an additional command shape. The adapter recognizes only that exact inline source. Real child tests reject foreign profiles and unrelated inline programs.

The final actual CT106 service component trial passes. A foreign profile keeps PID 5018 after admission refuses. No service journal is written. A matching profile drains and restarts from PID 5030 to PID 5052. The main dashboard PID 4038, configuration hash, and release hash stay unchanged. Temporary units and synthetic profiles are removed. This trial does not claim complete installation acceptance.

The primary repeats 111 selected tests (108 executed and three optional fixture skips), seven archive and lease controls without skips, three UI contracts, and eight version tests. The complete archive-bound rc.3 qualification and post-merge default GitHub web replay are separate gates.

Published rc.1 and rc.2 assets remain historical checkpoints. The corrected candidate uses rc.3. Production and development deployments are outside this replay.

The default GitHub web installation retrieves the PR18 merge commit f29e40a6a5e0565abe91994245d494b26a078ebf without a selected ref. The native sidecar records that source and commit. All 19 manager files match the candidate.

Post-merge synchronous preparation under the actual SSH caller umask 0002 fails before active program changes. The native metadata writer creates a 0775 directory and 0664 files. Source sealing refuses those shared-write modes. PR19 sets umask 0077 in stage subprocesses and preserves the parent mask. The actual metadata writer and 36 controls pass after correction. The independent follow-up review reports no findings. PR19 merges at ad3379f90018fc69a81cb8db022a8e5ea8e5a950.

The corrected unpublished rc.3 candidate uses program commit 10459df6c2b27bda8911dfd96a25b92bee769c93 and archive SHA-256 fe7a9bfbf1c3f68355fc1125f125fac8250a1f9ccecf95ff697b5979dc3d5474. The earlier b9d353cd archive completes 673 integration controls and remains a superseded checkpoint. The final corrected archive runs its own complete 674-control gate.

An attempted UI contention probe arrives after the synchronous preparation finishes. It starts a request for the unpublished public rc.3 release, which refuses without active changes. This probe does not prove real UI contention. The real lease regressions remain the contention evidence.
