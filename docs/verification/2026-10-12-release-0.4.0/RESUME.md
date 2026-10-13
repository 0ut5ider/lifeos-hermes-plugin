# Resume LifeOS 0.4.0 release qualification

Adrian authorizes merging PR14, qualification, and publication of the complete production release.
PR14 is merged at be215380dcbda35c92e6f28b23b4a1d7bc15004e.
The release branch is feature/release-0-4-0. PR15 is open at https://github.com/0ut5ider/lifeos-hermes-plugin/pull/15. No public 0.4.0 asset exists yet.

The current exact program commit is a87e7ae94894dabc3651454d1334cb23c4fae27e.
The archive SHA-256 is 82acd3da141ef5aad322b49f30a8306305c298fa6706d44cc320de54f76442da (119,131,156 bytes).
The immutable package is cache/lifeos-hermes-managed-20261012/packages/0.4.0-a87e7ae9.
Every sealed-source Python command requires PYTHONDONTWRITEBYTECODE=1 and -B.
The package pins Hermes v0.21.7 at 71d34bad, LifeOS at 5e2f2e8c, and Bun 1.4.3.
The patch count remains 10 Hermes plus 25 LifeOS groups.
The only product change after PR14 is the corrected Bun pin in two metadata files, plus stable version declarations.
All twelve native dependency locks remain exact. The Bun comparison verifies five isolated installations and no live-profile change.

Completed corrected gates:
- Sixteen focused native-dependency and version checks pass.
- The official Hermes runner passes 716 tests across 38 files. It uses a source copy and the new Bun.
- Stock plugin installation, CLI discovery, fresh integration, actual exit 73 at directory-retained, recovery, and later synthetic data preservation pass.
- Corrected .252 preparation and authenticated owner review pass.
- Actual .252 worker exit 73 at programs-published and authenticated recovery pass.
- Recovery verifies exact accepted 0.3.1, configuration, model hash, all aliases, and all three services.

The first corrected full run passes 624/625; its one failure is a proven mixed-timezone fixture setup.
Direct capture uses UTC while governed capture inherited Toronto. Both correct events exist in different day files.
The probe reproduces the failure with mixed zones and passes with uniform UTC.
The runner now supplies TZ=UTC, matching the official Hermes runner. Product sources and archive stay unchanged.
The UTC full repeat passes all 625 checks in 744.485 seconds. No replay is needed.
The failing receipt remains under integration-sealed-a87e7ae9-mixed-timezone.*.
The original 4644f90c package is superseded because of Bun 1.3.14 extraction failures. Never publish it.

Current development state:
- .252 now runs the exact corrected 0.4.0 after the verified normal update and guest reboot.
- The current normal operation is 5a659e7f11e1437b8e33d65f3e064426, applied.
- The interrupted corrected operation is 14215619fd654d9bab0028abe59b62af, rolled_back.
- The staging folder is /home/lifeos-hermes/releases/qualification-20261012-bunfixed.
- Normal review and apply both return HTTP 200. All aliases and services verify. All services start automatically after reboot with zero restarts.
- Browser tab: tab_f_6cbd26ac-befc-4d03-95f7-0b4474990134, authenticated owner on .252:9119.
- Call preview_status after a handoff. Use async fetch and bounded polling for long review/admission.
- The main .252 memory ownership is disabled. Do not call its authenticated review a native memory grant.
- .253 remains untouched on exact accepted 0.3.1.

Next actions:
1. The whole-guest controller is detached on .101 now. Check its process.done and private controller log before any replay.
2. Its Python environment is the normal operation python-environment/bin/python. Its operation is 5a659e7f11e1437b8e33d65f3e064426.
3. Complete its verification and cleanup before normal rollback.
4. The three synthetic Atlas cases already exist in deployment/history-recovery-0.4.0.
5. The .101 controller is /root/proxmox_history_restore_040.py. It requires LIFEOS_STABLE_PYTHON from the normal runtime and LIFEOS_STABLE_OPERATION.
6. It backs up only source guest 101 to PBS-01, restores unused guest 110, disconnects networking, masks all application services, verifies three Atlas cases and exact selected program targets, then removes the disposable guest.
7. Its output is /root/lifeos-release-0.4.0/history-restore. Export safe verification receipts, not secrets or raw private content.
8. Verify normal rollback through authenticated restore admission and observe exact 0.3.1.
9. After all gates pass, generate the public certificate. Private fixture certificates must never become release assets.
10. Push the release branch, create and link its PR, and obtain the authorized focused code review. Verify agent reports on disk and rerun their claimed probes.
11. Merge and publish new immutable v0.4.0 assets. Preserve every v0.3.1 asset and compare its inventory to v031-assets-before.json.
12. Verify the public GitHub catalog and complete package preparation path. Update release documentation with actual results.

GitHub writes use account 0ut5ider. Capture its gh auth token inside a subprocess environment without printing it.
Do not force push, skip hooks, import/reset personal data, fabricate memory grants, or manually run/send the morning job.
The shared memory tool returns integrity_error. Use repository evidence and do not bypass memory tools.
The primary owns Git mutations, pushes, merges, and publication.

PR15 review finds one P2 certificate receipt binding issue. The primary reproduces it.
The generator now checks integration commit, fresh preparation identity, native archive/source/runtime identity.
Thirteen isolated regression cases reject incomplete or mismatched evidence and accept the synthetic baseline only.
The official native repeat is deferred until the real SSH fixture .252 returns after backup.
The prior native receipt remains historical under native-sealed-a87e7ae9-unbound.*.
Native runner now extracts the immutable archive, validates source, checks original files after tests, and records exact identity.
Do not certify until the new bound native receipt passes. No product archive changes.

