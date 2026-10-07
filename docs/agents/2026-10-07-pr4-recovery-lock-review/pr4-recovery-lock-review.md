Date: 2026-10-07
Role: Targeted recovery and account-lock reviewer
Question: Does exact PR #4 head e7c10d02f2e4385bcea76e9dc0880aabb962c3f3 close the prior three failures and preserve edits across recovery retries?
Model: Inherited GPT-6 model, specific runtime alias unavailable to this agent.

Merge recommendation: Request changes. A P1 owner-edit loss remains across two real process-exit boundaries during compensation. An inherited P2 failed-launch status trap blocks further account selection.

P1: Revalidate the active mount on each compensation attempt before remounting the previous root.

Source: lifeos_hook_bridge/installation_selection.py lines 140-156; lifeos_hook_bridge/selection_worker.py lines 132-137.

The first compensation attempt sets target_mount_recovered=True. All later attempts skip recover_mount. Each attempt still calls mount(previous_root), and that explicit mount bypasses the completed fingerprint check. This leaves two supported retry windows:

1. The target native mount commits. The select child exits before the outer mounted stamp. A recovery child validates the target and durably sets target_mount_recovered=True, then exits before restoring the previous selection. An owner then edits SOUL.md. Retrying recovery overwrites the edit and reports rolled_back.
2. The recovery child commits the previous native mount, then exits before the outer rolled_back stamp. An owner then edits SOUL.md. Retrying recovery remounts the previous installation, overwrites the edit, and reports rolled_back.

Proof: probe_recovery_retry.py uses real Bun mounting, real Hermes configuration validation, actual child os._exit calls, synthetic installed roots, and the production selection/native mount functions. Service callbacks are local records. The probe does not establish live gateway, dashboard, or Pulse acceptance.

Raw output is retained in recovery-retry-results.json, recovery-retry.stdout, and recovery-retry.stderr. The current-head checkpoint child exits 92; the current-head previous-remount child exits 91. In both cases, the outer state is rolling_back, target_mount_recovered is true, and the active inner mount is committed. Both retries return rolled_back, owner_edit_preserved is false, and service_events include start and verify. The stderr file is empty.

Provenance: Both cases also reproduce using the exact e933 installation_selection.py source, retained as e933_installation_selection.py, with current native helper behavior. This is a controlled selection-source substitution, not a full e933 installed-host run. The shared skipped callback and explicit previous remount are unchanged from e933, so the latest completed-file fix leaves the retry hole open. Base PR3 did not have this durable checkpoint; this specific checkpoint window follows the PR4 compensation flow.

P2: Mark a failed worker launch terminal when no selection transaction starts.

Source: lifeos_hook_bridge/dashboard/plugin_api.py lines 815-818, 839-849, 864-868, and 923-928.

The dashboard writes queued status before it invokes systemd-run. If systemd-run returns a nonzero status, the request returns HTTP 409 but leaves that queued job. An inactive unit and absent transaction journal then produce interrupted status. All later selection admission scans treat the job as pending. Recovery requires the absent transaction journal and returns HTTP 409. An ordinary failed launch therefore blocks further account selection indefinitely until manual state intervention.

Proof: probe_failed_launch.py creates supported named profiles with current owner bindings, selects a synthetic installed root, and invokes the production dashboard queue path. The local systemd-run transport exits 23; the local systemctl transport reports inactive and exits 3. The first return request fails with Could not start the LifeOS selection worker. The job contains queued status and no transaction journal. The dashboard observes interrupted status. The next return fails with the account pending-job message, and recovery fails with FileNotFoundError for transaction/journal.json. Full results are retained in failed-launch-results.json, failed-launch.stdout, and failed-launch.stderr. Stderr is empty. These are dashboard component checks with local transports, not live systemd acceptance.

Provenance: The queued-before-launch and missing-journal interrupted inference exist in e933 and base PR3. The latest changes add account locking but leave this failure classification intact. The new shared recovery authority rejects the missing journal before launch. In e933 the dashboard launch path can launch recovery without the journal, but the worker recovery eventually fails because it also needs that journal. This finding is inherited behavior in the adjacent status/admission paths, rather than a claim that the new lock causes it.

Bounded closure and verification:

The four selection test modules pass: 33 tests, 11 passing subtests, no skips, in 20.65 seconds. focused-tests.txt retains output and focused-tests.exit records zero. This review uses the four modules named in run_checks.sh. The earlier claimed 48-test verification includes additional evidence checks and is not the count from this review command.

The existing regressions establish closure of the three previously reported boundaries within their component scope. Recovery refuses a target owner edit before target_mount_recovered is recorded and refuses service restart. A dashboard with a stale startup root admits valid owner recovery after publication. Two real profile processes admit exactly one account selection job, and a worker waits on a held account lock before constructing its service controller. These tests do not cover the newly reproduced compensation retry windows or failed-launch status trap.

Authority inspection and passing regressions preserve current owner/profile refusal, journal profile binding, outside-journal root refusal, and legitimate selected/configuration roots drawn from the journal previous/target set. Lock acquisition follows profile, account, then program order for the worker; dashboard admission follows profile then account. The separate account coordination scope avoids the earlier profile-at-HOME lock collision. I found no additional concrete lock-order defect in this bounded scope.

The historical mount snapshot equals the exact e933 source byte for byte and has SHA-256 a1f8fb6c4ac728284e85dd05960fe35d1ebfaa747ee3f878fe0580af0a0d7857. The ledger changes only the path for that retained artifact, with its hash unchanged. tests/test_mount_transaction.py has no latest-fix diff. scripts/check_hook_evidence.py --require-complete passes with unchanged-artifact output, retained in evidence-check.txt. verification-provenance.json retains the exact head, snapshot comparison, hash, tracked-diff result, and exit codes. The historical snapshot handling is truthful within these checks.

The head remains e7c10d02f2e4385bcea76e9dc0880aabb962c3f3 during verification, and git diff --name-only is empty. No tracked implementation files, commits, pushes, external services, memory, or journal stores are changed.

Review limits: Synthetic fixture files, real Bun/Hermes native checks, real process death, real profile/account file locks, and local launcher/service recorders establish the stated component failures and closures. They do not establish live installed-host acceptance or production service behavior. I did not repeat the full release suite. The e933 retry control substitutes only the exact selection source into current native helpers. I did not run a complete base/e933 installed-host control for the inherited failed-launch classification, whose provenance is established by retained source excerpts.

Adrian's review should focus on preserving later edits on every compensation attempt, keeping deliberate explicit mounts usable, and ensuring an unsuccessful launch becomes terminal only when no child transaction starts. A launcher timeout or ambiguous outcome requires different treatment from the reproduced nonzero launch failure, because a worker might exist.
