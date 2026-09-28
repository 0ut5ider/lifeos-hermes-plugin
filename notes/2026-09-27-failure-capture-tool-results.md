# FailureCapture tool result pairing

Date: 2026-09-27. Fixture: isolated `lifeos-hermes` account on `192.168.8.212`. The transcript and capture directory were disposable. The test used a local stub for LifeOS's description inference.

The bridge writes Claude-shaped tool results as `tool_result` blocks in user message rows. LifeOS `FailureCapture.ts` at base `5e2f2e8` read tool uses from assistant rows, but attached outputs only from top-level `tool_result` or `tool_output` rows. It also classified a user row containing only a tool result as conversation text. A bridge transcript with one Bash result produced a `tool-calls.json` entry without `output`.

The regression creates two distinct calls, Bash and Read, with separate outputs. It then invokes the native `captureFailure()` function. Against the unpatched file, the test failed because the first call had no `output`. The compatibility patch maps each assistant `tool_use.id` to its call, attaches each user `tool_result.tool_use_id` to that call, and keeps result blocks out of the user conversation excerpt. The expanded test passed against the patched fresh checkout and installed `.212` file.

The five LifeOS patches applied in order to a fresh worktree at `5e2f2e8`. Each passed `git apply --check`; the final diff passed `git diff --check`. The plugin suite passed 90 tests, with 10 native tests skipped when their optional fixture paths were absent. The dedicated FailureCapture test passed when pointed to the patched source and on `.212`. This probe did not run a real model or use a real user transcript.

The `.212` LifeOS source fix is commit `2f6626f` on `feature/hermes-task-hook`. The installed file has the same SHA-256 as the source file. Production `.211` and `.213` were not changed.
