# LifeOS hook parity record

This record describes the public LifeOS hook settings installed from commit `5e2f2e8` on 2026-09-27. It distinguishes registered callbacks from verified behavior. The bridge is a Hermes plugin. It does not edit LifeOS source files.

## Event coverage

| Claude Code event | Registrations | Hermes path | Current result |
| --- | ---: | --- | --- |
| `PreToolUse` | 6 | `pre_tool_call` | Command and local HTTP hooks execute for mapped tools. Exit code 2 and deny decisions block. Updated input maps back to Hermes arguments. |
| `PostToolUse` | 32 | `augment_tool_result` | Hooks execute after the existing result transform. Their `additionalContext` is appended to the model-bound result. |
| `UserPromptSubmit` | 9 | `pre_llm_call` | Hooks execute on text and multimodal prompts. For multimodal content, the hook receives the text portions joined with newlines. Their context is added to the current user turn. Async hooks start without blocking. |
| `Stop` | 8 | `pre_turn_stop` | Hooks execute on each text answer. A block continues the same Hermes turn, up to eight consecutive times by default. `CLAUDE_CODE_STOP_HOOK_BLOCK_CAP` overrides the cap. A private transcript supplies `transcript_path`. |
| `SessionStart` | 5 | first `pre_llm_call` | Hooks execute before the first user prompt is sent to the model. Their text output joins that prompt's context. |
| `SessionEnd` | 6 | `on_session_finalize` | All six installed handlers completed successfully on a synthetic session boundary. Their state-changing effects have not been checked end to end. |
| `PostToolUseFailure` | 3 | `augment_tool_result` on tool error | The failure payload is tested with a real child process. |
| `PermissionRequest` | 2 | `pre_command_approval` for Bash and `pre_tool_call` for files and MCP | Native `Safety.hook.ts` can grant a recoverable dangerous-command warning in Hermes manual approval mode. Hermes hardline, user deny, and Tirith warnings remain effective. For Write, Edit, and MCP, a native grant proceeds; a neutral decision requests human review, and a deny blocks. Hermes file guards still apply after a grant. |
| `TaskCreated` | 1 | `pre_tool_call` and `post_tool_call` on `todo_list` and `kanban_create` | The bridge enforces the installed hook's minimum description and shared 50-task session limit. Slots are reserved before a call and committed only after success. This is equivalent policy code, not native hook execution. |
| `ConfigChange` | 1 | bridge file watcher while a session is active | Installed user, project, local, and file-based managed settings plus user and project skills are checked once a second. Native hooks receive `source`, `file_path`, and LifeOS's `config_path` alias. A block keeps the active user hook settings. |
| `StopFailure` | 1 | `api_request_error` plus `on_turn_result` | Terminal API errors run the native log hook once with the last API error. Direct error returns and exhausted retries are covered. An earlier recovered API error does not turn an unrelated local failure into StopFailure. |

The native bridge executes the installed registration types with partial coverage of `ConfigChange` and Bash `PermissionRequest`. The MCP `PermissionRequest` registration executes, but Hermes's trusted-server policy can still differ from Claude Code's permission rules. Write and Edit permissions now execute the native hook, but Hermes file guards and a multi-file patch's approval scope can differ from Claude Code. The bridge also enforces the `TaskCreated` policy for new Hermes todo IDs and kanban task calls without executing that native hook. This is an event-level mapping, not a count of passing behavioral tests. Hermes tool names currently mapped are `terminal`, `read_file`, `write_file`, `patch`, `clarify`, `delegate_task`, `web_search`, `web_fetch`, `skill_view`, `tool_search`, and `mcp__*`. Hermes `clarify` maps to Claude Code `AskUserQuestion` for the installed tab-state hooks. Claude Code `MultiEdit` has no exact Hermes tool mapping. The LifeOS `Agent` HTTP hook uses fields that Hermes delegation does not always supply. Local Pulse routes fail open when Pulse is not running, as they do in Claude Code.

## Verified effects

