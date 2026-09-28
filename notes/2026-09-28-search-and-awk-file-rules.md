# Search and text command file rules

Date: 2026-09-28. Claude Code 2.1.272 ran in the isolated `.212` reference account through its private local model. Each exact command had a matching Bash allow. The control had no Read deny. The second run denied Read on the named file. The denied JSON responses included the exact Bash `tool_input`, so command rewriting did not explain the result.

| Bash command | Control denials | Read deny denials |
| --- | ---: | ---: |
| `rg parity parity-file` | 0 | 1 |
| `cut -c 1-6 parity-file` | 0 | 1 |
| `awk '{print $1}' parity-file` | 0 | 1 |

Before this change, `HookBridge.command_approval` returned no block for all three commands under the same rules. A regression returned `None` instead of `{"action":"deny"}` for each. The bridge now extracts literal file operands for those commands, checks the requested and resolved paths, and blocks a matching Read deny. It also treats `rg -f` and `awk -f` as file arguments. Unknown option forms request review.

An `awk` program can open a file internally. A separate native probe ran `awk 'BEGIN { getline line < "secret"; print line }'` with a matching Bash allow and `Read(./secret)` denied. Claude Code reported zero permission denials and returned the synthetic file content. The bridge likewise checks explicit operands and does not parse the `awk` program for hidden file reads. Hermes's independent command safety policy still applies. This is a measured permission boundary, not a claim that such a program is safe.

The final local suite passed 278 tests with 66 optional skips. The `.212` source suite passed 278 tests with 55 optional skips. Focused live SSH and Docker tests on `.212` denied twelve named file command forms when a symlink pointed outside the project to a Read-denied file. A direct Read of that symlink was also denied. The Docker test removed its container, and the temporary socket access entry was removed.
