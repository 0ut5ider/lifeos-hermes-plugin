Date: 2026-10-13
Role: Independent focused correctness reviewer
Question: Do the PR18 preparation and first-install service fixes preserve owner governance, safe publication, and recovery?
Model: gpt-6.1-sol, high reasoning effort

Final reviewed head: db48eb5beb92b8cec91a37e4e10e3ee186e24e77
Reviewed code identities: reviewed-file-identities.json
Base: origin/main 958d122a491ddead7c19a5f215494f0422c4b5d6

## Result

No additional concrete code defect remains in the final inspected preparation and managed-dashboard fixes. The first-round findings are closed for the bounded managed-dashboard installation mode. Release qualification remains pending. These component and service controls do not establish a successful browser installation followed by an update.

Foreground dashboards remain unsupported by this implementation and require a clear preflight refusal. Abrupt publication exits can require operator recovery. The public recovery command is not available at every possible manager-directory swap point. Those limits must remain visible in the release evidence and user guidance.

## Findings resolved during this review

### Live synchronous preparation was incorrectly classified as interrupted

The inherited-lock correction initially treated a live synchronous CLI prepare() as abandoned because that path did not publish a worker identity or retain the UI preparation lease. This affected the requested conversational preparation path.

The primary agent publishes the current process PID/start stamp before the synchronous preparing state. The final live_boundary_probes.py runs the real prepare() in a child process paused at a bounded synthetic download boundary. Its real status() reports preparing while the child remains alive. This probe isolates a component boundary. It is not a fake end-to-end acceptance.

### Process selection matched unrelated dashboard arguments

The initial procfs helper used a function that matches any argument token named dashboard or serve. The corrected helper first applies native canonical Hermes command recognition. The final live probe starts an unrelated Python sleep process with the argument dashboard and the selected HERMES_HOME. The writer check does not refuse it.

### Empty preparation directories hid every operation

A launch interruption before status.json publication left an operation directory that made the entire status listing fail. The corrected reader classifies only a request-free, plan-free incomplete job through the same liveness and lease logic. The new test preserves visibility of another operation and distinguishes a live worker receipt from an abandoned directory.

### Accepted service definitions did not match the fresh local-unit plan

The initial fresh preview accepted a global/root dashboard definition through the general service reader. The local plan could then create a user definition that replaced the accepted binding after reload. The corrected preview requires the exact local account dashboard FragmentPath and refuses drop-ins.

The initial gateway/Pulse preview did not bind ExecStart. The corrected preview requires the fixed account executable and the intended gateway or Pulse invocation. This prevents later updates from replacing a custom account executable that an unsupported unit happened to reference.

## Original findings

The preparation launch interruption before worker identity publication is closed. status() now checks the private inherited preparation lease when an identity is missing or dead. It does not classify an active launch as abandoned. When the process and lease disappear, the operation becomes preparation_interrupted in the returned status, so the UI can offer a new preparation.

The missing first-install service prerequisite is closed for the managed-dashboard path. The fresh plan includes all three account-owned unit files in ProgramTransaction. Existing local bytes are retained. New definitions remain inactive and disabled. Fresh preview checks the real dashboard, and the worker uses a separate systemd unit because the service plan is present. The dashboard-only first-install barrier uses a fixed separate journal and allows the absent native root. It drains and restarts the existing dashboard while default callers retain the exact three-role behavior.

Post-publication verification reloads the user manager and performs the real full ProfileServices preview. Fresh recovery distinguishes a missing first-install service journal from a journal that needs quiescence. Native mount recovery now occurs after the dashboard drain. Program resume preserves later target edits by refusal. The final reviewed head does not contain the exploratory pre-quiesce reload helper; that helper was removed after the identical-republication probe disproved its hypothesized necessity.

## Caught errors and abrupt exits

Completing only the already admitted program phase on a caught error is preferable to deleting or rolling back newly published user and native trees. The helper resumes programs only after native initialization reaches its recorded complete state. ProgramTransaction.resume validates the before/after artifacts and staged sources. The worker verifies the runtime and complete service bindings before it resumes the dashboard. If initialization has not completed, it requires the untouched prepared program state before resuming the original dashboard.

This behavior can return a usable release-manager page after an ordinary caught error. It does not claim that native mounting succeeded. The operation remains recovery_required. Invalid configuration, source tampering, later target edits, or an unusable runtime can prevent the dashboard return. Keeping the service stopped in those cases preserves the refusal rather than bypassing verification.

