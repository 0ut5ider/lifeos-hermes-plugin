# Claude Code permission reference probe

Date: 2026-09-28. The isolated Claude Code reference account on `.212` ran against the private LAN model. A disposable settings file registered `PreToolUse` and `PermissionRequest` hooks for Bash. Each hook used the same Python logger; the permission hook would deny if invoked.

The first one-shot prompt produced no Bash tool call and no hook event. A second prompt with stream JSON did produce two Bash tool calls. The first, `echo 12345`, returned tool error `Exit code 1` with no output. The second, a compound echo command, returned a request for approval of one command part. The disposable hook event log stayed empty during both calls. Feeding a PreToolUse payload directly to the same logger wrote one event, so the logger itself was runnable.

This probe does not establish Claude Code's PermissionRequest trigger rules. It shows that the current one-shot reference setup did not deliver these Bash events to the disposable hooks, despite delivering disposable Stop hooks in a separate test. Before changing the Hermes permission contract, inspect Claude Code's effective hook registration and tool failure path in this reference setup. No test command with a permission request was executed.
