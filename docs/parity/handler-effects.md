# Registration effect matrix

Date: 2026-10-07. The accepted finite contract verifies effects for 73 of 74 registrations. The ledger retains 152 equal selected comparisons and supplementary branch evidence. Enabled reminder delivery needs an approved private GitHub test repository. Actual Discord transport remains a release gate. Native web and batch controls remain functional comparisons with explicit native CLI limits.

The [acceptance checklist](step1-acceptance.md) records 150 verified scenarios out of 152. The [final installed report](../verification/2026-10-07-step1/installed-release-controls/README.md) records full installed flows, regression results, source identity, and intentional limits.

| Registration | Handler | Expected effect | Acceptance |
| --- | --- | --- | --- |
| PreToolUse.1.1 | $HOME/.claude/hooks/ContextReduction.hook.sh | Rewrite supported commands through RTK and retain the native permission decision. | Verified accepted handler contract |
| PreToolUse.2.1 | http://localhost:31337/hooks/skill-guard | Validate the selected skill and return its Pulse guard decision. | Verified accepted handler contract |
| PreToolUse.3.1 | http://localhost:31337/hooks/agent-guard | Validate the selected agent and return its Pulse guard decision. | Verified accepted handler contract |
| PreToolUse.3.2 | $HOME/.claude/hooks/AgentInvocation.hook.ts | Record and validate agent invocation and completion state. | Verified accepted handler contract |
| PreToolUse.4.1 | $HOME/.claude/hooks/TabState.hook.ts | Set the terminal state for a question awaiting a user answer. | Verified accepted handler contract |
| PreToolUse.5.1 | $HOME/.claude/hooks/PreToolGuard.hook.ts | Run the nested pre-tool guards and preserve deny, ask, and changed-input decisions. | Verified accepted handler contract |
| PostToolUse.1.1 | $HOME/.claude/hooks/AgentInvocation.hook.ts | Record and validate agent invocation and completion state. | Verified accepted handler contract |
| PostToolUse.2.1 | $HOME/.claude/hooks/Safety.hook.ts | Annotate attacker-writable external results as data, report injection patterns, and keep other MCP results neutral. | Verified accepted handler contract |
| PostToolUse.3.1 | $HOME/.claude/hooks/Safety.hook.ts | Annotate attacker-writable external results as data, report injection patterns, and keep other MCP results neutral. | Verified accepted handler contract |
| PostToolUse.4.1 | $HOME/.claude/hooks/Safety.hook.ts | Annotate attacker-writable external results as data, report injection patterns, and keep other MCP results neutral. | Verified accepted handler contract |
| PostToolUse.5.1 | $HOME/.claude/hooks/Safety.hook.ts | Annotate attacker-writable external results as data, report injection patterns, and keep other MCP results neutral. | Verified accepted handler contract |
| PostToolUse.6.1 | $HOME/.claude/hooks/TabState.hook.ts | Restore the applicable terminal state after the user answer. | Verified accepted handler contract |
| PostToolUse.7.1 | $HOME/.claude/hooks/ISAStaleWriteGuard.hook.ts | Record the complete ISA content view for this session and backend. | Verified accepted handler contract |
| PostToolUse.8.1 | $HOME/.claude/hooks/ISASync.hook.ts | Synchronize ISA and active work state after a successful file change. | Verified accepted handler contract |
| PostToolUse.8.2 | $HOME/.claude/hooks/ISAStaleWriteGuard.hook.ts | Prevent ISA writes based on a stale session view of the actual local or backend file. | Verified accepted handler contract |
| PostToolUse.8.3 | $HOME/.claude/hooks/CheckpointPerISC.hook.ts | Commit eligible verified ISC state and write a retrievable checkpoint record. | Verified accepted handler contract |
| PostToolUse.8.4 | $HOME/.claude/hooks/ConfigEvalFire.hook.ts | Trigger the configured evaluation when an applicable configuration file changes. | Verified accepted handler contract |
| PostToolUse.8.5 | $HOME/.claude/hooks/AtlasEventCapture.hook.ts | Record applicable architecture file changes in the native event store. | Verified accepted handler contract |
| PostToolUse.8.6 | $HOME/.claude/hooks/KnowledgeWriteGuard.hook.ts | Enforce the native knowledge-write contract for applicable file changes. | Verified accepted handler contract |
| PostToolUse.8.7 | $HOME/.claude/hooks/ComplexityRatchet.hook.ts | Accumulate changed lines and return the configured complexity warning. | Verified accepted handler contract |
| PostToolUse.9.1 | $HOME/.claude/hooks/ISASync.hook.ts | Synchronize ISA and active work state after a successful file change. | Verified accepted handler contract |
| PostToolUse.9.2 | $HOME/.claude/hooks/ISAStaleWriteGuard.hook.ts | Prevent ISA writes based on a stale session view of the actual local or backend file. | Verified accepted handler contract |
| PostToolUse.9.3 | $HOME/.claude/hooks/CheckpointPerISC.hook.ts | Commit eligible verified ISC state and write a retrievable checkpoint record. | Verified accepted handler contract |
| PostToolUse.9.4 | $HOME/.claude/hooks/ConfigEvalFire.hook.ts | Trigger the configured evaluation when an applicable configuration file changes. | Verified accepted handler contract |
| PostToolUse.9.5 | $HOME/.claude/hooks/AtlasEventCapture.hook.ts | Record applicable architecture file changes in the native event store. | Verified accepted handler contract |
| PostToolUse.9.6 | $HOME/.claude/hooks/KnowledgeWriteGuard.hook.ts | Enforce the native knowledge-write contract for applicable file changes. | Verified accepted handler contract |
| PostToolUse.9.7 | $HOME/.claude/hooks/ComplexityRatchet.hook.ts | Accumulate changed lines and return the configured complexity warning. | Verified accepted handler contract |
| PostToolUse.10.1 | $HOME/.claude/hooks/ISASync.hook.ts | Synchronize ISA and active work state after a successful file change. | Verified accepted handler contract |
| PostToolUse.10.2 | $HOME/.claude/hooks/ISAStaleWriteGuard.hook.ts | Prevent ISA writes based on a stale session view of the actual local or backend file. | Verified accepted handler contract |
| PostToolUse.10.3 | $HOME/.claude/hooks/CheckpointPerISC.hook.ts | Commit eligible verified ISC state and write a retrievable checkpoint record. | Verified accepted handler contract |
| PostToolUse.10.4 | $HOME/.claude/hooks/ConfigEvalFire.hook.ts | Trigger the configured evaluation when an applicable configuration file changes. | Verified accepted handler contract |
| PostToolUse.10.5 | $HOME/.claude/hooks/AtlasEventCapture.hook.ts | Record applicable architecture file changes in the native event store. | Verified accepted handler contract |
| PostToolUse.10.6 | $HOME/.claude/hooks/KnowledgeWriteGuard.hook.ts | Enforce the native knowledge-write contract for applicable file changes. | Verified accepted handler contract |
| PostToolUse.10.7 | $HOME/.claude/hooks/ComplexityRatchet.hook.ts | Accumulate changed lines and return the configured complexity warning. | Verified accepted handler contract |
| PostToolUse.11.1 | $HOME/.claude/hooks/EventLogger.hook.ts | Write native tool activity, record applicable skill execution, and update the active ISA heartbeat. | Verified accepted handler contract |
| PostToolUse.12.1 | $HOME/.claude/hooks/PostToolObserver.hook.ts | Run the nested post-tool observers with the actual result and transcript. | Verified accepted handler contract |
| PostToolUse.12.2 | $HOME/.claude/hooks/LoopDetector.hook.ts | Track repeated failures and return the native loop warning. | Verified accepted handler contract |
| PostToolUse.13.1 | $HOME/.claude/hooks/AtlasEventCapture.hook.ts | Record applicable architecture file changes in the native event store. | Verified accepted handler contract |
| SessionEnd.1.1 | $HOME/.claude/hooks/WorkCompletionLearning.hook.ts | Read session completion evidence and persist eligible native learning. | Verified accepted handler contract |
| SessionEnd.1.2 | $HOME/.claude/hooks/SessionCleanup.hook.ts | Retain completed work and remove applicable transient session naming state. | Verified accepted handler contract |
| SessionEnd.1.3 | $HOME/.claude/hooks/UpdateCounts.hook.ts | Refresh the configured usage counts or remain neutral without OAuth credentials. | Verified accepted handler contract |
| SessionEnd.1.4 | $HOME/.claude/hooks/MemoryHealthGate.hook.ts | Check native memory health and publish the applicable result without losing async delivery. | Verified accepted handler contract |
| SessionEnd.1.5 | $HOME/.claude/hooks/DocIntegrity.hook.ts | Check documentation integrity and report applicable stale documentation. | Verified accepted handler contract |
| SessionEnd.1.6 | $HOME/.claude/hooks/IntegrityCheck.hook.ts | Compare installed files with the native integrity baseline and report changes. | Verified accepted handler contract |
| UserPromptSubmit.1.1 | $HOME/.claude/hooks/PromptProcessing.hook.ts | Create and persist the session name, including the configured child inference result. | Verified accepted handler contract |
| UserPromptSubmit.2.1 | $HOME/.claude/hooks/SatisfactionCapture.hook.ts | Capture eligible satisfaction feedback from the submitted prompt. | Verified accepted handler contract |
| UserPromptSubmit.3.1 | $HOME/.claude/hooks/ReminderRouter.hook.ts | Create a private GitHub issue for configured explicit reminder, research, or queue intent after confirmed command success. | Enabled external delivery remains open |
| UserPromptSubmit.4.1 | $HOME/.claude/hooks/VersionDrift.hook.ts | Compare the installation with its selected baseline and emit the native drift warning. | Verified accepted handler contract |
| UserPromptSubmit.5.1 | $HOME/.claude/hooks/MemoryTurnStart.hook.ts | Supply the admitted native memory context for the current turn. | Verified accepted handler contract |
| UserPromptSubmit.6.1 | $HOME/.claude/hooks/DriftReminder.hook.ts | Return the applicable drift context within its per-prompt line budget. | Verified accepted handler contract |
| UserPromptSubmit.7.1 | $HOME/.claude/hooks/AlgorithmNudge.hook.ts | Return the applicable algorithm or capability nudge to the model. | Verified accepted handler contract |
| UserPromptSubmit.8.1 | $HOME/.claude/hooks/TimeContext.hook.ts | Return the current native time context through the configured async path. | Verified accepted handler contract |
| UserPromptSubmit.9.1 | $HOME/.claude/hooks/ModelRungGuard.hook.ts | Evaluate the actual model and effort carrier and return the applicable rung guidance. | Verified accepted handler contract |
| PostToolUseFailure.1.1 | $HOME/.claude/hooks/EventLogger.hook.ts | Write the native tool-failure audit row with the actual tool and error. | Verified accepted handler contract |
| PostToolUseFailure.2.1 | $HOME/.claude/hooks/AlgorithmNudge.hook.ts | Return the applicable algorithm or capability nudge to the model. | Verified accepted handler contract |
| PostToolUseFailure.3.1 | $HOME/.claude/hooks/LoopDetector.hook.ts | Track repeated failures and return the native loop warning. | Verified accepted handler contract |
| TaskCreated.1.1 | $HOME/.claude/hooks/TaskGovernance.hook.ts | Apply the task quality and count rules to the actual task creation event. | Verified accepted handler contract |
| ConfigChange.1.1 | $HOME/.claude/hooks/EventLogger.hook.ts | Write the native settings-change audit row and applicable configuration difference. | Verified accepted handler contract |
| SessionStart.1.1 | bun $HOME/.claude/hooks/HookHealer.hook.ts | Repair interpreter and executable permissions for installed registered hooks. | Verified accepted handler contract |
| SessionStart.1.2 | $HOME/.claude/hooks/KittyEnvPersist.hook.ts | Persist applicable terminal environment state and remain neutral on remote channels. | Verified accepted handler contract |
| SessionStart.1.3 | $HOME/.claude/hooks/LoadContext.hook.ts | Load the applicable native identity, system, and admitted user context. | Verified accepted handler contract |
| SessionStart.1.4 | bun $HOME/.claude/LIFEOS/TOOLS/FreshnessCache.ts --quiet | Write the native freshness cache for the installed source tree. | Verified accepted handler contract |
| SessionStart.1.5 | bun $HOME/.claude/LIFEOS/TOOLS/SettingsBackport.ts; bun $HOME/.claude/LIFEOS/TOOLS/MergeSettings.ts --system $HOME/.claude/settings.system.json --user $HOME/.claude/LIFEOS/USER/CONFIG/settings.user.json --output $HOME/.claude/settings.json | Backport applicable settings and atomically merge system and user settings. | Verified accepted handler contract |
| Stop.1.1 | $HOME/.claude/hooks/LastResponseCache.hook.ts | Persist the final assistant response in the native response cache. | Verified accepted handler contract |
| Stop.1.2 | $HOME/.claude/hooks/TabState.hook.ts | Set the applicable completed-turn terminal state. | Verified accepted handler contract |
| Stop.1.3 | $HOME/.claude/hooks/VoiceCompletion.hook.ts | Record final-answer voice state and apply the configured remote-channel desktop gate. | Verified accepted handler contract |
| Stop.1.4 | $HOME/.claude/hooks/ISARenderOnStop.hook.ts | Render the applicable active ISA after the completed response. | Verified accepted handler contract |
| Stop.1.5 | $HOME/.claude/hooks/SpendAuditor.hook.ts | Audit capability use against the native prompt-length floor and preserve the session audit marker. | Verified accepted handler contract |
| Stop.1.6 | $HOME/.claude/hooks/StopGates.hook.ts | Run nested completion gates and return required continuation or blocking feedback. | Verified accepted handler contract |
| Stop.1.7 | $HOME/.claude/hooks/MemoryReviewFire.hook.ts | Trigger the eligible native memory review and preserve proposal approval rules. | Verified accepted handler contract |
| Stop.2.1 | $HOME/.claude/hooks/MemoryHealthGate.hook.ts | Check native memory health and publish the applicable result without losing async delivery. | Verified accepted handler contract |
| StopFailure.1.1 | $HOME/.claude/hooks/EventLogger.hook.ts | Write the native terminal API failure audit row with the actual error. | Verified accepted handler contract |
| PermissionRequest.1.1 | $HOME/.claude/hooks/Safety.hook.ts | Evaluate the actual command or file permission request, including secret egress, and return the native decision. | Verified accepted handler contract |
| PermissionRequest.2.1 | $HOME/.claude/hooks/Safety.hook.ts | Evaluate the actual command or file permission request, including secret egress, and return the native decision. | Verified accepted handler contract |