Publishing the manager last would only reduce one failure window. It would not eliminate the stopped-dashboard or changed-launcher recovery problem. The existing admitted-phase strategy is the better narrow correction.

An abrupt process exit between retaining and publishing the manager directory removes the installed plugin entry point. Ordinary hermes lifeos-release recover cannot register while that directory is absent. The sealed job worker and retained manager provide operator recovery material, but invoking them is a different path that needs measured acceptance. A programs-published interruption keeps the manager available and can test the ordinary CLI recovery command. Do not combine those cases into one public-command recovery claim.

## Correction to the reload hypothesis

I initially inferred that byte-identical unit republication would set NeedDaemonReload=yes and block quiesce. The actual isolated service probe observes NeedDaemonReload=no and successful quiesce before reload. That inference is not a confirmed defect. unit-reload-probe.json preserves the measured result. The primary agent was told this correction immediately.

New unit definitions still require daemon-reload before the final three-role preview. The final worker performs that reload in post-publication verification. The exploratory recovery reload helper was removed after the actual probe disproved the identical-republication hypothesis.

## Controls run by this reviewer

The final selected Python run passes 32 tests in 5.494 seconds. It uses -B and ResourceWarning as an error. It covers source validation, isolated bytecode behavior, lock and interruption handling, live synchronous preparation, empty-directory status, configuration preservation, unit-file transactions, command arguments, native owner sessions, current revocation, foreign origins, and bounded request rejection. There are no skips or failures.

All 14 actual temporary user-service tests pass in 17.436 seconds. The new first-install test drains only the dashboard while the native root is absent, preserves gateway/Pulse processes, creates the native root, and resumes the same dashboard binding. Existing three-role tests continue to pass. Temporary test units are stopped and removed by their fixture cleanup. No guest or production service is changed.

All three Node UI contract tests pass. They use a synthetic SDK and are not browser acceptance. node.stderr is empty.

The final live boundary probes pass. They confirm real synchronous process liveness and corrected selection of unrelated process arguments. The child processes are bounded and terminated after each probe. No active installation is changed.

Unittest's normal verbose report appears in the captured stderr files. The selected stdout files are empty. No ResourceWarning or unexpected diagnostic occurs. The first boundary-probe attempt asserted the old defect after the primary had already corrected it. Its AssertionError is preserved in initial-live-boundary-probes.stderr. The corrected expectation passes with empty live-boundary-probes.stderr.

## Qualification still required

1. Actual browser first installation on the managed stock guest, with a surviving detached worker and a restarted dashboard.
2. A direct subsequent user update on that same installation without operator-created service prerequisites between the two actions.
3. Actual caught-error dashboard return and recovery.
4. Actual abrupt-exit recovery, with public CLI and retained-worker/operator paths identified separately.
5. Preservation of later edits, inactive gateway/Pulse decisions, model mapping, and user data.
6. Foreground and unsupported custom-unit refusal evidence.
7. Full package, certificate, and release verification after the final source changes.

I did not publish a release, mutate a guest, change product source, commit, push, or call memory tools. The broader daily deployment remains outside this review.

## Raw data

- final-pr.diff: final committed PR diff.
- working-tree.diff: initial working-tree service changes.
- final-followup.diff: final follow-up diff snapshot.
- reviewed-file-identities.json: exact reviewed source hashes and final head.
- release_services-reviewed.py: initial service helper snapshot.
- final-head.stdout and final-head.stderr: final 32-test component run.
- python.stdout/python.stderr and python-final.stdout/python-final.stderr: intermediate component runs.
- final-followup.stdout/final-followup.stderr: latest preparation/configuration repeat.
- services.stdout/services.stderr and services/: actual 14-test service run and recorded receipts.
- node.stdout/node.stderr: three UI contract controls.
- live_boundary_probes.py and live-boundary-probes.json: final actual process/status component probes.
- initial-live-boundary-probes.stderr: preserved assertion against the already corrected preparation behavior.
- unit_reload_probe.py and unit-reload-probe.json: measured correction to the daemon-reload hypothesis.

## Prose correction recorded during round 3

The original result paragraph described an exploratory pre-quiesce reload helper as present in the final head. That description was incorrect. The saved source hashes and final diff represent the actual code. The paragraph above now describes that code, and the original report is retained in pr18-release-ui-review-2-before-prose-correction.md.
