# Installed permission controls

Date: 2026-10-06. Target: disposable local profiles with the prepared source bundle.

Sixteen controls execute the actual Hermes Bash, Write, Edit, and multi-file patch dispatcher. Each target receives allow, deny, ask with one approval, and ask with rejection. The controls verify the changed or unchanged target bytes and approval callback count. A denied batch leaves its first target unchanged. [permission-results.json](permission-results.json) records each result; [permission-trace.jsonl](permission-trace.jsonl) retains the actual arguments and tool output.

Four additional controls register and call the real fixture MCP stdio transport. Allowed and approved calls return the server marker. Denied and rejected calls return an error before the server result. [mcp-results.json](mcp-results.json) retains those results. These are installed dispatcher controls with explicit operator callbacks. They do not claim an interactive panel or a Discord round trip.

The MCP baseline ignores an explicit deny rule and returns the fixture server marker. The bridge correction evaluates current user, project, and managed rules before transport execution. Deny takes precedence. Ask and malformed policy require review even when the native Safety hook grants permission. An explicit allow follows the native permission contract. Pre-tool guards and Hermes transport security still apply.

The focused gate passes 214 tests with two missing source bindings. [required-repeat.txt](required-repeat.txt) repeats those two native controls with the required bindings. Their output records whether the repeat passes. The additional rules tests cover a changed policy after a grant, managed denial, managed-only rules, and malformed managed policy. Full interactive cancellation and remote permission acceptance remain separate scenarios.
