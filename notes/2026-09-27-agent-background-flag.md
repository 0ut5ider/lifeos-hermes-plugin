# Agent background flag probe

Date: 2026-09-27

Hermes `delegate_task` defaults `background` to false. Its synchronous path waits for the child. The bridge instead derived Claude's `run_in_background` from whether the caller was a Hermes delegated child. At top level it therefore marked every Agent invocation as background, even an explicit `background: false`. Inside a delegated child it marked an explicit background invocation as foreground.

The regression test supplied Hermes's delegation context module and called `pre_tool_call` with `background: false`. Before the fix, the hook payload contained `run_in_background: true` and the test failed. This was invisible in earlier local tests because the bridge fell back to the argument when the Hermes module was absent from the test interpreter.

On the isolated `.212` installation, the old installed bridge returned `true`, `true`, `true` for omitted, false, and true background arguments. After synchronizing the corrected bridge file, the same probe returned `false`, `false`, `true`. The regression test also checks omitted foreground and a nested child with explicit background. The full local suite passed 74 tests with four optional native skips.

LifeOS and Pulse hooks now receive the actual delegation mode. This also prevents the bridge from starting its background watchdog for a foreground call merely because the call came from the primary agent. The correction changes only hook payload translation; it does not change Hermes delegation execution.
