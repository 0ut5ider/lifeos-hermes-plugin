Date: 2026-09-28
Agent role: Independent read-only parity risk reviewer
Question: What is the next highest-risk unverified parity behavior, what paired experiment settles it, and did the SessionEnd patch chain introduce obvious correctness or upgrade risks?
Model: GPT-6-Astra (inherited runtime model)

Reviewed revision: `43bb0f238c5718b68e4549db483c2a6a20c20798`.

The highest-priority next experiment is a permanent command approval followed by a changed LifeOS deny rule, with the identical command replayed through the real host. Source ordering suggests that a permanent Hermes allow can return before LifeOS command policy runs. This is a concrete source risk. This review did not reproduce an installed bypass and does not classify the behavior as a confirmed Claude/Hermes mismatch.

## Evidence and classification

1. `patches/hermes-command-policy.patch:248-264` places prepared-guard reuse, the existing yolo/off branch, and the existing permanent-allowlist return ahead of `_plugin_command_decision()`. The permanent allow branch explicitly returns `_approved()`. The later context patch changes the prepared key and plugin arguments, not that order (`patches/hermes-command-context.patch:157-170`). Searching the complete patch directory found no subsequent patch relocating the permanent allow branch. This is observed patch source evidence, not an observation of the installed runtime.
2. The bridge reads current policy when `command_approval()` actually runs, then rejects file and Bash denies before considering a PermissionRequest grant (`lifeos_hook_bridge/bridge.py:1395-1425`). That cannot protect an invocation which the host short-circuits before calling the bridge.
3. The existing dynamic-deny regression explicitly grants a session approval and then injects a plugin deny (`patches/hermes-command-policy.patch:181-197`). It does not test a permanent allow or an actual edited policy file. Mocked plugin results make this a useful unit assertion, not an end-to-end test of host policy delivery.
4. The current plan explicitly requires that an approval grant cannot override a later LifeOS deny (`docs/parity-resolution-plan.md:11`). Prior grants, permanent grants, policy edits, and unattended modes remain in scope (`docs/agents/2026-09-28-parity-inventory/parity-inventory.md:27`). The existing paired rewrite data limits its claim to final input and effects (`docs/parity/paired-permission-rewrites.json:3`). Complete approval traces and live gateway approval remain open (`docs/parity-resolution-plan.md:30-32`).

The same source order raises questions about unattended off/yolo runs. Their expected native behavior must be measured under equivalent Claude settings. Do not assume a parity defect simply because an explicitly disabled approval mode differs. A prepared guard is single-use and bound to command, backend, workspace, task, and call identity (`patches/hermes-command-context.patch:27-40`), so its risk is a policy change between preparation and execution, not unlimited cross-workspace reuse.

## Paired experiment

Use disposable local accounts or isolated configuration roots with pinned Claude Code 2.1.272 and the prepared Hermes/plugin revisions. Record exact revisions, patch hashes, effective settings, model and effort. Use the accepted private model mapping. Begin on local CLI transport to isolate policy behavior. Repeat the resulting confirmed scenario on the authorized test gateway before claiming gateway coverage.

1. Create a fixture `marker.txt` containing one synthetic line. Choose one exact benign Bash append command, for example `printf PARITY_APPEND >> /absolute/fixture/marker.txt`. Supply the same absolute fixture shape to both hosts and verify the actual model tool input before accepting each trial. Record initial file bytes and hashes.
2. Install passive PreToolUse, PermissionRequest, and PostToolUse recorders. Capture raw hook payloads, approval requests and choices, tool result, terminal output, and marker bytes. Passive recording must not grant or deny. Keep the installed LifeOS handlers active. Record Hermes hardline/user/guardian/Tirith outcomes separately if any fires.
3. In manual mode with no prior grant, request the command. Save the real approval UI and choose the permanent approval option for exactly that command. Confirm one append. Record the persisted rule and its scope. If a host has no equivalent permanent scope, report that fact instead of silently substituting a session grant.
4. Replay the identical command with unchanged policy. This establishes that the stored grant is actually used. A denied or failed control invalidates the trial.
5. Add an exact matching Bash deny to the disposable LifeOS settings source used by each host. Preserve the earlier allow. Verify the file contents and effective source identity. Replay the identical command without granting anything else. Observe whether the marker grows and whether the bridge/plugin policy event runs.
6. Repeat from fresh roots with a session approval, then with no prior grant. These controls distinguish permanent-allow precedence from a broken settings reload or an incorrect rule pattern. Run a separate fresh-process trial with the same conflicting saved allow and deny to distinguish reload behavior from permanent rule precedence.
7. Once this is settled, exercise a PermissionRequest rewrite into a newly denied target using the same capture. Confirm that final-target deny still blocks after prior approval. Treat it as a separate trial, because changing input and permission state at once makes a first failure harder to attribute.

