# Paired MCP result and permission

Date: 2026-10-05. Two cases call the tool `ping` of a synthetic MCP stdio server, [paired-mcp-server.py](paired-mcp-server.py), in Claude Code 2.1.272 and Hermes. All four clients pass.

| Registration | Setting | Required effect |
| --- | --- | --- |
| `PostToolUse.4.1` (Safety, matcher `mcp__.*`) | Claude Code allows `mcp__pair__ping` | The hook returns its external-content warning. A later model request contains the tool result and the warning. No LifeOS file changes. |
| `PermissionRequest.2.1` (Safety, matcher `mcp__.*`) | The tool is not allowed in advance | The hook answers `allow`. Both clients write the decision row and the permission cache. |

The hook input names `mcp__pair__ping` on both clients. Hermes reports the tool result as `{"result": ...}`; Claude Code reports a list of text blocks. Hermes also wraps the result in its own untrusted-content block before the LifeOS warning.

## Request count

Hermes makes three model requests and Claude Code two. Hermes loads MCP tools through an additional discovery request. The MCP cases therefore join the cases where the model or host chooses the request count; the ledger compares every other field.

[mcp-proof.json](mcp-proof.json) recomputes the changed files from the raw captures, checks the hook input and decision, and finds the tool result and the warning in the model requests. [runtime-check.json](runtime-check.json) verifies the 18,153 runtime files. See [source differences](../../parity/source-differences.md).

The focused suite passes 115 tests. Each case is one selected branch. The cumulative ledger contains 102 equal selected cases for 57 registrations. Complete compatibility remains unverified.
