# 2026-09-27: MCP permission hooks exposed a different trust model

LifeOS `Safety.hook.ts` auto-allows ordinary MCP input but returns no grant when its serialized arguments contain a secret-shaped value. Claude Code then falls through to its permission engine. Hermes's trusted MCP path can otherwise proceed without a prompt, so simply running the LifeOS hook as an observer would leave that secret egress path open.

The plugin now runs the native MCP PermissionRequest hook before dispatch. An explicit grant proceeds. A neutral result asks Hermes for human approval with a per-input hash key; a native deny blocks. The approval reason omits the tool arguments. A real test with the installed public LifeOS hook allowed an ordinary synthetic message and required approval for a synthetic token-shaped message. A second test drove Hermes's pre-tool dispatcher without a human channel; it blocked before any MCP call.

This is stricter than Claude Code when a separate Claude permission allow rule would approve the neutral input. Hermes's untrusted-server consent gate remains in force after the LifeOS decision. The mapping closes the tested egress case, but it does not reproduce every Claude permission rule.
