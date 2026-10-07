# Hooks in delegated child turns

Date: 2026-10-05. A paired Agent case found that Hermes ran the main-session hooks for a delegated child. Production on `.212` stays unchanged.

## Measurement

The same prompt asks each client to delegate one task. The fixture records every lifecycle event that reaches the hook layer.

| Client | Events |
| --- | --- |
| Claude Code 2.1.272 | Main session: SessionStart, UserPromptSubmit, SessionEnd. The subagent produces none of these events. |
| Hermes with the bridge | Main session: SessionStart, UserPromptSubmit, SessionEnd. Child session: SessionStart (`startup`) and UserPromptSubmit with the delegated task text. |

Under Hermes, every LifeOS SessionStart and UserPromptSubmit hook therefore ran again for each delegated child: context loading, memory injection, feedback capture, version drift, and the others. The bridge also ran the Stop gates on the child answer. A Claude Code subagent ends with SubagentStop, and LifeOS registers no SubagentStop hook.

## Correction

The bridge now returns without running hooks in `pre_llm_call` and `stop` when Hermes reports a delegated child context, in the same process or in a child process. Tool hooks still run in children and carry the `agent_id` and `agent_type` fields, as before.

Two new regressions fail before the correction ([before.txt](before.txt) records the first): a child prompt ran both hooks, and a child answer could be blocked by a Stop gate. The bridge, provider, Stop effort, and delegation route suites pass 194 tests with one optional skip ([after.txt](after.txt)).

## Limits

A paired Agent case on the corrected plugin is the next check. This correction does not add SubagentStart or SubagentStop support, because LifeOS registers neither event.
