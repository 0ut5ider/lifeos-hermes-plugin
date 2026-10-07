# Registration effect matrix

Date: 2026-10-06. This table gives each of the 74 pinned registrations an expected effect. The ledger retains 152 equal selected cases across all 74 registrations. Cases for 65 registrations use native Claude Code events. Nine registrations use actual Hermes tools and direct native handlers because the pinned native CLI has no usable web or MultiEdit control in these fixtures. The [selected completion report](../verification/2026-10-06-hook-completion/README.md) records the distinction and the remaining limits. A selected passing case does not close every handler branch. Related native tests are indexed in [the JSON ledger](handler-effects.json). The retained remote Kitty case demonstrates the existing channel-isolation difference and does not count as equal.

| Registration | Handler | Expected effect | Paired effect evidence |
| --- | --- | --- | --- |
| PreToolUse.1.1 | ContextReduction | Rewrite supported commands through RTK and retain the native permission decision. | Selected case without rtk passes: no output, command unchanged |
| PreToolUse.2.1 | skill-guard | Validate the selected skill and return its Pulse guard decision. | Real Pulse skill denial and allowance pass through both clients |
| PreToolUse.3.1 | agent-guard | Validate the selected agent and return its Pulse guard decision. | Real Pulse foreground warning passes through both clients; watchdog and failure paths have native controls |
| PreToolUse.3.2 | AgentInvocation | Record and validate agent invocation and completion state. | Inherited and explicit Opus starts pass with the served model and fixed agent type |
| PreToolUse.4.1 | TabState | Set the terminal state for a question awaiting a user answer. | Real question round trip sets waiting state; Discord delivery remains open |
| PreToolUse.5.1 | PreToolGuard | Run the nested pre-tool guards and preserve deny, ask, and changed-input decisions. | Selected Bash cases pass; file guards and the other Bash guards remain open |
| PostToolUse.1.1 | AgentInvocation | Record and validate agent invocation and completion state. | Selected delegation passes: one subagent stop row on both clients after the child-hook correction |
| PostToolUse.2.1 | Safety | Annotate attacker-writable external results as data, report injection patterns, and keep other MCP results neutral. | Ordinary and injection extraction pass through Hermes with next-request Safety context and direct native handler comparison |
| PostToolUse.3.1 | Safety | Annotate attacker-writable external results as data, report injection patterns, and keep other MCP results neutral. | Ordinary and injection search pass through Hermes with next-request Safety context and direct native handler comparison |
| PostToolUse.4.1 | Safety | Annotate attacker-writable external results as data, report injection patterns, and keep other MCP results neutral. | Selected MCP result passes: external-content warning delivered to the model on both clients |
| PostToolUse.5.1 | Safety | Annotate attacker-writable external results as data, report injection patterns, and keep other MCP results neutral. | Selected case verified |
| PostToolUse.6.1 | TabState | Restore the applicable terminal state after the user answer. | Real question round trip restores the prior state; timeout and cancellation have native controls |
| PostToolUse.7.1 | ISAStaleWriteGuard | Record the complete ISA content view for this session and backend. | Selected Read case passes: the session view records the read content |
| PostToolUse.8.1 | ISASync | Synchronize ISA and active work state after a successful file change. | Selected Write case passes: registry, render state, and phase strip |
| PostToolUse.8.2 | ISAStaleWriteGuard | Prevent ISA writes based on a stale session view of the actual local or backend file. | Selected Write case passes: the session view records the written content |
| PostToolUse.8.3 | CheckpointPerISC | Commit eligible verified ISC state and write a retrievable checkpoint record. | Selected Write case passes: one checkpoint commit; subject format differs by the plugin patch |
| PostToolUse.8.4 | ConfigEvalFire | Trigger the configured evaluation when an applicable configuration file changes. | Actual Write evaluation, failed result, debounce, missing runner, nonsentinel, and protected-file controls pass |
| PostToolUse.8.5 | AtlasEventCapture | Record applicable architecture file changes in the native event store. | Selected Write cases pass; other tracked file patterns remain open |
| PostToolUse.8.6 | KnowledgeWriteGuard | Enforce the native knowledge-write contract for applicable file changes. | Off-schema warning, index-file, and outside-tree branches pass for Write |
| PostToolUse.8.7 | ComplexityRatchet | Accumulate changed lines and return the configured complexity warning. | Selected Write case passes without a finding |
| PostToolUse.9.1 | ISASync | Synchronize ISA and active work state after a successful file change. | Selected Edit case passes: registry, render state, and phase strip delivered to the model |
| PostToolUse.9.2 | ISAStaleWriteGuard | Prevent ISA writes based on a stale session view of the actual local or backend file. | Selected Edit case passes: the session view records the edited content |
| PostToolUse.9.3 | CheckpointPerISC | Commit eligible verified ISC state and write a retrievable checkpoint record. | Selected Edit case passes: one checkpoint commit in the allowlisted repository; subject format differs by the plugin patch |
| PostToolUse.9.4 | ConfigEvalFire | Trigger the configured evaluation when an applicable configuration file changes. | Actual Edit evaluation and four concurrent sentinel edits complete one real evaluation without hook errors |
| PostToolUse.9.5 | AtlasEventCapture | Record applicable architecture file changes in the native event store. | Selected Edit cases pass |
| PostToolUse.9.6 | KnowledgeWriteGuard | Enforce the native knowledge-write contract for applicable file changes. | Selected Edit case passes outside the knowledge tree |
| PostToolUse.9.7 | ComplexityRatchet | Accumulate changed lines and return the configured complexity warning. | Selected Edit case passes without a finding |
| PostToolUse.10.1 | ISASync | Synchronize ISA and active work state after a successful file change. | Actual batch patch updates ISA registry and render state; partial patch retains applied-file effects |
| PostToolUse.10.2 | ISAStaleWriteGuard | Prevent ISA writes based on a stale session view of the actual local or backend file. | Actual batch patch records the applied ISA content view in successful and partial cases |
| PostToolUse.10.3 | CheckpointPerISC | Commit eligible verified ISC state and write a retrievable checkpoint record. | Successful batch makes one criterion checkpoint; partial batch suppresses that checkpoint |
| PostToolUse.10.4 | ConfigEvalFire | Trigger the configured evaluation when an applicable configuration file changes. | Actual two-file sentinel batch completes one real evaluation; debounce and partial-file effects also pass |
| PostToolUse.10.5 | AtlasEventCapture | Record applicable architecture file changes in the native event store. | Actual batch captures the projects event; partial case has no unapplied projects event |
| PostToolUse.10.6 | KnowledgeWriteGuard | Enforce the native knowledge-write contract for applicable file changes. | Actual batch emits the off-schema warning; partial case has no unapplied knowledge warning |
| PostToolUse.10.7 | ComplexityRatchet | Accumulate changed lines and return the configured complexity warning. | Actual batch records 250 changed source lines and one dependency; partial case adds neither |
| PostToolUse.11.1 | EventLogger | Write native tool activity, record applicable skill execution, and update the active ISA heartbeat. | Selected Bash case passes with the pinned asynchronous setting; output field names differ by an accepted host limit; Skill, file, and work-reconcile branches remain open |
| PostToolUse.12.1 | PostToolObserver | Run the nested post-tool observers with the actual result and transcript. | Selected single-call case passes: loop and nudge state written, no output |
| PostToolUse.12.2 | LoopDetector | Track repeated failures and return the native loop warning. | Selected single-call and exact-repeat cases pass; oscillation and hammering remain open |
| PostToolUse.13.1 | AtlasEventCapture | Record applicable architecture file changes in the native event store. | Selected Bash cases pass; the cloudflare and DNS patterns remain open |
| SessionEnd.1.1 | WorkCompletionLearning | Read session completion evidence and persist eligible native learning. | Selected cases verified |
| SessionEnd.1.2 | SessionCleanup | Close native session state and remove the applicable transient work state. | Selected cases verified |
| SessionEnd.1.3 | UpdateCounts | Refresh the configured usage counts or remain neutral without OAuth credentials. | Selected cases verified |
| SessionEnd.1.4 | MemoryHealthGate | Check native memory health and publish the applicable result without losing async delivery. | Selected cases verified |
| SessionEnd.1.5 | DocIntegrity | Check documentation integrity and report applicable stale documentation. | Selected cases verified |
| SessionEnd.1.6 | IntegrityCheck | Compare installed files with the native integrity baseline and report changes. | Selected SessionEnd passes: no system file change and no output |
| UserPromptSubmit.1.1 | PromptProcessing | Create and persist the session name, including the configured child inference result. | Selected prompt passes: work events and registry written |
| UserPromptSubmit.2.1 | SatisfactionCapture | Capture eligible satisfaction feedback from the submitted prompt. | Selected synchronous and asynchronous feedback cases; remaining branches open |
| UserPromptSubmit.3.1 | ReminderRouter | Route due native reminders under the configured session and delivery policy. | Selected disabled branch passes: no work repository, no issue, no state |
| UserPromptSubmit.4.1 | VersionDrift | Compare the installation with its selected baseline and emit the native drift warning. | Selected cases pass; first asynchronous request lacks the warning; next-turn delivery remains open |
| UserPromptSubmit.5.1 | MemoryTurnStart | Supply the admitted native memory context for the current turn. | Selected first prompt passes: memory context delivered to the model and injection state written |
| UserPromptSubmit.6.1 | DriftReminder | Return the applicable drift context within its per-prompt line budget. | Five paired format-contract cases; remaining branches open |
| UserPromptSubmit.7.1 | AlgorithmNudge | Return the applicable algorithm or capability nudge to the model. | Selected first prompt passes: nudge state and skill index written, no output |
| UserPromptSubmit.8.1 | TimeContext | Return the current native time context through the configured async path. | Selected cases pass; first asynchronous request lacks clock context; next-turn delivery remains open |
| UserPromptSubmit.9.1 | ModelRungGuard | Evaluate the actual model and effort carrier and return the applicable rung guidance. | Selected first prompt passes with a pinned model; the plugin patch adds the reasoning effort to the log |
| PostToolUseFailure.1.1 | EventLogger | Write the native tool-failure audit row with the actual tool and error. | Selected failing Bash case passes with equal error text; other tools remain open |
| PostToolUseFailure.2.1 | AlgorithmNudge | Return the applicable algorithm or capability nudge to the model. | Selected failing call passes: nudge state written, no output |
| PostToolUseFailure.3.1 | LoopDetector | Track repeated failures and return the native loop warning. | Selected failing Bash case passes; hammering remains open |
| TaskCreated.1.1 | TaskGovernance | Apply the task quality and count rules to the actual task creation event. | Allowed and blocked task creation pass on both clients |
| ConfigChange.1.1 | EventLogger | Write the native settings-change audit row and applicable configuration difference. | Eight real external edits pass for user, project, local settings, and skills; paths and source-specific differences match |
| SessionStart.1.1 | HookHealer | Repair interpreter and executable permissions for installed registered hooks. | Selected cases verified |
| SessionStart.1.2 | KittyEnvPersist | Persist applicable terminal environment state and remain neutral on remote channels. | Selected cases verified |
| SessionStart.1.3 | LoadContext | Load the applicable native identity, system, and admitted user context. | Selected cases verified |
| SessionStart.1.4 | FreshnessCache.ts --quiet | Write the native freshness cache for the installed source tree. | Selected cases verified |
| SessionStart.1.5 | SettingsBackport and MergeSettings | Backport applicable settings and atomically merge system and user settings. | Selected cases verified |
| Stop.1.1 | LastResponseCache | Persist the final assistant response in the native response cache. | Selected cases verified |
| Stop.1.2 | TabState | Set the applicable completed-turn terminal state. | Selected Stop passes without a terminal: no state change |
| Stop.1.3 | VoiceCompletion | Record final-answer voice state and apply the configured remote-channel desktop gate. | Selected remote-channel Stop passes: a skipped voice event is logged |
| Stop.1.4 | ISARenderOnStop | Render the applicable active ISA after the completed response. | Selected cases pass; spawn failure and fresh-page branches remain open |
| Stop.1.5 | SpendAuditor | Update and check the native session spending record under the configured cost policy. | Selected Stop passes: spend audit row and state written |
| Stop.1.6 | StopGates | Run nested completion gates and return required continuation or blocking feedback. | Selected Stop passes after the transcript timing correction: format, verification, and writing gate rows written |
| Stop.1.7 | MemoryReviewFire | Trigger the eligible native memory review and preserve proposal approval rules. | Selected Stop passes: review state written |
| Stop.2.1 | MemoryHealthGate | Check native memory health and publish the applicable result without losing async delivery. | Selected Stop passes synchronously; the pinned asynchronous setting cannot be observed in print mode |
| StopFailure.1.1 | EventLogger | Write the native terminal API failure audit row with the actual error. | Selected case verified |
| PermissionRequest.1.1 | Safety | Evaluate the actual command or file permission request, including secret egress, and return the native decision. | Selected deferred Bash request passes: decision row written, command not run |
| PermissionRequest.2.1 | Safety | Evaluate the actual command or file permission request, including secret egress, and return the native decision. | Selected MCP permission request passes: allow decision and decision rows on both clients |
