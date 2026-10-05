# Paired pre-tool guard decisions

Date: 2026-10-05. Three cases exercise the native PreToolGuard hook through real Bash tool calls in Claude Code 2.1.272 and Hermes. All six clients complete with status zero and two successful private FlashNext responses.

The registration uses the pinned matcher `Bash|Write|Edit|MultiEdit`. Each command prints a marker that the command text does not contain, so the marker in the next model request proves execution.

| Case | Command | Required effect | Result |
| --- | --- | --- | --- |
| Unsafe extract | `plutil -extract` without `-o` | Hook exit code 2 with the guard message. The command does not run. The next model request contains the guard message. | Both clients pass. |
| Safe extract text | The same words with `-o -` | Hook exit code 0. The command runs and its output reaches the model. | Both clients pass. |
| Plain | No guarded pattern | Hook exit code 0. The command runs and its output reaches the model. | Both clients pass. |

[guard-proof.json](guard-proof.json) independently reads the raw captures. It checks the PreToolUse payload, the exact command, the hook exit code and message, the first and second model requests, the empty project directory, and both response statuses.

[runtime-check.json](runtime-check.json) verifies all 16,925 prepared source files and records 603 native program hashes. Full model wire bodies remain private outside Git. No product code changes in this unit.

The new required-effect tests fail before implementation ([before-output.txt](before-output.txt)). The focused suite passes 83 tests. These cases cover one of the six Bash guards. The file guards for Write and Edit, the other Bash guards, interrupted clients, and complete groups remain open. The cumulative ledger contains 71 equal selected cases for 20 registrations. Complete compatibility remains unverified.
