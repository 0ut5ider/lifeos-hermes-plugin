# Hook compatibility controls

Date: 2026-10-03. Target: Claude Code 2.1.272, public LifeOS `5e2f2e8`, and the current plugin compatibility package.

The September 29 fixture listed 100 MCP tools without native `ToolSearch`. That did not establish a tool-count limit. The current [Claude Code environment documentation](https://code.claude.com/docs/en/env-vars) says a custom API endpoint disables MCP tool search by default. A disposable profile copy on `.212` tested `ENABLE_TOOL_SEARCH=false` and `true` against the same loopback model-alias proxy and private LAN model. The false control listed 125 tools without `ToolSearch`. The true control listed 126 tools, called `ToolSearch`, returned a `tool_reference` result, and ran `PostToolUse.5.1` with exit code zero. `MultiEdit` was absent in both inventories.

The true control then failed at the next model request with HTTP 400, `Unexpected item type in content.` The private gateway does not accept the returned `tool_reference` content. The successful search event is usable registration evidence. The session is not a successful search-and-MCP-call control. No proxy translation was added to conceal that limitation.

The pinned binary contains `CLAUDE_CODE_MAX_RETRIES`. Setting it to zero made the loopback 401 control finish in 0.817 seconds rather than reaching the previous 45-second timeout. Print mode displayed the authentication failure but still did not run `StopFailure.1.1`. An interactive control is the next test. This setting is an observed fixture control, not a documented public interface.

The native handler suite initially ran 46 tests with one missing inference fixture. A private model environment and the plugin child launcher enabled the prompt naming test. The repeat passed all 46 tests without skips in 15.798 seconds. These tests check real native handlers and selected filesystem effects. They do not establish all 74 paired registration effects.

Raw outputs remain in private fixture directories. The final evidence bundle will include commands, sanitized results, source hashes, and the remaining limits.
