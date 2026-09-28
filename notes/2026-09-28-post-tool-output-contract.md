# Post-tool hook output contract

On 2026-09-28, I checked the bridge against the [Claude Code hook output contract](https://code.claude.com/docs/en/hooks#exit-code-0). Claude Code sends successful plain stdout to its debug log for `PostToolUse` and `PostToolUseFailure`. It sends exit-code-2 stderr to the model as feedback after the tool has run.

A real synthetic `PostToolUse` command printed `PLAIN_DIAGNOSTIC_ONLY` and exited zero. The bridge returned that string as model-bound context. Two red regression tests reproduced the same problem for successful and failed tool events. Two more red tests showed that exit-code-2 stderr was lost for both events.

The bridge now accepts plain stdout as context only for SessionStart and UserPromptSubmit, which are the supported events it currently maps. It appends exit-code-2 stderr after post-tool JSON context. The four focused regressions and the existing SessionStart, UserPromptSubmit, and JSON post-tool context tests pass locally. All 118 tests passed on `.212` with the patched native LifeOS checkout and Bun available. The installed bridge file matched the tested source by SHA-256. After the dashboard restart, its status endpoint returned HTTP 200.
