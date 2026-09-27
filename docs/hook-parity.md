# LifeOS hook parity record

This record describes the public LifeOS hook settings installed from commit `5e2f2e8` on 2026-09-27. It distinguishes registered callbacks from verified behavior. The bridge is a Hermes plugin. It does not edit LifeOS source files.

## Event coverage

| Claude Code event | Registrations | Hermes path | Current result |
| --- | ---: | --- | --- |
| `PreToolUse` | 6 | `pre_tool_call` | Command and local HTTP hooks execute for mapped tools. Exit code 2 and deny decisions block. Updated input maps back to Hermes arguments. |
| `PostToolUse` | 32 | `augment_tool_result` | Hooks execute after the existing result transform. Their `additionalContext` is appended to the model-bound result. |
| `UserPromptSubmit` | 9 | `pre_llm_call` | Hooks execute on a text prompt. Their context is added to the current user turn. Async hooks start without blocking. |
| `Stop` | 8 | `pre_turn_stop` | Hooks execute on each text answer. A block continues the same Hermes turn. A private transcript supplies `transcript_path`. |
| `SessionStart` | 5 | first `pre_llm_call` | Hooks execute before the first user prompt is sent to the model. Their text output joins that prompt's context. |
| `SessionEnd` | 6 | `on_session_end`, `on_session_reset` | Hooks are registered for both boundaries. Their effects have not been checked end to end. |
| `PostToolUseFailure` | 3 | `augment_tool_result` on tool error | The failure payload is tested with a real child process. |
| `PermissionRequest` | 2 | `pre_command_approval` for Bash | Native `Safety.hook.ts` can grant a recoverable dangerous-command warning in Hermes manual approval mode. Hermes hardline, user deny, and Tirith warnings remain effective. Write, Edit, and MCP approval paths are not mapped. |
| `TaskCreated` | 1 | `pre_tool_call` on `todo_list` | The bridge enforces the installed hook's minimum description and 50-task session limit for new todo IDs. This is equivalent policy code, not native hook execution. Kanban task creation is not covered. |
| `ConfigChange` | 1 | none | No equivalent Hermes config-change event is wired. |
| `StopFailure` | 1 | none | No equivalent failed-stop event is wired. |

The native bridge executes 69 complete registrations at matching event types and part of one `PermissionRequest` registration for Bash. The other `PermissionRequest` registration, for MCP tools, remains unmapped. It also enforces the `TaskCreated` policy for new Hermes todo IDs without executing that native hook. This count is an event-level mapping, not 69 passing behavioral tests. Hermes tool names currently mapped are `terminal`, `read_file`, `write_file`, `patch`, `delegate_task`, `web_search`, `web_fetch`, `skill_view`, `tool_search`, and `mcp__*`. Claude Code's `AskUserQuestion` and `MultiEdit` have no exact Hermes tool mapping. The LifeOS `Agent` HTTP hook uses fields that Hermes delegation does not always supply. Local Pulse routes fail open when Pulse is not running, as they do in Claude Code.

## Verified effects

- The plugin validates and loads in the isolated Hermes account.
- A real Hermes turn reads the synthetic principal as `Test Operator` and includes LifeOS memory context.
- A native LifeOS child inference call returns `READY` through the local model. The model tier is translated, so tier selection is not verified.
- A temporary Stop hook blocked the first answer. Hermes continued and produced a second answer. The hook saw `stop_hook_active: false` followed by `true`.
- Native LifeOS Format, Verification, and Writing gates wrote observability records from a Hermes turn after the bridge supplied a transcript.
- A temporary PostToolUse hook appended its marker after the LifeOS sidecar transformed a tool result.
- Thirteen bridge tests exercise real command processes, a local HTTP server, context, blocking, task governance, argument changes, transcript creation, and permission grants. Eighteen focused Hermes tests passed after the first two generic core changes.
- The installed LifeOS safety hook granted a synthetic `/tmp` removal in the test account. It abstained on a `sudo systemctl restart`, and Hermes kept its hardline block on `rm -rf /`. Fifty-five focused Hermes approval tests passed with the new event.

## Hermes core dependency

The stock Hermes plugin API cannot continue a non-coding turn from a Stop hook. It also keeps only the first tool-result replacement, so the existing LifeOS sidecar can mask another plugin's `additionalContext`. Its approval hooks observe requests but cannot grant one. The test fork adds three generic plugin events: `pre_turn_stop`, `augment_tool_result`, and `pre_command_approval`. The [patch](../patches/hermes-hook-controls.patch) is based on Hermes commit `758ad514e` and includes its tests. It must be reviewed and applied to a compatible Hermes checkout before enabling this plugin. The isolated test fork has the change on branch `feature/universal-stop-hook` at commit `56df3225c`; production Hermes is unchanged.

## Current limits

- Full hook parity is not achieved. `PermissionRequest` for file and MCP approvals, `ConfigChange`, and `StopFailure` need explicit Hermes event and approval contracts. The `TaskCreated` adaptation does not cover kanban task creation. The command grant currently applies only in manual approval mode. Hermes smart approval keeps its own decision path.
- The bridge creates a private Claude-shaped transcript from the events it sees. It is sufficient for the tested Stop gates, but it is not a byte-for-byte Claude Code transcript. Hook behavior that depends on Claude-specific transcript entries needs separate verification.
- Async LifeOS hooks are started as child processes and their output is not injected. A short-lived Hermes process can exit before an async child completes.
- LifeOS's nested inference tool clears local gateway variables. The optional `bin/claude` child launcher restores private gateway settings and maps model and effort flags. This still requires the Claude Code CLI as a child helper; Hermes remains the main conversation agent.
- The isolated test account uses LAN-only outbound rules. The plugin does not install a firewall or credentials.

## Test installation

The test account has a fresh LifeOS tree and a `~/.claude/settings.json` created by `InstallHooks.ts --apply`. The plugin files live under `~/.hermes/plugins/lifeos-hook-bridge/`, and `hermes plugins enable lifeos-hook-bridge` enables them. The existing LifeOS sidecar guard remains enabled. The private `~/.config/lifeos-hook-bridge/model.env` file supplies the local model gateway to the child launcher and has mode `0600`. Keep that file outside Git.

The core patch applies only to a compatible Hermes checkout. On a new branch, run `git apply --check /path/to/lifeos-hermes-plugin/patches/hermes-hook-controls.patch` from the Hermes checkout, then apply it and run the included tests. Do not apply the patch to an unrelated Hermes version without reviewing the changed call sites.
