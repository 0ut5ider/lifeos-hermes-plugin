# Registration effect matrix

Date: 2026-10-05. This table gives each of the 74 pinned registrations an expected effect. A selected passing case does not close all handler branches. Related native tests are indexed in [the JSON ledger](handler-effects.json). Seventy-seven equal selected cases cover 28 registrations. Seventy-five lifecycle cases use real client events and synthetic file assertions, including three request-delivery cases, three successful startup response cases, three response-cache cases, ten feedback capture cases, including five asynchronous cases, five format-contract cases, four current-time cases, seven version-drift cases, six end-of-turn render cases, three mutation hint cases with real tool calls, three pre-tool guard cases, three tool logging cases, and three file hint cases with real Write and Edit calls; the earlier two cases retain their original scope. The retained remote Kitty case demonstrates the existing channel-isolation difference and does not count as equal.

| Registration | Handler | Expected effect | Paired effect evidence |
| --- | --- | --- | --- |
| PreToolUse.1.1 | ContextReduction | Rewrite supported commands through RTK and retain the native permission decision. | Pending |
| PreToolUse.2.1 | skill-guard | Validate the selected skill and return its Pulse guard decision. | Pending |
| PreToolUse.3.1 | agent-guard | Validate the selected agent and return its Pulse guard decision. | Pending |
| PreToolUse.3.2 | AgentInvocation | Record and validate agent invocation and completion state. | Pending |
| PreToolUse.4.1 | TabState | Set the terminal state for a question awaiting a user answer. | Pending |
| PreToolUse.5.1 | PreToolGuard | Run the nested pre-tool guards and preserve deny, ask, and changed-input decisions. | Selected Bash cases pass; file guards and the other Bash guards remain open |
| PostToolUse.1.1 | AgentInvocation | Record and validate agent invocation and completion state. | Pending |
| PostToolUse.2.1 | Safety | Annotate attacker-writable external results as data, report injection patterns, and keep other MCP results neutral. | Pending |
| PostToolUse.3.1 | Safety | Annotate attacker-writable external results as data, report injection patterns, and keep other MCP results neutral. | Pending |
| PostToolUse.4.1 | Safety | Annotate attacker-writable external results as data, report injection patterns, and keep other MCP results neutral. | Pending |
| PostToolUse.5.1 | Safety | Annotate attacker-writable external results as data, report injection patterns, and keep other MCP results neutral. | Selected case verified |
| PostToolUse.6.1 | TabState | Restore the applicable terminal state after the user answer. | Pending |
| PostToolUse.7.1 | ISAStaleWriteGuard | Record the complete ISA content view for this session and backend. | Pending |
| PostToolUse.8.1 | ISASync | Synchronize ISA and active work state after a successful file change. | Pending |
| PostToolUse.8.2 | ISAStaleWriteGuard | Prevent ISA writes based on a stale session view of the actual local or backend file. | Pending |
| PostToolUse.8.3 | CheckpointPerISC | Commit eligible verified ISC state and write a retrievable checkpoint record. | Pending |
| PostToolUse.8.4 | ConfigEvalFire | Trigger the configured evaluation when an applicable configuration file changes. | Only the non-sentinel Write branch passes; the sentinel branch is deferred after a Hermes hang |
| PostToolUse.8.5 | AtlasEventCapture | Record applicable architecture file changes in the native event store. | Selected Write cases pass; other tracked file patterns remain open |
| PostToolUse.8.6 | KnowledgeWriteGuard | Enforce the native knowledge-write contract for applicable file changes. | Pending |
| PostToolUse.8.7 | ComplexityRatchet | Accumulate changed lines and return the configured complexity warning. | Pending |
| PostToolUse.9.1 | ISASync | Synchronize ISA and active work state after a successful file change. | Pending |
| PostToolUse.9.2 | ISAStaleWriteGuard | Prevent ISA writes based on a stale session view of the actual local or backend file. | Pending |
| PostToolUse.9.3 | CheckpointPerISC | Commit eligible verified ISC state and write a retrievable checkpoint record. | Pending |
| PostToolUse.9.4 | ConfigEvalFire | Trigger the configured evaluation when an applicable configuration file changes. | Only the non-sentinel Edit branch passes; the sentinel branch is open |
| PostToolUse.9.5 | AtlasEventCapture | Record applicable architecture file changes in the native event store. | Selected Edit case passes; other tracked file patterns remain open |
| PostToolUse.9.6 | KnowledgeWriteGuard | Enforce the native knowledge-write contract for applicable file changes. | Pending |
| PostToolUse.9.7 | ComplexityRatchet | Accumulate changed lines and return the configured complexity warning. | Pending |
| PostToolUse.10.1 | ISASync | Synchronize ISA and active work state after a successful file change. | Pending |
| PostToolUse.10.2 | ISAStaleWriteGuard | Prevent ISA writes based on a stale session view of the actual local or backend file. | Pending |
| PostToolUse.10.3 | CheckpointPerISC | Commit eligible verified ISC state and write a retrievable checkpoint record. | Pending |
| PostToolUse.10.4 | ConfigEvalFire | Trigger the configured evaluation when an applicable configuration file changes. | Pending |
| PostToolUse.10.5 | AtlasEventCapture | Record applicable architecture file changes in the native event store. | Pending |
| PostToolUse.10.6 | KnowledgeWriteGuard | Enforce the native knowledge-write contract for applicable file changes. | Pending |
| PostToolUse.10.7 | ComplexityRatchet | Accumulate changed lines and return the configured complexity warning. | Pending |
| PostToolUse.11.1 | EventLogger | Write native tool activity, record applicable skill execution, and update the active ISA heartbeat. | Selected Bash case passes with the pinned asynchronous setting; output field names differ by an accepted host limit; Skill, file, and work-reconcile branches remain open |
| PostToolUse.12.1 | PostToolObserver | Run the nested post-tool observers with the actual result and transcript. | Pending |
| PostToolUse.12.2 | LoopDetector | Track repeated failures and return the native loop warning. | Selected single-call and exact-repeat cases pass; oscillation and hammering remain open |
| PostToolUse.13.1 | AtlasEventCapture | Record applicable architecture file changes in the native event store. | Selected Bash cases pass; the cloudflare and DNS patterns remain open |
| SessionEnd.1.1 | WorkCompletionLearning | Read session completion evidence and persist eligible native learning. | Selected cases verified |
| SessionEnd.1.2 | SessionCleanup | Close native session state and remove the applicable transient work state. | Selected cases verified |
| SessionEnd.1.3 | UpdateCounts | Refresh the configured usage counts or remain neutral without OAuth credentials. | Selected cases verified |
| SessionEnd.1.4 | MemoryHealthGate | Check native memory health and publish the applicable result without losing async delivery. | Selected cases verified |
| SessionEnd.1.5 | DocIntegrity | Check documentation integrity and report applicable stale documentation. | Selected cases verified |
| SessionEnd.1.6 | IntegrityCheck | Compare installed files with the native integrity baseline and report changes. | Pending |
| UserPromptSubmit.1.1 | PromptProcessing | Create and persist the session name, including the configured child inference result. | Pending |
| UserPromptSubmit.2.1 | SatisfactionCapture | Capture eligible satisfaction feedback from the submitted prompt. | Selected synchronous and asynchronous feedback cases; remaining branches open |
| UserPromptSubmit.3.1 | ReminderRouter | Route due native reminders under the configured session and delivery policy. | Pending |
| UserPromptSubmit.4.1 | VersionDrift | Compare the installation with its selected baseline and emit the native drift warning. | Selected cases pass; first asynchronous request lacks the warning; next-turn delivery remains open |
| UserPromptSubmit.5.1 | MemoryTurnStart | Supply the admitted native memory context for the current turn. | Pending |
| UserPromptSubmit.6.1 | DriftReminder | Return the applicable drift context within its per-prompt line budget. | Five paired format-contract cases; remaining branches open |
| UserPromptSubmit.7.1 | AlgorithmNudge | Return the applicable algorithm or capability nudge to the model. | Pending |
| UserPromptSubmit.8.1 | TimeContext | Return the current native time context through the configured async path. | Selected cases pass; first asynchronous request lacks clock context; next-turn delivery remains open |
| UserPromptSubmit.9.1 | ModelRungGuard | Evaluate the actual model and effort carrier and return the applicable rung guidance. | Pending |
| PostToolUseFailure.1.1 | EventLogger | Write the native tool-failure audit row with the actual tool and error. | Selected failing Bash case passes with equal error text; other tools remain open |
| PostToolUseFailure.2.1 | AlgorithmNudge | Return the applicable algorithm or capability nudge to the model. | Pending |
| PostToolUseFailure.3.1 | LoopDetector | Track repeated failures and return the native loop warning. | Selected failing Bash case passes; hammering remains open |
| TaskCreated.1.1 | TaskGovernance | Apply the task quality and count rules to the actual task creation event. | Pending |
| ConfigChange.1.1 | EventLogger | Write the native settings-change audit row and applicable configuration difference. | Pending |
| SessionStart.1.1 | HookHealer | Repair interpreter and executable permissions for installed registered hooks. | Selected cases verified |
| SessionStart.1.2 | KittyEnvPersist | Persist applicable terminal environment state and remain neutral on remote channels. | Selected cases verified |
| SessionStart.1.3 | LoadContext | Load the applicable native identity, system, and admitted user context. | Selected cases verified |
| SessionStart.1.4 | FreshnessCache.ts --quiet | Write the native freshness cache for the installed source tree. | Selected cases verified |
| SessionStart.1.5 | SettingsBackport and MergeSettings | Backport applicable settings and atomically merge system and user settings. | Selected cases verified |
| Stop.1.1 | LastResponseCache | Persist the final assistant response in the native response cache. | Selected cases verified |
| Stop.1.2 | TabState | Set the applicable completed-turn terminal state. | Pending |
| Stop.1.3 | VoiceCompletion | Record final-answer voice state and apply the configured remote-channel desktop gate. | Pending |
| Stop.1.4 | ISARenderOnStop | Render the applicable active ISA after the completed response. | Selected cases pass; spawn failure and fresh-page branches remain open |
| Stop.1.5 | SpendAuditor | Update and check the native session spending record under the configured cost policy. | Pending |
| Stop.1.6 | StopGates | Run nested completion gates and return required continuation or blocking feedback. | Pending |
| Stop.1.7 | MemoryReviewFire | Trigger the eligible native memory review and preserve proposal approval rules. | Pending |
| Stop.2.1 | MemoryHealthGate | Check native memory health and publish the applicable result without losing async delivery. | Pending |
| StopFailure.1.1 | EventLogger | Write the native terminal API failure audit row with the actual error. | Selected case verified |
| PermissionRequest.1.1 | Safety | Evaluate the actual command or file permission request, including secret egress, and return the native decision. | Pending |
| PermissionRequest.2.1 | Safety | Evaluate the actual command or file permission request, including secret egress, and return the native decision. | Pending |
