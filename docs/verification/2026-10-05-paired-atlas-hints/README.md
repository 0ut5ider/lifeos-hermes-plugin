# Paired mutation hints with real tool calls

Date: 2026-10-05. Three cases exercise the native AtlasEventCapture hook through actual Claude Code 2.1.272 and Hermes clients. This is the first unit in which the model runs a real tool call. All six clients complete with status zero and two successful private FlashNext responses: the tool request and the final answer.

Each prompt gives one exact `printf` command. The command only prints text, and the text contains the pattern that the hook reads. The native client runs with the Bash tool and the default permission mode. Hermes runs with the terminal toolset.

| Case | Command text | Required effect | Result |
| --- | --- | --- | --- |
| systemd | `systemctl --user daemon-reload` | Append one `systemd` hint for tool `Bash`. | Both clients pass. |
| plain | No tracked pattern | Append nothing. | Both clients pass. |
| multiple | `gh repo create` and `launchctl load` | Append a `github` hint and a `launchd` hint in that order. | Both clients pass. |

Every case preserves an earlier unrelated row in the events file. The hook input names tool `Bash` and carries the exact command on both clients.

[hint-proof.json](hint-proof.json) independently reads the raw captures. It checks the PostToolUse payload, the exact command, the tool output marker, the matcher, the appended rows, each row timestamp against the client interval, and both response statuses. Each client folder retains its raw `atlas-events.jsonl`.

[runtime-check.json](runtime-check.json) verifies all 16,925 prepared source files and records 603 native program hashes. Full model wire bodies remain private outside Git. No product code changes in this unit.

The new required-effect tests fail before implementation ([before-output.txt](before-output.txt)). The focused suite passes 79 tests. These selected cases leave the cloudflare and DNS patterns, the file-edit branches of this hook, interrupted clients, and complete groups open. The cumulative ledger contains 68 equal selected cases for 19 registrations. Complete compatibility remains unverified.
