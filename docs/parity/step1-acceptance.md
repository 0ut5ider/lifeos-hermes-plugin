# Step 1 acceptance checklist

Date: 2026-10-06. This checklist implements the nine-package plan accepted by Adrian. 78 scenarios have verified evidence. The remaining scenarios stay open until their required branches are measured. No scenario status is inferred from registration dispatch.

The development target is `192.168.8.252`. Private FlashNext effort mapping stays unchanged. Production receives one combined release. Actual Discord delivery stays a named release acceptance requirement. Native web and batch dispatch limits remain separate from functional handler evidence.

The [machine-readable checklist](step1-acceptance.json) binds the registration inventory. The [effect ledger](handler-effects.json) retains earlier selected passing cases. The final gate must validate both records.

## Requirements

### context-reduction (package 2)

Registrations: PreToolUse.1.1.

- [x] `context-reduction-01`: Installed RTK rewrites git status and preserves other input fields.
- [x] `context-reduction-02`: Installed RTK rewrites supported gh metadata commands.
- [x] `context-reduction-03`: Environment prefixes, git flags, and command chains retain supported command semantics.
- [x] `context-reduction-04`: Already rewritten commands, heredocs, multiline scripts, and unsupported reads stay unchanged.
- [x] `context-reduction-05`: A later deny still blocks the rewritten command.

### pulse-skill (package 2)

Registrations: PreToolUse.2.1.

- [x] `pulse-skill-01`: Valid, unknown, disabled, and blocked skills produce the real daemon policy decisions.
- [x] `pulse-skill-02`: Malformed payload and unavailable daemon preserve the documented failure policy.

### pulse-agent (package 5)

Registrations: PreToolUse.3.1.

- [x] `pulse-agent-01`: Foreground, background, fast-model, and timing agents receive their applicable policy.
- [x] `pulse-agent-02`: The live gateway delivers asynchronous policy feedback to the parent.
- [x] `pulse-agent-03`: Unavailable daemon, malformed decision, restart denial, and watchdog cleanup preserve their policy.

### agent-lifecycle (package 5)

Registrations: PreToolUse.3.2, PostToolUse.1.1.

- [x] `agent-lifecycle-01`: Inherited and explicit tier metadata describe the served model.
- [x] `agent-lifecycle-02`: Background success and failure correlate one start with one completion.
- [x] `agent-lifecycle-03`: Concurrent children retain separate starts, results, and parent delivery.
- [x] `agent-lifecycle-04`: Cancellation and parent shutdown clean up watchdogs and incomplete child state.
- [x] `agent-lifecycle-05`: Child dispatch does not run main-session lifecycle hooks.

### question-state (package 5)

Registrations: PreToolUse.4.1, PostToolUse.6.1, Stop.1.2.

- [x] `question-state-01`: Single and batch questions set waiting state and restore the prior state after an answer.
- [x] `question-state-02`: Timeout, cancellation, duplicate answer, and late answer preserve first resolution.
- [x] `question-state-03`: Session finalization restores or removes applicable transient terminal state.
- [x] `question-state-04`: Desktop and remote channels apply their documented terminal isolation.

### nested-pre-guards (package 2)

Registrations: PreToolUse.5.1.

- [x] `nested-pre-guards-01`: System content Write, Edit, and batch deny identifying content; user and outside-tree content stay allowed.
- [x] `nested-pre-guards-02`: Stale whole-file ISA writes deny after an external change; fresh views and supported edits pass.
- [x] `nested-pre-guards-03`: Unsafe plutil extraction denies; the explicit output form passes.
- [x] `nested-pre-guards-04`: Remote and headless speaker calls deny; health and explicitly silent calls pass.
- [x] `nested-pre-guards-05`: Public push policy tests blocked, admitted, bypass, scan failure, and private destination cases on disposable repositories.
- [x] `nested-pre-guards-06`: Raw Gmail and SES sends deny; skill-routed and read-only forms pass without external delivery.
- [x] `nested-pre-guards-07`: Tier-2 classified egress tests allowed content, above-ceiling content, and classification failure.
- [x] `nested-pre-guards-08`: Inline system writes through redirect, tee, copy, sed, and script forms preserve target classification.
- [x] `nested-pre-guards-09`: Malformed dispatcher input and isolated guard failure preserve each documented failure policy.

