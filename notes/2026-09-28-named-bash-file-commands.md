# Named Bash files and Claude Code Read rules

Date: 2026-09-28. Claude Code 2.1.272 ran in the isolated `.212` reference account through its private local model. Each probe used a disposable file, a matching Bash allow, the default permission mode, and JSON output. The paired control had no Read deny. The second run added a Read deny for the named file. The JSON `permission_denials` array and the actual Bash `tool_input` determined the result, rather than the model's prose.

| Bash command | Control denials | Read deny denials | Observation |
| --- | ---: | ---: | --- |
| `wc -c parity-file` | 0 | 1 | File read blocked. |
| `grep PATTERN parity-file` | 0 | 1 | File read blocked. A fresh marker was absent from the denied run. |
| `stat parity-file` | 0 | 1 | Named target blocked. |
| `diff parity-file other` | 0 | 1 | Named target blocked. |
| `sort parity-file` | 0 | 1 | Exact command blocked on a repeat probe. |
| `ls parity-file` | Not paired | 1 | Named target blocked. |
| `file parity-file` | Not paired | 1 | Named target blocked. |
| `find parity-file -maxdepth 0` | Not paired | 1 | Named starting point blocked. |
| `du parity-file` | Not paired | 0 | Read deny did not block the exact command. |

One denied `sort` attempt was inconclusive because the model changed the command to an in-place sort. Repeating with the exact command established the one-denial result. One denied `grep` response appeared to echo a previous marker even though the permission result denied the command. A second probe with a new random marker returned one denial and no marker. The model's response text cannot serve as proof that a tool executed.

The bridge previously found no file target for these commands. It now extracts literal file operands for the eight measured command families and applies Read rules before a Bash allow can grant the command. It extracts an output target for `sort -o` and checks Edit rules. Unknown option forms remain on the review path. It leaves `du` outside this recognized set because the observed Claude Code behavior did not enforce the Read deny there.

The local suite passed 277 tests with 66 optional skips. The `.212` source suite passed 277 tests with 55 optional skips. Focused live SSH and Docker tests on `.212` denied each of the nine named file command forms (`cat` plus the eight new families) when a symlink pointed outside the project to a Read-denied file. A direct Read of the symlink was also denied. The parser covers literal names and selected options; it does not establish parity for every command option, dynamic argument, or compound expression.
