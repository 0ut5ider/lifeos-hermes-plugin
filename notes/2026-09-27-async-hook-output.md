# 2026-09-27: Async LifeOS context was discarded

The bridge already detached async command hooks so they could finish after a one-shot Hermes process exited. Its runner sent stdout to `/dev/null`. That lost context from installed LifeOS hooks such as TimeContext, VersionDrift, and ModelRungGuard. The [Claude Code hooks reference](https://code.claude.com/docs/en/hooks#how-async-hooks-execute) specifies next-turn delivery for async `additionalContext` and `systemMessage`.

A characterization test ran an async UserPromptSubmit hook that returned both fields. The second Hermes prompt received no context before the change. The runner now writes a private, size-limited result file after the hook exits. The bridge claims completed files for the same session at the start of the next prompt and adds their fields to the user turn. A second session cannot drain those files. A child hook that completes after its parent Hermes process exits can still write the file for a later process to read.

The installed native TimeContext hook ran async on `.212`. Its `<time-now>` output was absent from the triggering prompt and present on the next prompt. Local tests covered both same-process and restarted-process delivery. Ordinary async hooks no longer use the synchronous hook timeout, matching Claude Code's documented behavior.

The bridge reads at most 64 KiB of one hook's stdout for deferred context. Completed output is removed after delivery or session finalization. A hook that finishes after finalization can lose its result, and a service manager can still kill a detached child with the gateway's control group.
