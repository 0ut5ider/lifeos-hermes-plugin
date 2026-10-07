# Paired tool failure text

Date: 2026-10-05. This unit repeats the three tool logging cases after a bridge correction. It replaces the earlier [tool logging unit](../2026-10-05-paired-tool-log/README.md) in the ledger. All six clients complete with status zero, and every model request succeeds.

## What changed

For a failed terminal command, the bridge sent only the short Hermes status `exit 2`. Claude Code sends the exit code and the command output. Commit `818c5d3` corrects the bridge. Both clients now write this identical error text to the failure log:

```
Exit code 2
ls: cannot access 'pair-missing-tool-log': No such file or directory
```

The check now requires that exact text. It also requires the recorded command output in the activity row.

## Accepted host differences

Adrian accepts two differences on 2026-10-05. [tool-log-proof.json](tool-log-proof.json) asserts them for each side, so another difference in these rows fails the proof.

- Output fields. Claude Code records `stdout_preview`, `stdout_bytes`, and `stderr_preview`. Hermes gives one combined stream, so its row has `combined_output_preview`, `combined_output_bytes`, and `exit_code`. Both rows contain the command output.
- Tool input. The Claude Code input has a `description` field. The Hermes input has only the command.

## Environment

This is the first unit that runs in the development container `lifeos-dev` and not on `.212`. It is also the first unit that runs the current plugin commit. Earlier units ran plugin commit `1ea7757`. [runtime-manifest.json](runtime-manifest.json) records 17,583 prepared source files and the plugin commit. [runtime-check.json](runtime-check.json) verifies those files and records 603 native program hashes.

The two clients run different LifeOS trees. See [source differences](../../parity/source-differences.md).

## Results

| Case | Result |
| --- | --- |
| One successful call | Both clients pass. One activity row with the command and its output. |
| Three identical calls | Both clients pass with exactly three calls. The loop alert appears at call 3 and reaches the model. |
| One failing call | Both clients pass with the identical error text. |

The tightened tests fail against the earlier driver ([before-output.txt](before-output.txt)). The focused suite passes 99 tests. The cumulative ledger contains 77 equal selected cases for 28 registrations. Complete compatibility remains unverified.
