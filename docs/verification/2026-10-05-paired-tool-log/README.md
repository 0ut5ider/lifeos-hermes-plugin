# Paired tool logging and loop alerts

Date: 2026-10-05. Three cases exercise the native EventLogger and LoopDetector hooks through real shell tool calls in Claude Code 2.1.272 and Hermes. All six clients complete with status zero, and every model request succeeds.

| Case | Event and hooks | Required effect | Result |
| --- | --- | --- | --- |
| One successful call | PostToolUse: EventLogger (pinned `async: true`, timeout 5) and LoopDetector | One `tool_use` activity row with the command as ground truth. Loop state with one successful entry and no alert. | Both clients pass. |
| Three identical calls | PostToolUse: LoopDetector | The third call emits the loop alert. The state records one alert at call 3. A later model request contains the alert. | Both clients pass with exactly three calls. |
| One failing call | PostToolUseFailure: EventLogger and LoopDetector | One `tool_failure` row that names exit code 2. Loop state with one failed entry. No activity row. | Both clients pass. |

The failing command is `ls pair-missing-tool-log` inside the project directory. Both clients route it to PostToolUseFailure. This case registers no PostToolUse hook, so it cannot show that a PostToolUse event is absent.

[tool-log-proof.json](tool-log-proof.json) independently reads the raw captures. It checks every hook payload, the registration settings, the log rows, the loop state file, the alert position, the later model requests, and every response status.

[runtime-check.json](runtime-check.json) verifies all 16,925 prepared source files and records 603 native program hashes. Full model wire bodies remain private outside Git. No product code changes in this unit.

## Recorded differences

An independent review found two differences that the summaries do not compare. Both are confirmed in the raw rows.

- Successful call. The native activity row has `stdout_preview`, `stdout_bytes`, and `stderr_preview`. The Hermes row has `combined_output_preview`, `combined_output_bytes`, and `exit_code`. Hermes gives the hook one combined output stream. The check compares only the command.
- Failing call. The native failure row has the error `Exit code 2` followed by the `ls` message. The Hermes row has the error `exit 2` without the message. The check requires only the digit 2.
- Tool input. The native input has a `description` field that the Hermes input lacks. The check compares only the command.

The two clients also run different `EventLogger.hook.ts` files. See [source differences](../../parity/source-differences.md). These cases therefore show equal events, equal row kinds, and an equal command. They do not show equal row content.

## Limits and deferred work

The repeat case requires at least three calls, because the model selects the number of calls. This run has exactly three calls on both clients. The checks use the first three calls.

Exploratory runs found three native control limits. Claude Code refuses `exit 3` and a listing outside the project in the default permission mode, so neither command reaches the failure event. In one exploratory run the native model sent three calls in one response; the three concurrent hook processes then wrote the loop state at the same time and no alert appeared. That concurrent case is native behavior and is not compared here.

The PostToolObserver repeat case is deferred. In three exploratory runs the native model made two, three parallel, and five calls, so the case has no stable control.

This unit also adds two protections to the driver after the fixture host ran out of disk space. A run stops when the host has less than 2 GiB free. The driver removes the Hermes tool program cache, about 360 MB for each new profile, after each case.

The new required-effect tests fail before the final expectations ([before-output.txt](before-output.txt)); the exploratory driver accepted any equal state at that point. The focused suite passes 91 tests. The cumulative ledger contains 74 equal selected cases for 24 registrations. Complete compatibility remains unverified.

The two clients run different LifeOS trees: the installed reference tree and the patched prepared tree. See [source differences](../../parity/source-differences.md).