### external-safety (package 7)

Registrations: PostToolUse.2.1, PostToolUse.3.1, PostToolUse.4.1, PostToolUse.5.1.

- [ ] `external-safety-01`: Ordinary and injection-shaped web, MCP, and discovery results reach the next request with the correct Safety context.
- [ ] `external-safety-02`: Supported string, object, content-block, empty, failure, and partial-success results retain their actual data.
- [ ] `external-safety-03`: Neutral nonexternal MCP results retain their documented treatment.
- [ ] `external-safety-04`: Native ToolSearch continuation records the private gateway tool-reference limitation.

### permission-safety (package 2)

Registrations: PermissionRequest.1.1, PermissionRequest.2.1.

- [x] `permission-safety-01`: Actual Bash, Write, Edit, batch, and MCP targets receive allow, ask, or deny decisions.
- [x] `permission-safety-02`: Interactive approval permits the reviewed operation; cancellation and unattended mode do not grant approval.
- [x] `permission-safety-03`: Prior approval, policy changes, managed policy, and trusted-project scope preserve denial precedence.
- [x] `permission-safety-04`: Compound commands, wrappers, redirects, path aliases, and remote namespaces preserve the supported rule contract.
- [x] `permission-safety-05`: Malformed managed policy follows the installed review path without granting execution.

### isa-views (package 3)

Registrations: PostToolUse.7.1, PostToolUse.8.2, PostToolUse.9.2, PostToolUse.10.2.

- [x] `isa-views-01`: Read and applied Write, Edit, and batch updates record the actual local file view.
- [x] `isa-views-02`: External mutation followed by a full-file write uses the changed file for the stale-write decision.
- [x] `isa-views-03`: SSH and Docker views identify the actual backend and file.
- [x] `isa-views-04`: Failed and partial operations record only the applied file views.

### isa-sync (package 3)

Registrations: PostToolUse.8.1, PostToolUse.9.1, PostToolUse.10.1.

- [x] `isa-sync-01`: New ISA, phase change, completion, and resumed work synchronize registry and render state.
- [x] `isa-sync-02`: Work-tree, skill-owned, and outside-tree ISAs follow their applicable synchronization rules.
- [x] `isa-sync-03`: Failed and partial operations synchronize only applied changes.

### checkpoints (package 3)

Registrations: PostToolUse.8.3, PostToolUse.9.3, PostToolUse.10.3.

- [x] `checkpoints-01`: Verified criterion closure creates one retrievable checkpoint in the admitted repository.
- [x] `checkpoints-02`: Repeated closure produces no duplicate checkpoint; multiple new closures retain criterion identity.
- [x] `checkpoints-03`: Skill-owned ISAs and repository boundaries preserve the checkpoint contract.
- [x] `checkpoints-04`: Git failure and partial patch do not falsely record a completed checkpoint.

### evaluation (package 3)

Registrations: PostToolUse.8.4, PostToolUse.9.4, PostToolUse.10.4.

- [x] `evaluation-01`: Actual sentinel Write, Edit, and batch operations launch the configured real evaluation runner.
- [x] `evaluation-02`: Completed and failed evaluations publish their actual result and exit status.
- [x] `evaluation-03`: Recent debounce, concurrent edits, absent runner, and nonsentinel changes preserve their applicable state.
- [x] `evaluation-04`: The actual Hermes file tool completes the measured CLAUDE.md sentinel write.

### atlas (package 3)

Registrations: PostToolUse.8.5, PostToolUse.9.5, PostToolUse.10.5, PostToolUse.13.1.

- [x] `atlas-01`: Projects, gear, inventory, and service-unit changes emit the correct event for each applicable file tool.
- [x] `atlas-02`: Supported shell mutation patterns emit their systemd, DNS, and Cloudflare hints.
- [x] `atlas-03`: Read-only, unrelated, failed, and unapplied partial changes do not emit mutation events.

### knowledge-writes (package 3)

Registrations: PostToolUse.8.6, PostToolUse.9.6, PostToolUse.10.6.

- [x] `knowledge-writes-01`: Valid notes, invalid notes, index files, and outside-tree changes follow the knowledge-write contract.
- [x] `knowledge-writes-02`: Write, Edit, and batch warnings reach the model for the actual applied changes.