Current gate update: the backup passes in 2326.115 seconds. Source services resume successfully.
The restored guest 110 is still being created by the actual Proxmox restore task. Do not start another restore.
The identity-bound native repeat passes all 716 tests across 38 files in 71.471 seconds.
The original files are unchanged; archive, source manifest, tree, Bun version and binary hashes are recorded.
Both focused review rounds are clear. The primary repeats the actual historical-receipt refusal, thirteen-case old-generator failure, and reviewed file hash checks.
The post-backup development observer passes exact 0.4.0 identity, model mapping, commands and all services.
Still pending: disconnected restore verification/cleanup, normal owner rollback, public certification and publication, then public path verification.

Restore ceiling adjustment: source backup has 203.815 GiB logical data. Original restore intentionally cancels at 1006.659 seconds.
Native Proxmox cancellation removes guest 110 configuration and its partial volume. Source backup and .252 remain accepted.
Original attempt stays private under /root/lifeos-release-0.4.0/history-restore-initial-ceiling.
The resumed controller reuses archives.stdout via --resume-backup. Only pct restore timeout becomes 7200 seconds; all other commands keep 3600.
Controller PID1965942 log=/root/lifeos-040-whole-guest-controller-resume.log; main evidence folder unchanged.
A narrow independent review checks this one-line operational change. Final passing restore/verification still required.

Additional measured receipt correction: update.operation must equal rollback.operation.
A fourteen-case fixture probe reproduces acceptance of an unrelated rollback before the one-line fix, and all cases pass after it.
A focused review runs under docs/agents/2026-10-12-pr15-rollback-binding-review. The immutable program package remains unchanged.

Current receipt closure: twenty-nine certificate fixture cases pass. Before the latest fix, seven interrupted-worker proof cases are accepted incorrectly.
The generator now requires the actual exit 73 at programs-published, matching operation and exact commit, with applying/applied journal states.
The primary also repeats the reviewer actual current/missing/actual historical proof probe, which now passes.
The final focused review runs under docs/agents/2026-10-12-pr15-exit-proof-review.
The primary repeats the real .252 reboot and collects operation, active identity and changed boot IDs. All services start automatically with zero restarts.
The read-only post-reboot observer also passes. The dashboard tab is tab_g_6cbd26ac-befc-4d03-95f7-0b4474990134 after browser reopen.
The actual whole-guest restore is still running. Do not certify or roll back until it completes its verification and cleanup.

Final interruption prerequisite review is clear. All twenty-nine cases and actual historical proof refusal pass independently.
The primary reruns the reviewed three-case probe, including all fourteen certificate receipt hashes, and confirms exact reviewed file bytes.

Whole-guest controller finishes process.done 0. Actual restore, all three Atlas cases, and all 143 program targets pass. Guest 110 is removed.
Safe receipts: whole-guest-recovery.json, whole-guest-program-coverage.json, whole-guest-controller.json.
The normal owner rollback request first refuses HTTP 400 because an empty JSON body is supplied. This is a client request error; no effect occurs.
A corrected bodyless POST to operation 5a/restore is pending in browser tab_h_6cbd26ac-befc-4d03-95f7-0b4474990134 window.normalRollback040.

All corrected archive qualification gates pass. Whole restore verifies three Atlas cases and 143 program targets and removes guest 110.
Normal bodyless owner rollback passes HTTP 200, completes, and verifies exact 0.3.1, configuration, model mapping, aliases, and all services.
Public RELEASE-CERTIFICATE.json is generated, SHA-256 d57f24578a05467afd57df96b3bc9c2110a6b0b88777bac429544dd9f3b75a0d. Do not replace it.
Next: finalize PR15 and merge, publish immutable v0.4.0 assets, then actual public stock installation and default stable update on .252.
Daily .253 remains unchanged. No product code changes occur after sealed program commit a87e7ae9.

PR15 merges at de2172241a545b901188deab21461dac4c136700. v0.4.0 tags that merge; product files match sealed commit a87e7ae9.
The same draft release 411207062 is published after all three asset hashes/sizes pass. Draft tag lookup returns 404; authenticated release list locates it. No replacement or duplicate release occurs.
Public release https://github.com/0ut5ider/lifeos-hermes-plugin/releases/tag/v0.4.0 is latest stable. All 14 historical 0.3.1 assets remain exact.
Detached public stock installation PID 3971525 writes public-install-verification.json/.done and public-run.stdout/stderr.
Detached .252 public default preparation PID 4375 writes staging/public-preparation.json/.done. Helper prepare_public_update.py uses installed public CLI and validates real published certificate.
After both pass, actual owner review/apply public .252 operation, export observer, publish new public-installation-verification.json asset, and document in a documentation branch/PR.

Public verification exposes two actual issues. The tag ref is rejected because stock Hermes requires a full forty-character commit SHA. Driver/README/release notes now use the exact tag commit.
Explicit --version is a product parser collision: cli.configure stores its value in args.version, which native main checks for the global version command before plugin dispatch. Equals form also fails.
The fix stores args.release_version and keeps the external flag. Seven CLI tests and the full twenty-six focused controls pass with all required real fixtures and no skips.
Five version declarations now select 0.4.1. Current branch is feature/release-0-4-1. Published 0.4.0/0.3.1 assets remain immutable.
Development public operation 0234c583cc26473d9ff2a00b883ca368 is ready and actual owner review passes HTTP 200. Do not apply it; wait for corrected package qualification. Development remains exact 0.3.1.
Published 0.4.0 latest-only stock check runs detached PID 3981148. Its completion is in public-install-verification.json/.done. Prior two failures remain under public-tag-ref-failure-* and public-version-destination-failure-*.
Next: commit and build the corrected complete 0.4.1, open PR16, send focused reviewer, complete all release qualification and public exact-version/default update checks.
