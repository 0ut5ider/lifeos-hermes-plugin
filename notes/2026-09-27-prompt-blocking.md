# Prompt blocking probe

Date: 2026-09-27. Target: isolated `lifeos-hermes@192.168.8.212` account.

Claude Code documents two blocking results for `UserPromptSubmit`: JSON `decision: block` and command exit code 2. It removes a blocked prompt from model context. The bridge previously ignored both results and saved the prompt. Hermes's stock `pre_llm_call` collector treated plugin output only as context.

The bridge now converts either blocking result into `{"action":"block","message":...}` without appending the prompt to its private transcript. A child-process test covers each result. The Hermes test fork recognizes that result, returns the hook reason to the caller, and skips the model call and turn persistence. A real `AIAgent.run_conversation` test supplied prior history and a blocking hook. It observed zero provider calls, unchanged prior history, no turn persistence call, and `turn_exit_reason: prompt_blocked`. A second test found that an identical earlier prompt could be labeled as the current turn, and an older unfinished turn could be closed by the failed-turn cleanup. The patched core excludes blocked prompts from both paths.

The focused Hermes agent and plugin group passed 37 tests. The plugin suite passed 84 tests with six optional native skips. The updated core patch applies cleanly to its base commit `758ad514e` and reverses cleanly from the installed fork at `a33250529`. This test uses a controlled lifecycle hook result; a full Hermes CLI turn with a native LifeOS prompt hook returning block remains to be run. Other LifeOS hook parity limits remain in `docs/hook-parity.md`.