### complexity (package 3)

Registrations: PostToolUse.8.7, PostToolUse.9.7, PostToolUse.10.7.

- [x] `complexity-01`: Write, Edit, and batch source changes accumulate actual line and dependency counts.
- [x] `complexity-02`: Below, at, and above the configured budget produce the specified warning behavior.
- [x] `complexity-03`: Partial and failed changes add only applied work; repeated events follow the documented counting contract.

### event-audit (package 4)

Registrations: PostToolUse.11.1, PostToolUseFailure.1.1, ConfigChange.1.1, StopFailure.1.1.

- [x] `event-audit-01`: Skill execution, file activity, heartbeat, and work reconciliation record actual tool facts.
- [x] `event-audit-02`: Failure rows for shell, file, MCP, and terminal model errors retain the actual error and truncation policy.
- [x] `event-audit-03`: External configuration first observation, change, no change, deletion, and malformed source preserve source-specific audit state.
- [x] `event-audit-04`: Asynchronous logging during interruption and parallel activity preserves complete rows.

### tool-observers (package 4)

Registrations: PostToolUse.12.1, PostToolUse.12.2, PostToolUseFailure.3.1.

- [x] `tool-observers-01`: Exact repeats through the full observer produce the expected alert.
- [x] `tool-observers-02`: Oscillation, repeated failure, cooldown, and parallel activity preserve loop history and thresholds.
- [x] `tool-observers-03`: System-change observations use actual tool results and transcript state.

### work-learning (package 6)

Registrations: SessionEnd.1.1.

- [x] `work-learning-01`: Eligible completed work produces learning; ineligible, incomplete, and repeated sessions preserve eligibility rules.
- [x] `work-learning-02`: Concurrent learning and cleanup in both scheduling orders preserve the durable result.

### session-cleanup (package 6)

Registrations: SessionEnd.1.2.

- [x] `session-cleanup-01`: Normal, resumed, failed, and interrupted sessions remove only applicable transient work.
- [x] `session-cleanup-02`: Concurrent sessions retain each other's active state and durable results.

### usage-counts (package 6)

Registrations: SessionEnd.1.3.

- [ ] `usage-counts-01`: Absent, invalid, and expired OAuth credentials preserve the documented usage-cache behavior.
- [ ] `usage-counts-02`: Network failure preserves the prior valid usage state.
- [ ] `usage-counts-03`: An authenticated real usage refresh is tested or recorded as an explicit unavailable enabled-feature control.

### memory-health (package 6)

Registrations: SessionEnd.1.4, Stop.2.1.

- [ ] `memory-health-01`: Healthy, warning, and unavailable-tool states produce the applicable report at both registered events.
- [ ] `memory-health-02`: Synthetic managed memory enforces caller and destination admission.
- [ ] `memory-health-03`: Pinned asynchronous execution, interruption, and subsequent turn delivery preserve the report.

### doc-integrity (package 6)

Registrations: SessionEnd.1.5.

- [ ] `doc-integrity-01`: Supported documentation handlers detect changed and stale documentation.
- [ ] `doc-integrity-02`: Inference-dependent branches retain actual child routing and results.
- [ ] `doc-integrity-03`: Concurrent lifecycle effects preserve documentation state.

### system-integrity (package 6)

Registrations: SessionEnd.1.6.

- [ ] `system-integrity-01`: Unchanged, changed, missing, and malformed baseline cases publish the applicable integrity result.
- [ ] `system-integrity-02`: Interruption preserves prior valid integrity state.

### prompt-processing (package 6)

Registrations: UserPromptSubmit.1.1.

- [ ] `prompt-processing-01`: First and subsequent prompts create or retain the correct session name and work state.
- [ ] `prompt-processing-02`: Actual title inference success and failure preserve the naming contract.
- [ ] `prompt-processing-03`: Restart and concurrent prompts preserve session identity.

### satisfaction (package 6)

Registrations: UserPromptSubmit.2.1.

