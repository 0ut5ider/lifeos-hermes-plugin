# Prompt transcript timing probe

Date: 2026-09-27. Target: isolated `lifeos-hermes@192.168.8.212` account.

The Claude Code reference CLI ran an allowed first prompt through a temporary `UserPromptSubmit` command hook. The hook inspected its `transcript_path` before the model call. The file did not exist, and no row contained the current prompt. The CLI answered `READY` with exit code zero after running the hook. This avoids mistaking a blocked prompt's behavior for an allowed prompt's behavior.

The bridge previously appended the current user row before running the hook. A new child-process test observed `['first prompt']` during the first hook call and failed because native Claude Code exposes no current prompt then. After moving the append after hook execution, the test observed `[]` on the first call, `['first prompt']` on the second, and both rows after the second call. The installed bridge on `.212` reproduced those three observations and passed `hermes plugins validate`.

The local suite passed 82 tests with six optional native tests skipped. The reference run used `--effort medium` because the local model endpoint rejects Claude Code's default high effort; it did not need a remote model. This probe does not establish complete Claude Code transcript equivalence. In particular, the bridge still does not block a user prompt when `UserPromptSubmit` returns `decision: block` or exits with code 2.
