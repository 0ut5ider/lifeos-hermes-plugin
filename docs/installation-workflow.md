# Plugin-managed LifeOS installation

The intended order is Hermes, LifeOS Bridge plugin, then LifeOS. The plugin must load before LifeOS exists so its settings page can guide installation. An absent `~/.claude/settings.json` now leaves its hooks inactive without making the plugin fail to load.

## Requested page flow

1. The page checks whether LifeOS is missing, partial, or installed.
2. **Prepare latest LifeOS** reads the current commit of [Daniel Miessler's public repository](https://github.com/danielmiessler/LifeOS), clones that exact revision, applies the bundled LifeOS patches, and publishes a private candidate. It changes no running files.
3. An install action must review that candidate, run the LifeOS installation tools, preserve existing Hermes configuration and user files, verify the deployed hooks, and recover from failure. This action is not implemented yet.
4. After installation, the page explains the stock Hermes limits. Leaving Hermes stock selects reduced mode. A separate action will prepare and apply the tested Hermes patch set for the extended mode. That action is not implemented yet.
5. Updates must repeat the revision, patch, test, and rollback checks. The existing release transaction covers code and LifeOS system files but does not yet update dependencies or hook registrations.

The latest upstream LifeOS commit was `5e2f2e8c0abde612da0e99c16c0d07d4ec21b88c` when checked on 2026-09-29. That is the current tested base. If upstream moves, preparation refuses the new commit until its patch set and behavior tests are ported. A clean patch application alone is not a parity result. The page must not label an untested future commit as compatible.

## Reduced mode with stock Hermes

The runtime registers only hooks present in the pinned stock Hermes source. Its manifest validated without findings against that source on `.212`. The reduced path is an experimental integration and does not provide the LifeOS safety contract:

| LifeOS behavior | Stock Hermes path | Limit |
| --- | --- | --- |
| PreToolUse | `pre_tool_call` | The callback can inspect tool calls. This mode still needs a live paired tool run. |
| PostToolUse and PostToolUseFailure | `post_tool_call` observer | Native handlers can run and record side effects. Their returned advice is not reliably appended after another result transformer. |
| SessionStart and UserPromptSubmit | `pre_llm_call` | Context can be added. A LifeOS prompt block is not enforced by the stock host. |
| SessionEnd and API request errors | Stock lifecycle events | Handlers can run when the host emits those events. Exact reason and restart coverage remains open. |
| Bash PermissionRequest | No equivalent command approval callback | LifeOS Bash permission allow, ask, deny, and replacement decisions are not enforced. Hermes keeps its own approval rules. |
| Command policy on every Bash call | No extended command-policy callback | LifeOS cannot check a command that stock Hermes would run without an approval warning. Manual allowlists, prepared desktop approvals, and bypass modes do not receive the tested LifeOS denial precedence. |
| PermissionRequest replacement | No tested command replacement and recheck path | A native hook cannot safely substitute a Bash command and have the replacement checked again before execution. File and Model Context Protocol replacement still need separate stock-host validation. |
| Stop answer gates | No pre-delivery continuation or failure callback | LifeOS cannot withhold a rejected answer before delivery and history persistence. |
| Child model route | No tested per-child provider and effort contract | The plugin cannot promise Hermes provider selection for each LifeOS tier. |
| Remote file guard | No tested stale-write patch | SSH and Docker whole-file writes lack the tested guard supplied by our Hermes patch. |
| Nested tool identity | No tested `execute_code` session propagation | Inner tool calls can lose the parent LifeOS session and transcript identity. |
| Session reasons | Basic finalization event only | Empty-session clear and resume, prompt exit, and gateway resume lack the tested reason paths supplied by the patch set. |
| Turn completion and watchdog activity | No `on_turn_result` callback | The bridge cannot observe the tested final-turn activity signal used by its watchdog and transcript cleanup. |
| Scheduled worker runtime | No tested cron worker bootstrap patch | A source installation can start a worker outside the managed dependency environment needed by this plugin. |

The patched source exposes the missing hooks and fixes additional command, model, session, and worker paths. It is still an experimental compatibility set. Full parity requires the paired registration matrix and live release checks in the [resolution plan](parity-resolution-plan.md).