- [ ] `satisfaction-01`: Supported ratings, praise, directives, complaints, and numeric work text follow feedback eligibility.
- [ ] `satisfaction-02`: Code/system exclusions and absent context avoid false feedback capture.
- [ ] `satisfaction-03`: Very low ratings run actual FailureCapture and retain applicable learning.
- [ ] `satisfaction-04`: ISA pulses, write failure, asynchronous interruption, and rapid shutdown preserve feedback state.

### reminders (package 6)

Registrations: UserPromptSubmit.3.1.

- [ ] `reminders-01`: Disabled, not-due, due, and already-delivered reminders preserve scheduling and delivery policy.
- [ ] `reminders-02`: Enabled supported reminder routing uses the configured test destination without duplicate operation.
- [ ] `reminders-03`: Interruption and unavailable destination preserve retry state.

### version-drift (package 5)

Registrations: UserPromptSubmit.4.1.

- [x] `version-drift-01`: Changed-file count, tag age, no tag, bump in flight, and recent warning obey the thresholds.
- [x] `version-drift-02`: The exact nag interval boundary and next-turn asynchronous delivery preserve warning policy.
- [x] `version-drift-03`: Interrupted execution preserves prior valid warning state.

### memory-turn (package 6)

Registrations: UserPromptSubmit.5.1.

- [ ] `memory-turn-01`: First, subsequent, and resumed turns supply only admitted synthetic memory.
- [ ] `memory-turn-02`: Unavailable memory, revoked caller, and changed destination do not expose prohibited context.
- [ ] `memory-turn-03`: Interruption preserves turn injection bookkeeping.

### drift-reminder (package 6)

Registrations: UserPromptSubmit.6.1.

- [ ] `drift-reminder-01`: Code exclusions, repeated prompts, and the exact staleness boundary preserve the line budget.
- [ ] `drift-reminder-02`: Malformed input or state and write failure preserve the documented failure behavior.
- [ ] `drift-reminder-03`: Synthetic managed source and destination enforce admission.

### algorithm-nudge (package 6)

Registrations: UserPromptSubmit.7.1, PostToolUseFailure.2.1.

- [ ] `algorithm-nudge-01`: Initial, later, and late-ISA turns emit the applicable capability and algorithm nudge.
- [ ] `algorithm-nudge-02`: Actual tool failure, absent state, and malformed state preserve counters and output.
- [ ] `algorithm-nudge-03`: Restart and interruption preserve valid nudge state.

### time-context (package 5)

Registrations: UserPromptSubmit.8.1.

- [x] `time-context-01`: Valid UTC, owner timezone, and invalid timezone follow the clock contract.
- [x] `time-context-02`: Pinned asynchronous output reaches the next turn without duplicated stale clock context.
- [ ] `time-context-03`: Interruption and synthetic managed source preserve admission and delivery policy.

### model-rung (package 6)

Registrations: UserPromptSubmit.9.1.

- [ ] `model-rung-01`: Actual served model and effort carriers produce the applicable rung guidance.
- [ ] `model-rung-02`: Inherited, explicit, absent, and malformed carriers preserve the accepted tier mapping.
- [ ] `model-rung-03`: Repeated turns and child requests retain the correct model context.

### task-governance (package 4)

Registrations: TaskCreated.1.1.

- [x] `task-governance-01`: Allowed and rejected task descriptions preserve quality rules.
- [x] `task-governance-02`: The 50-task boundary and kanban task kinds follow their distinct rules.
- [x] `task-governance-03`: Delegated child tasks use the correct session count and governance.

### hook-healer (package 6)

Registrations: SessionStart.1.1.

- [ ] `hook-healer-01`: Actual interpreter and executable permission repairs affect only registered installed hooks.
- [ ] `hook-healer-02`: Already valid, missing, and unsupported interpreter cases preserve the documented repair policy.

### kitty-environment (package 6)

Registrations: SessionStart.1.2.

- [ ] `kitty-environment-01`: Desktop persistence, absent terminal, and subagent startup follow native terminal rules.
- [ ] `kitty-environment-02`: Remote startup preserves the accepted isolation from native Kitty files.

### load-context (package 6)

Registrations: SessionStart.1.3.

- [ ] `load-context-01`: Enabled, disabled, missing, and synthetic managed sources retain identity and admission policy.
- [ ] `load-context-02`: Active work and resumed sessions supply applicable context.
- [ ] `load-context-03`: Actual model requests and generated user delivery preserve the admitted context boundary.

