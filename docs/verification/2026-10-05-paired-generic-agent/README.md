# Paired Agent result

Date: 2026-10-05. One case delegates one task in Claude Code 2.1.272 (Agent tool) and Hermes (`delegate_task`, reported to hooks as `Agent`). AgentInvocation runs on `PostToolUse.1.1` with the matcher `Agent`. Both clients pass.

| Effect | Result |
| --- | --- |
| One `subagent_stop` row in `subagent-events.jsonl` with type `general-purpose` | Both clients. |
| No hook output | Both clients. |
| No SessionStart or UserPromptSubmit event for the child | Both clients, after the [child-hook correction](../2026-10-05-child-session-hooks/README.md). |

Each model writes its own delegation description. The comparison replaces the subagent identifier, description, and prompt preview with a placeholder on both sides and compares every other field.

## Open: Agent PreToolUse

The `PreToolUse.3.2` case is not in the ledger. In one run, the native model chose the subagent type `Explore` and Hermes `general-purpose`. In an earlier run, Claude Code logged the model level `session-inherited` and Hermes `inherited`. The hook reads the current model from the transcript tail. Claude Code writes the assistant tool call before PreToolUse; the bridge writes it after the tool runs. That transcript difference needs a host field for the current model and a separate check.

[agent-proof.json](agent-proof.json) recomputes the changed files from the raw captures and checks the hook input. [runtime-check.json](runtime-check.json) verifies the runtime with the corrected plugin. The focused suite passes 115 tests. The cumulative ledger contains 103 equal selected cases for 58 registrations. Complete compatibility remains unverified.
