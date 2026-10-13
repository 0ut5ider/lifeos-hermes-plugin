# PR18 final review and default GitHub installation replay

The review covers the complete PR18 product diff and the final review corrections at b9d353cdf1cca571194d1f60c269efdc97880fe5.

The first review identifies two defects. The running dashboard profile is not bound to the selected installation. Synchronous preparation does not hold the dashboard preparation lease. The recorded failing probes reproduce both defects before correction.

The next review identifies redundant decoding of effective systemd percent signs. The primary real unit test also finds that systemctl omits empty EnvironmentFiles. The parser preserves the effective path and rejects nonempty environment files.

The actual CT106 trial identifies the official bundled Hermes launcher as an additional command shape. The adapter recognizes only that exact inline source. Real child tests reject foreign profiles and unrelated inline programs.

The final actual CT106 service component trial passes. A foreign profile keeps PID 5018 after admission refuses. No service journal is written. A matching profile drains and restarts from PID 5030 to PID 5052. The main dashboard PID 4038, configuration hash, and release hash stay unchanged. Temporary units and synthetic profiles are removed. This trial does not claim complete installation acceptance.

The primary repeats 111 selected tests (108 executed and three optional fixture skips), seven archive and lease controls without skips, three UI contracts, and eight version tests. The complete archive-bound rc.3 qualification and post-merge default GitHub web replay are separate gates.

Published rc.1 and rc.2 assets remain historical checkpoints. The corrected candidate uses rc.3. Production and development deployments are outside this replay.

The first default GitHub web bootstrap retrieves the PR18 merge commit f29e40a6a5e0565abe91994245d494b26a078ebf without a selected ref. Its sidecar and 19 manager files match that checkpoint. The final replay after PR19 retrieves ad3379f90018fc69a81cb8db022a8e5ea8e5a950.

Post-merge synchronous preparation under the actual SSH caller umask 0002 fails before active program changes. The native metadata writer creates a 0775 directory and 0664 files. Source sealing refuses those shared-write modes. PR19 sets umask 0077 in stage subprocesses and preserves the parent mask. The actual metadata writer and 36 controls pass after correction. The independent follow-up review reports no findings. PR19 merges at ad3379f90018fc69a81cb8db022a8e5ea8e5a950.

The corrected unpublished rc.3 candidate uses program commit 10459df6c2b27bda8911dfd96a25b92bee769c93 and archive SHA-256 fe7a9bfbf1c3f68355fc1125f125fac8250a1f9ccecf95ff697b5979dc3d5474. The earlier b9d353cd archive completes 673 integration controls and remains a superseded checkpoint. The final corrected archive runs its own complete 674-control gate.

An attempted UI contention probe arrives after the synchronous preparation finishes. It starts a request for the unpublished public rc.3 release, which refuses without active changes. This probe does not prove real UI contention. The real lease regressions remain the contention evidence.

## Final qualification

The corrected archive runs 674 integration tests without skips or failures. Its 21,085 regular files match the archive before and after execution. Generated test bytecode is recorded separately. The retained archive stays unchanged.

The earlier native gate runs 716 tests at commit 914ad24b0eea7f0022e75edc815f5be08566d0f9. Exact archive comparison confirms that all 20,269 native and Python runtime files match the corrected archive. This qualification reuses that native result. It does not claim a new execution of those 716 tests at commit 10459df6.

The corrected guest preparation passes under the SSH caller mask 0002. A deliberate interruption after program publication exits with status 73. Recovery admits the exact operation and applies the package. A complete installed update also applies. Both preserve later synthetic data with mode 0600, model configuration, and prior tier settings. These two operations use private qualification assets. Their receipts do not claim public user actions.

The first certificate review identifies missing recovery admission checks and missing loaded-unit checks. The corrected certificate checks the recovery identifier, exit status, queued result, unit load state, native presence, program state, and target count. The final independent review reports no findings. Four certificate tests run 12 subprocess cases, including 11 altered inputs that must refuse certification.

## Final default GitHub URL replay

1. Restore CT106 at 192.168.8.249 to the stock managed-dashboard baseline.
2. Enter `https://github.com/0ut5ider/lifeos-hermes-plugin.git#optional/lifeos_release_manager` in the native Hermes Plugins page.
3. Select **Force reinstall** because the test baseline already contains the small manager plugin.
4. Install the manager without a selected ref.
5. Restart the dashboard through the Hermes web chat.
6. Enter the explicit test version `0.4.2-rc.3` and synthetic names on the LifeOS releases page.
7. Select **Install LifeOS**.
8. Review operation `9a48c820b659418db29f4e177e7ed9e9` and its exact commit and archive hash.
9. Select **Install this release**.
10. Verify the installed source identity after the dashboard restarts.
11. Send the synthetic chat prompt and verify the separate assistant reply.

The native plugin sidecar records default-branch commit ad3379f90018fc69a81cb8db022a8e5ea8e5a950 and no selected ref. All 19 manager files match the qualified source. LifeOS is absent before this operation. The replay installs a fresh synthetic store without personal imports.

The public operation applies all 11 first-installation targets. It preserves model configuration and prior tier settings. The dashboard returns active. Gateway and Pulse units are loaded, disabled, and inactive, as required by this synthetic installation. `hermes lifeos-version` reports 0.4.2-rc.3, the exact qualified program commit and archive hash, verified plugin sources, and no modified files.

The post-installation Hermes web chat returns `PR18-PUBLIC-REPLAY-CHAT-PASS` as a separate assistant reply. It does not show a tool call. The raw capture records the bundled terminal banner as `vunknown`; the installed release identity is verified separately by the version command.

During the public operation, all preparation buttons are disabled. A duplicate click cannot submit another operation. This check verifies disabled UI controls. It does not claim an additional concurrent backend request.

## Published evidence and limits

The [rc.3 prerelease](https://github.com/0ut5ider/lifeos-hermes-plugin/releases/tag/v0.4.2-rc.3) contains the exact qualified archive and dashboard assets. The initial release certificate remains an immutable historical checkpoint. The new [final verification asset](https://github.com/0ut5ider/lifeos-hermes-plugin/releases/download/v0.4.2-rc.3/FINAL-GITHUB-INSTALL-VERIFICATION.json) records the completed public replay and receipt hashes. Its SHA-256 is 5ecbeac031c27f85edf0948183e97e869fdf9b2dcc88e1301bca320eaa32f34e.

All 11 previously published rc.1, rc.2, and initial rc.3 assets retain their original digests. The latest stable release remains 0.4.1. The empty release field therefore does not select rc.3.

The test covers a synthetic managed-dashboard installation. It does not qualify memory ownership activation, whole-guest recovery, or daily deployment. The bootstrap uses force replacement of a preinstalled manager. These limits are explicit in the final verification asset.

Read-only health checks confirm that development server .252 stays at 0.4.1 and daily server .253 stays at 0.3.1. Gateway, dashboard, and Pulse stay active on both servers. The test guest remains at .249 on rc.3. Its retained stock baseline permits another isolated replay. Only CT106 is reset for this task.