### freshness (package 6)

Registrations: SessionStart.1.4.

- [ ] `freshness-01`: Complete installed tree, stale cache, and missing source produce the applicable freshness result.
- [ ] `freshness-02`: Concurrent startup and interrupted refresh preserve valid cache state.

### settings-merge (package 6)

Registrations: SessionStart.1.5.

- [ ] `settings-merge-01`: System and user merge, direct edit backport, and settings deletion preserve source ownership.
- [ ] `settings-merge-02`: Concurrent edits and malformed settings preserve atomic output and the configured merge policies.

### response-cache (package 6)

Registrations: Stop.1.1.

- [ ] `response-cache-01`: Absent and prior cache, short and long response, and repeated Stop retain the delivered final response with the exact limit.
- [ ] `response-cache-02`: Interrupted completion does not publish an undelivered response as a completed answer.

### voice-completion (package 6)

Registrations: Stop.1.3.

- [ ] `voice-completion-01`: Desktop, remote, headless, disabled, and malformed completion follow the configured notification policy.
- [ ] `voice-completion-02`: Interruption and repeated Stop preserve applicable final voice state.

### isa-render (package 6)

Registrations: Stop.1.4.

- [ ] `isa-render-01`: Absent, authored, missing-document, completed, resumed, and existing-page cases preserve native rendering.
- [ ] `isa-render-02`: Newer-page, spawn failure, interruption, and concurrent render follow the freshness contract.

### spend-audit (package 6)

Registrations: Stop.1.5.

- [ ] `spend-audit-01`: Below, at, and above spending thresholds use actual recorded costs and policy.
- [ ] `spend-audit-02`: Missing and malformed usage, repeated Stop, and interrupted update preserve valid audit state.

### stop-gates (package 6)

Registrations: Stop.1.6.

- [ ] `stop-gates-01`: Required format, verification, writing, stale-ISA, and structural gates return the specified continuation or block.
- [ ] `stop-gates-02`: Satisfied gates permit completion through the actual final transcript.
- [ ] `stop-gates-03`: Repeated gate feedback and interruption preserve continuation state.

### memory-review (package 6)

Registrations: Stop.1.7.

- [ ] `memory-review-01`: Eligible review uses actual inference and records proposals without automatic approval.
- [ ] `memory-review-02`: Ineligible, debounce, unavailable inference, and revoked synthetic memory preserve review policy.
- [ ] `memory-review-03`: Concurrent or interrupted review does not duplicate publication.

### event-contract (package 2)

Registrations: PreToolUse.1.1, PreToolUse.2.1, PreToolUse.3.1, PreToolUse.3.2, PreToolUse.4.1, PreToolUse.5.1, PostToolUse.1.1, PostToolUse.2.1, PostToolUse.3.1, PostToolUse.4.1, PostToolUse.5.1, PostToolUse.6.1, PostToolUse.7.1, PostToolUse.8.1, PostToolUse.8.2, PostToolUse.8.3, PostToolUse.8.4, PostToolUse.8.5, PostToolUse.8.6, PostToolUse.8.7, PostToolUse.9.1, PostToolUse.9.2, PostToolUse.9.3, PostToolUse.9.4, PostToolUse.9.5, PostToolUse.9.6, PostToolUse.9.7, PostToolUse.10.1, PostToolUse.10.2, PostToolUse.10.3, PostToolUse.10.4, PostToolUse.10.5, PostToolUse.10.6, PostToolUse.10.7, PostToolUse.11.1, PostToolUse.12.1, PostToolUse.12.2, PostToolUse.13.1, SessionEnd.1.1, SessionEnd.1.2, SessionEnd.1.3, SessionEnd.1.4, SessionEnd.1.5, SessionEnd.1.6, UserPromptSubmit.1.1, UserPromptSubmit.2.1, UserPromptSubmit.3.1, UserPromptSubmit.4.1, UserPromptSubmit.5.1, UserPromptSubmit.6.1, UserPromptSubmit.7.1, UserPromptSubmit.8.1, UserPromptSubmit.9.1, PostToolUseFailure.1.1, PostToolUseFailure.2.1, PostToolUseFailure.3.1, TaskCreated.1.1, ConfigChange.1.1, SessionStart.1.1, SessionStart.1.2, SessionStart.1.3, SessionStart.1.4, SessionStart.1.5, Stop.1.1, Stop.1.2, Stop.1.3, Stop.1.4, Stop.1.5, Stop.1.6, Stop.1.7, Stop.2.1, StopFailure.1.1, PermissionRequest.1.1, PermissionRequest.2.1.