Primary assertion: after the deny becomes effective, the marker must not change. Compare approval counts, hook order, matched policy source, effective input, and actual side effects. Normalize only timestamps, random IDs, and equivalent fixture root prefixes. Native denial plus Hermes execution confirms a parity mismatch. Both executing is a failure of the plan's declared deny invariant even if the pair matches. Both denying with different approval traces leaves timing parity open. A stronger Hermes safety denial is the documented accepted difference only when its actual verdict is captured.

A live Discord message is not part of this review's authorization. The primary agent must use an already authorized test transport or obtain message authorization before that repeat.

## SessionEnd patch chain

No definite new correctness defect was established by the source reviewed. The four patches are explicitly ordered after command rewrite in `scripts/prepare_sources.py:34-37`. Source preparation applies them to the pinned Hermes base, checks each patch, records SHA-256 hashes, and publishes only after both component trees prepare successfully (`scripts/prepare_sources.py:80-110`). This limits accidental textual drift. It does not prove runtime compatibility with an upgraded Hermes base.

Observed favorable details:

- Gateway resume finalizes only after `switch_session()` returns a new entry (`patches/hermes-session-reasons.patch:5-14`). A failed switch does not immediately finalize the current session.
- CLI resume notifies before changing `self.session_id` (`patches/hermes-session-reasons.patch:24-29`), and the final patch expands the guard to an existing old session ID (`patches/hermes-empty-session-resume.patch:5-12`).
- The empty clear patch supplies `self.session_id` when no agent exists and finalizes an empty session (`patches/hermes-empty-session-clear.patch:5-20`).
- Prompt exit carries the CLI session ID into cleanup when no active agent exists (`patches/hermes-prompt-exit-reason.patch:18-22,34-38`).
- The bridge maps clear, resume, and prompt exit explicitly and dispatches the reason as the matcher (`lifeos_hook_bridge/bridge.py:2019-2027`).

Remaining correctness risks are hypotheses requiring sequences, not more isolated field checks:

- Gateway finalization occurs after the session store switches, while the explicit ID still identifies the old session. The lifecycle implementation and installed handlers must use the supplied old identity for transcript and cleanup work. A callback that instead consults current session state could affect the resumed session. The patch test replaces `_finalize_session_off_loop` with AsyncMock (`patches/hermes-session-reasons.patch:71-76`), so it cannot establish those effects.
- Cleanup and boundary helpers prefer the agent's session ID whenever an agent exists (`patches/hermes-session-reasons.patch:46`; `patches/hermes-prompt-exit-reason.patch:19`). Correctness depends on the full host updating or replacing that agent after resume/new. The isolated no-agent tests do not prove this across a completed turn followed by multiple boundaries.
- Gateway finalization suppresses exceptions (`patches/hermes-session-reasons.patch:11`). A successful resume UI can therefore coexist with missing SessionEnd effects. Capture hook completion and handler effects, not just command success.
- `HookBridge.session_end()` immediately removes async results, stops the watchdog, and clears project/session state (`lifeos_hook_bridge/bridge.py:2028-2044`). Duplicate or misidentified finalization is consequential. The inspected reason tests dispatch independent synthetic session IDs, not a complete resume/clear/exit lifecycle (`tests/test_bridge.py:193-209`).

Concrete lifecycle follow-up: on both hosts, create sessions A and B with distinct synthetic transcript markers and real handler state, complete a turn in A, resume B, complete a turn in B, clear to C, then exit C. Assert exactly one SessionEnd for each actual boundary, correct old session ID, reason, transcript ownership, and handler side effects. Include failed resume and same-session resume controls with no extra finalization. Repeat with empty A. On Hermes, run the gateway resume portion through a real authorized gateway because CLI behavior does not prove gateway state ownership.

## Upgrade and evidence limits

`tests/test_prepare_sources.py:44-67` gates real patch application behind external repository paths. Its assertions include 16 Hermes patches and the final empty-session-resume patch, but a run with absent source repositories skips that gate. A fresh prepared-tree run must execute the host lifecycle tests as well as patch application before changing the compatibility manifest. The chain changes several shared call sites and the `_run_cleanup` signature, so textual applicability alone is insufficient.

The historical inventory's patch manifest predates the four SessionEnd patches and command rewrite. It is accurately dated evidence, not the current deployable manifest. Use the new preparation output and its hashes for update rehearsal. Coordinated Hermes/plugin rollback remains explicitly open (`docs/parity-resolution-plan.md:32`), so no safe update claim follows from these review findings.

This review read local source and existing evidence. It did not run tests, connect to remote machines, inspect a live Hermes checkout, deploy, push, or modify implementation. No memory or journal tools were used because this was a delegated review. Raw numbered source excerpts are saved in `source-hits.txt`. Only this report directory was created.