- The plugin validates and loads in the isolated Hermes account.
- A real Hermes turn reads the synthetic principal as `Test Operator` and includes LifeOS memory context.
- A native LifeOS child inference call returns `READY` through the local model. The model tier is translated, so tier selection is not verified.
- A temporary Stop hook blocked the first answer. Hermes continued and produced a second answer. The hook saw `stop_hook_active: false` followed by `true`.
- Native LifeOS Format, Verification, and Writing gates wrote observability records from a Hermes turn after the bridge supplied a transcript.
- A temporary PostToolUse hook appended its marker after the LifeOS sidecar transformed a tool result.
- Forty-one bridge tests exercise real command processes, a local HTTP server, context, blocking, task governance, argument changes, transcript creation, permission grants, failure logging, config changes, multi-file patch guards and audit, clarification hooks, concurrent hook dispatch, async process survival, and session boundary registration. One hundred sixteen focused Hermes agent and plugin tests passed after the turn result change.
- The installed LifeOS safety hook granted a synthetic `/tmp` removal in the test account. It abstained on a `sudo systemctl restart`, and Hermes kept its hardline block on `rm -rf /`. Fifty-five focused Hermes approval tests passed with the new event.
- A synthetic terminal API error reached the installed native LifeOS StopFailure logger once. The test account contains its JSONL record.
- A synthetic direct authentication failure also reached the installed native LifeOS StopFailure logger. A real Hermes 401 turn test confirmed the observer event fires on that direct return path.
- A synthetic task-specific workspace on `.212` reached a Bash PreToolUse hook as both the payload `cwd` and the child process working directory.
- A multimodal first prompt triggered SessionStart and UserPromptSubmit in order, with its text portion in the latter payload.
- A synthetic settings change reached the installed native LifeOS ConfigChange logger. The test account contains its JSONL record.
- An idle synthetic session detected a project local settings change without a new prompt or tool result. The installed LifeOS logger recorded the changed filename after the bridge supplied its `config_path` alias.
- The installed LifeOS MCP permission hook allowed an ordinary synthetic message and requested review for a synthetic token-shaped message. Hermes blocked the latter in an unattended session.
- The installed LifeOS file permission hook granted a synthetic write under `~/.claude` and requested review for synthetic Write and Edit calls to a credential path. No file write was executed.
- Matching synchronous hook handlers now run concurrently. A blocking PreToolUse handler does not suppress another matching observer. A direct run of the installed Stop hooks completed with this dispatch path.
- An async hook read a one-megabyte synthetic prompt after its parent Hermes process exited. The detached runner removed its private spool file.
- All six installed SessionEnd handlers returned exit code zero for a synthetic session on `.212`.

## Hermes core dependency

The stock Hermes plugin API cannot continue a non-coding turn from a Stop hook. It also keeps only the first tool-result replacement, so the existing LifeOS sidecar can mask another plugin's `additionalContext`. Its approval hooks observe requests but cannot grant one. The test fork adds four generic plugin events: `pre_turn_stop`, `augment_tool_result`, `pre_command_approval`, and `on_turn_result`. It also preserves updated tool arguments when a plugin requests approval. The [patch](../patches/hermes-hook-controls.patch) is based on Hermes commit `758ad514e` and includes its tests. It must be reviewed and applied to a compatible Hermes checkout before enabling this plugin. The isolated test fork has the change on branch `feature/universal-stop-hook` at commit `73d7814e2`; production Hermes is unchanged.

## Current limits

- Full hook parity is not achieved. The `TaskCreated` adaptation uses equivalent policy code rather than the installed native hook. The command grant currently applies only in manual approval mode. Hermes smart approval keeps its own decision path. File permission prompts happen before Hermes file guards and can result in a second approval prompt for an SSH config write.
- Config changes are detected within the watcher's one-second polling interval while a session is active, rather than through a filesystem event. The watcher stops when no session remains. Project files are based on Hermes's process working directory when the plugin loads; a later workspace change is not followed. File-based managed policy paths are audited but Hermes does not apply Claude Code's managed settings. Server-managed settings, macOS managed preferences, and Windows registry policy have no bridge event.
- A successful Hermes multi-file patch is presented to `Edit` PreToolUse, PermissionRequest, and PostToolUse hooks once per changed, deleted, or moved path. Added and updated files include the added text. A failed patch produces one PostToolUseFailure event with the original Hermes patch shape. The private transcript still records the original patch tool call. Hook `cwd` follows Hermes's task workspace for a local backend and an explicit terminal `workdir` when supplied. Remote or container backends still need separate path fidelity tests.
- The bridge creates a private Claude-shaped transcript from the events it sees. It is sufficient for the tested Stop gates, but it is not a byte-for-byte Claude Code transcript. Hook behavior that depends on Claude-specific transcript entries needs separate verification.
- Multimodal prompts pass text portions to UserPromptSubmit. Image and attachment content remains in the bridge transcript but is not represented in the prompt string, so hooks that interpret that content can differ from Claude Code.
- Async LifeOS hooks run through a detached child process with a private spool file so a one-shot Hermes process can exit without truncating their input. Hook output is not injected into the model. A service manager that kills an entire process group or control group can still stop the child.
- LifeOS's nested inference tool clears local gateway variables. The optional `bin/claude` child launcher restores private gateway settings and maps model and effort flags. This still requires the Claude Code CLI as a child helper; Hermes remains the main conversation agent.
- The isolated test account uses LAN-only outbound rules. The plugin does not install a firewall or credentials.

## Test installation

The test account has a fresh LifeOS tree and a `~/.claude/settings.json` created by `InstallHooks.ts --apply`. The plugin files live under `~/.hermes/plugins/lifeos-hook-bridge/`, and `hermes plugins enable lifeos-hook-bridge` enables them. The existing LifeOS sidecar guard remains enabled. The private `~/.config/lifeos-hook-bridge/model.env` file supplies the local model gateway to the child launcher and has mode `0600`. Keep that file outside Git.

The core patch applies only to a compatible Hermes checkout. On a new branch, run `git apply --check /path/to/lifeos-hermes-plugin/patches/hermes-hook-controls.patch` from the Hermes checkout, then apply it and run the included tests. Do not apply the patch to an unrelated Hermes version without reviewing the changed call sites.