- [x] `event-contract-01`: SessionStart source matchers and SessionEnd reason matchers select the correct installed hooks.
- [x] `event-contract-02`: Changed inputs, ask decisions, hook failures, timeout, and asynchronous hook settings preserve the event contract.

### control-limits (package 7)

Registrations: PreToolUse.1.1, PreToolUse.2.1, PreToolUse.3.1, PreToolUse.3.2, PreToolUse.4.1, PreToolUse.5.1, PostToolUse.1.1, PostToolUse.2.1, PostToolUse.3.1, PostToolUse.4.1, PostToolUse.5.1, PostToolUse.6.1, PostToolUse.7.1, PostToolUse.8.1, PostToolUse.8.2, PostToolUse.8.3, PostToolUse.8.4, PostToolUse.8.5, PostToolUse.8.6, PostToolUse.8.7, PostToolUse.9.1, PostToolUse.9.2, PostToolUse.9.3, PostToolUse.9.4, PostToolUse.9.5, PostToolUse.9.6, PostToolUse.9.7, PostToolUse.10.1, PostToolUse.10.2, PostToolUse.10.3, PostToolUse.10.4, PostToolUse.10.5, PostToolUse.10.6, PostToolUse.10.7, PostToolUse.11.1, PostToolUse.12.1, PostToolUse.12.2, PostToolUse.13.1, SessionEnd.1.1, SessionEnd.1.2, SessionEnd.1.3, SessionEnd.1.4, SessionEnd.1.5, SessionEnd.1.6, UserPromptSubmit.1.1, UserPromptSubmit.2.1, UserPromptSubmit.3.1, UserPromptSubmit.4.1, UserPromptSubmit.5.1, UserPromptSubmit.6.1, UserPromptSubmit.7.1, UserPromptSubmit.8.1, UserPromptSubmit.9.1, PostToolUseFailure.1.1, PostToolUseFailure.2.1, PostToolUseFailure.3.1, TaskCreated.1.1, ConfigChange.1.1, SessionStart.1.1, SessionStart.1.2, SessionStart.1.3, SessionStart.1.4, SessionStart.1.5, Stop.1.1, Stop.1.2, Stop.1.3, Stop.1.4, Stop.1.5, Stop.1.6, Stop.1.7, Stop.2.1, StopFailure.1.1, PermissionRequest.1.1, PermissionRequest.2.1.

- [ ] `control-limits-01`: WebFetch, WebSearch, and MultiEdit retain measured native CLI limitations and expanded Hermes functional evidence.
- [ ] `control-limits-02`: Combined output, checkpoint subject, Kitty isolation, private routing, and other intentional changes retain explicit accepted differences.

### installed-groups (package 8)

Registrations: PreToolUse.1.1, PreToolUse.2.1, PreToolUse.3.1, PreToolUse.3.2, PreToolUse.4.1, PreToolUse.5.1, PostToolUse.1.1, PostToolUse.2.1, PostToolUse.3.1, PostToolUse.4.1, PostToolUse.5.1, PostToolUse.6.1, PostToolUse.7.1, PostToolUse.8.1, PostToolUse.8.2, PostToolUse.8.3, PostToolUse.8.4, PostToolUse.8.5, PostToolUse.8.6, PostToolUse.8.7, PostToolUse.9.1, PostToolUse.9.2, PostToolUse.9.3, PostToolUse.9.4, PostToolUse.9.5, PostToolUse.9.6, PostToolUse.9.7, PostToolUse.10.1, PostToolUse.10.2, PostToolUse.10.3, PostToolUse.10.4, PostToolUse.10.5, PostToolUse.10.6, PostToolUse.10.7, PostToolUse.11.1, PostToolUse.12.1, PostToolUse.12.2, PostToolUse.13.1, SessionEnd.1.1, SessionEnd.1.2, SessionEnd.1.3, SessionEnd.1.4, SessionEnd.1.5, SessionEnd.1.6, UserPromptSubmit.1.1, UserPromptSubmit.2.1, UserPromptSubmit.3.1, UserPromptSubmit.4.1, UserPromptSubmit.5.1, UserPromptSubmit.6.1, UserPromptSubmit.7.1, UserPromptSubmit.8.1, UserPromptSubmit.9.1, PostToolUseFailure.1.1, PostToolUseFailure.2.1, PostToolUseFailure.3.1, TaskCreated.1.1, ConfigChange.1.1, SessionStart.1.1, SessionStart.1.2, SessionStart.1.3, SessionStart.1.4, SessionStart.1.5, Stop.1.1, Stop.1.2, Stop.1.3, Stop.1.4, Stop.1.5, Stop.1.6, Stop.1.7, Stop.2.1, StopFailure.1.1, PermissionRequest.1.1, PermissionRequest.2.1.

