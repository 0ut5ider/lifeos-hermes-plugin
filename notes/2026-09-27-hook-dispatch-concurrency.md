# 2026-09-27: First block skipped later hooks

The bridge originally executed matching native hooks in settings order and returned immediately when a PreToolUse or Stop hook blocked. The Claude Code hook reference says all matching handlers run in parallel. A two-handler test confirmed the difference: a blocking first handler prevented a later observer from writing its marker.

Another test used two command hooks that waited for each other's marker. Sequential dispatch failed after about one second because the second process had not started. The bridge now starts matching synchronous command and HTTP hooks in a bounded worker pool, waits for all results, and combines decisions in settings order. Both tests pass. A direct run of the installed LifeOS Stop hooks completed in 1.64 seconds on the isolated test account.

The bridge still does not support Claude Code `prompt`, `agent`, or `mcp_tool` hook handler types. The installed LifeOS hook settings used here contain command and local HTTP handlers.
