Date: 2026-09-28
Agent role: Read-only command rewrite contract reviewer
Question: What is the smallest safe Hermes host change for PermissionRequest updatedInput.command?
Model: GPT-6 Codex (inherited model)

The existing hook contract cannot carry a rewritten command. HookBridge.command_approval reads decision.behavior and drops decision.updatedInput. Hermes _plugin_command_decision reduces dictionaries to a string. terminal_tool always executes its original command even if a future guard result supplies another command.

Source checkout: lifeos-hermes@192.168.8.212:~/workspace/hermes-agent. The exact commit and status are at the start of hermes-source.txt. Review used SSH reads only. No production code was edited. No tests were run for this review.

Recommended generic contract

Return an optional command string alongside action (allow/review/deny) from pre_command_approval. Carry the final command in the combined guard result and _ApprovalVerdict. Do not overload the action string to convey replacement. Explicit deny wins across all plugin returns. Validate replacement type, nonempty content, and conflicting replacements. Reject malformed or conflicting replacements with a structured denial. Identical replacements are harmless. Extra native Bash keys such as timeout must not silently become Hermes execution options; support command only and state that scope.

The replacement requires another complete policy pass. A grant for command A is not authority for command B. Recompute pattern detection, command fingerprint, plugin decision, applicable safety floors, Tirith findings, and human approval from B. Invoke plugins against B so another plugin that only denies B can participate. Treat a replacement equal to the current command as stable. Bound repeated rewrites and reject cycles or exhaustion before execution. A small loop is safer than uncontrolled recursive guard calls. Scope every prepared approval and final consent to the effective command, workspace, task, environment, and host-access state.

The bridge must also evaluate LifeOS Bash and Read/Write file rules against B. Re-entering command_approval on B naturally supplies those checks. Existing allow-only and deny-only behavior should remain unchanged. Retain denial precedence if one native hook denies while another proposes a rewrite.

Host patch points

1. tools/approval.py: _plugin_command_decision has TWO callers, check_all_command_guards and check_dangerous_command. Update both if its return type changes. The simpler check_dangerous_command cannot silently accept and drop a replacement. Either propagate an effective command contract there or fail closed when a rewrite is returned to a caller that cannot execute it.
2. tools/approval.py: check_all_command_guards must produce approved/pending results for the final command. Run applicable hardline, runtime self-delete, sudo stdin, user deny, dangerous-pattern and Tirith checks against that command. Current isolated container behavior intentionally omits hardline and Tirith checks; preserve this existing backend policy while keeping user deny and plugin policy active there.
3. tools/terminal_tool.py: _ApprovalVerdict needs the final command. After approval, assign that command before PTY checks, spawn_background_process, and _run_foreground. Both paths must execute the same command that the guard approved.
4. tools/terminal_tool.py: _pre_exec_block currently runs BEFORE _run_approval_guards. Therefore a rewrite can evade gateway lifecycle and self-repository checks unless the final command passes the bounded pre-exec guard again. Preserve deadline, interruption, and fail-closed timeout behavior. A second check only when the command changes is the smallest change.
5. tools/terminal_tool.py: _plan_execution also examines command before approval, through _foreground_background_guidance. Revalidate that command-dependent planning rule for the replacement. Full replanning is unnecessary if all non-command options remain fixed.
6. agent/terminal_approval_batch.py: prepared guard decisions are indexed by original command plus environment, host access, cwd, and task_id. Consuming a result with command B must not discard B. Recheck B's applicable safety floors before accepting cached approval. Preserve one-use consumption, call-id matching, workspace matching, and invalidation after earlier batch failure. Do not mutate the prepared input dictionary in a way that triggers validate_prepared_terminal's deliberate argument mismatch refusal.
7. Audit observers: agent/tool_executor.py emits post_tool_call using _ToolCallRef.args, while _handle_terminal passes a scalar command into terminal_tool. Reassigning that scalar does not update PostToolUse input. Full native parity requires carrying effective arguments back to the observer boundary or an explicit execution-metadata contract consumed by the bridge. Otherwise document that execution works while the audit still reports the original command. Do not claim complete native rewrite parity without testing this.

Approval details

The pending command gate already includes command in _pending_result, and terminal_tool propagates approval.get(command, original). Populate it with the final command. Human/guardian prompts must inspect the final command. Existing normal approved results do not include command; the new contract must attach it on every successful return path, including no-warning, isolated container, plugin allow, and human approval.

force=True currently skips _run_approval_guards entirely. Normal _handle_terminal does not expose force. Any internal replay must execute the exact approved replacement, never the original command plus permission for its replacement. A forced pass cannot apply a fresh rewrite after consent unless it also obtains consent for that new command. Review this as an explicit replay invariant even if no active gateway replay caller exists in the inspected source.

Current policy bypass behavior is pre-existing: yolo/off and permanent allowlist return before plugin policy; unattended noninteractive flows can return before Tirith. A rewrite extension should not silently claim stronger guarantees than those configured modes provide. Rechecking the replacement must follow the same ordinary guard path for its applicable mode.

Verification required before claiming support

- A benign original becomes a benign replacement, and only the replacement creates its marker, in both foreground and background terminal paths.
- Hardline, runtime self-delete, sudo stdin, and user-deny replacements never reach environment execution where those checks apply.
- A Tirith finding on the replacement reaches human/guardian review, and plugin allow cannot suppress it.
- Native LifeOS Bash deny and Read/Write target deny block the replacement, including backend-specific paths.
- Another plugin's denial of the replacement wins over the first plugin's grant.
- Conflicting, malformed, cyclic, and too-many rewrites fail closed. Same-command replacement terminates normally.
- Gateway lifecycle and self-repository guards receive the replacement, and their timeout blocks execution.
- Pending approvals and session fingerprints identify the replacement. Prepared approvals survive correctly scoped use and reject changed cwd/task/call or a changed policy denial.
- PostToolUse and failure transcripts record the effective command with its real result.

Raw source excerpts are in hermes-source.txt and bridge-source.txt. The read-only review proves the current dataflow gaps from source, not the correctness of an implementation that has not been written.