- [ ] `installed-groups-01`: Complete startup and prompt groups run together in normal and resumed sessions.
- [ ] `installed-groups-02`: Complete pre-tool, permission, success, and failure groups preserve ordering and actual targets.
- [ ] `installed-groups-03`: Complete Stop and SessionEnd groups preserve delivery, durable learning, and transient cleanup.
- [ ] `installed-groups-04`: Multi-turn questions, delegation, parallel operations, denial, restart, and interruption preserve shared state.
- [ ] `installed-groups-05`: Clean install, update, and restore use the exact tested source and dependency manifests.

### release-adapter (package 8)

Registrations: PreToolUse.4.1, PostToolUse.6.1.

- [ ] `release-adapter-01`: Actual Discord question, answer, timeout, and cancellation delivery pass after the single-gateway migration.

### regression-gates (package 9)

Registrations: PreToolUse.1.1, PreToolUse.2.1, PreToolUse.3.1, PreToolUse.3.2, PreToolUse.4.1, PreToolUse.5.1, PostToolUse.1.1, PostToolUse.2.1, PostToolUse.3.1, PostToolUse.4.1, PostToolUse.5.1, PostToolUse.6.1, PostToolUse.7.1, PostToolUse.8.1, PostToolUse.8.2, PostToolUse.8.3, PostToolUse.8.4, PostToolUse.8.5, PostToolUse.8.6, PostToolUse.8.7, PostToolUse.9.1, PostToolUse.9.2, PostToolUse.9.3, PostToolUse.9.4, PostToolUse.9.5, PostToolUse.9.6, PostToolUse.9.7, PostToolUse.10.1, PostToolUse.10.2, PostToolUse.10.3, PostToolUse.10.4, PostToolUse.10.5, PostToolUse.10.6, PostToolUse.10.7, PostToolUse.11.1, PostToolUse.12.1, PostToolUse.12.2, PostToolUse.13.1, SessionEnd.1.1, SessionEnd.1.2, SessionEnd.1.3, SessionEnd.1.4, SessionEnd.1.5, SessionEnd.1.6, UserPromptSubmit.1.1, UserPromptSubmit.2.1, UserPromptSubmit.3.1, UserPromptSubmit.4.1, UserPromptSubmit.5.1, UserPromptSubmit.6.1, UserPromptSubmit.7.1, UserPromptSubmit.8.1, UserPromptSubmit.9.1, PostToolUseFailure.1.1, PostToolUseFailure.2.1, PostToolUseFailure.3.1, TaskCreated.1.1, ConfigChange.1.1, SessionStart.1.1, SessionStart.1.2, SessionStart.1.3, SessionStart.1.4, SessionStart.1.5, Stop.1.1, Stop.1.2, Stop.1.3, Stop.1.4, Stop.1.5, Stop.1.6, Stop.1.7, Stop.2.1, StopFailure.1.1, PermissionRequest.1.1, PermissionRequest.2.1.

- [ ] `regression-gates-01`: All paired acceptance results and retained artifact hashes pass the final evidence check.
- [ ] `regression-gates-02`: The complete patch rebuild and installed source identity checks pass.
- [x] `regression-gates-03`: Concurrent service admission errors are instrumented and resolved without weakening admission.
- [ ] `regression-gates-04`: Required regression suites pass with every skip explicitly classified against the acceptance scope.
