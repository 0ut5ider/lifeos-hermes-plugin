# Bash audit output probe

Date: 2026-09-27

Hermes terminal tool results contain one combined `output` field plus `exit_code`. LifeOS `EventLogger` recorded only the command and exit code because its Bash audit reader looked for separate `stdout` and `stderr` fields. An isolated `.212` probe reproduced the missing preview with a Hermes-shaped result.

The LifeOS compatibility patch adds four lines to record the combined stream under `combined_output_preview` and `combined_output_bytes` when separate streams are absent. A native regression test failed before the patch and passed afterward. The patch applies cleanly to LifeOS base `5e2f2e8`. A bridge-to-installed-hook probe then recorded `hello` from a synthetic terminal result. Another native probe with separate stdout and stderr still recorded the original `stdout_preview` and `stderr_preview` fields.

This preserves the output available to Hermes without claiming that the combined stream is stdout. It does not recover the two original streams; that would require Hermes terminal execution to retain them separately.
