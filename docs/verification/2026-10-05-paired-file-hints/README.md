# Paired file hints with real Write and Edit calls

Date: 2026-10-05. Three cases exercise the native AtlasEventCapture and ConfigEvalFire hooks through real file tool calls in Claude Code 2.1.272 and Hermes. All six clients complete with status zero, and every model request succeeds.

The native client runs with the Write tool, or the Read and Edit tools, in the `acceptEdits` permission mode. Hermes runs with the file toolset. The hook input names tool `Write` or `Edit` and the exact absolute file path on both clients.

| Case | Operation | Required effect | Result |
| --- | --- | --- | --- |
| Tracked write | Write `PROJECTS.md` | The file has the requested content. One `projects` hint for tool `Write` for each call. No evaluation state. | Both clients pass. |
| Untracked write | Write `notes.md` | The file has the requested content. No hint. No evaluation state. | Both clients pass. |
| Tracked edit | Replace one line in `GEAR.md` | The other lines stay unchanged. One `gear` hint for tool `Edit` for each call. No evaluation state. | Both clients pass. |

Every case preserves an earlier unrelated row in the events file. Both hooks return no output.

[file-hint-proof.json](file-hint-proof.json) independently reads the raw captures. It checks every hook payload, the matcher, the final file content, the appended rows, each row timestamp against the client interval, the absent evaluation state, and every response status. Each client folder retains its raw `atlas-events.jsonl` and the final target file.

[runtime-check.json](runtime-check.json) verifies all 16,925 prepared source files and records 603 native program hashes. Full model wire bodies remain private outside Git. No product code changes in this unit.

## Limits and deferred work

The model selects the number of file calls. An earlier attempt had two native Edit calls, so each case requires at least one call and one hint for each call. This run has one call in every client. The final answer text is not compared; an earlier native answer added prose after the write.

For ConfigEvalFire, these cases cover only the branch for a file that is not a sentinel. A sentinel case that writes a file named `CLAUDE.md` is deferred. In the exploratory run, Hermes printed `Preparing the isolated Hermes runtime` after the write call and did not finish within 120 seconds. A later [measurement](../../../notes/2026-10-05-instruction-file-write-gate.md) shows the cause: Hermes has an approval gate for instruction file names, and the plugin is not involved. The sentinel case needs another file name.

The KnowledgeWriteGuard hook needs a write inside the LifeOS memory tree, outside the project directory. That case needs a separate permission design and remains open.

The new required-effect tests fail before the final expectations ([before-output.txt](before-output.txt)); the exploratory driver accepted any equal state at that point. The focused suite passes 96 tests. The cumulative ledger contains 77 equal selected cases for 28 registrations. Complete compatibility remains unverified.

The two clients run different LifeOS trees: the installed reference tree and the patched prepared tree. See [source differences](../../parity/source-differences.md).
