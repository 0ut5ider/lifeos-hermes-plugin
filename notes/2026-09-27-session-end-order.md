# 2026-09-27: Parallel SessionEnd handlers could lose work learning

The bridge ran all matching command hooks concurrently. LifeOS registers WorkCompletionLearning before SessionCleanup, and the former explicitly says it must read active work before the latter marks it complete. A characterization test made the first hook wait 200 ms before writing a marker. The second hook checked for that marker. Before the change, their exit codes were `[0, 2]`, proving the second hook ran too early.

The bridge now runs SessionEnd handlers in registration order. Other hook events retain concurrent synchronous dispatch. The same characterization test returned `[0, 0]` after the change.

An isolated `.212` probe used the installed native WorkCompletionLearning and SessionCleanup hooks with a synthetic work registry and one closed claim. The bridge produced one learning file containing the synthetic session ID. It also changed the synthetic work row and ISA phase to `complete`. The fixture lived in a temporary LifeOS root; the probe did not alter the installed work registry.

All six installed SessionEnd commands then ran sequentially with a separate synthetic session and temporary LifeOS root. They returned six zero exit codes in 0.465 seconds. Hermes's gateway shutdown finalization budget is 10 seconds. This timing result covers the no-active-work path; the learning capture path was verified separately with two handlers.

On 2026-09-28, this bridge behavior was superseded. The installed LifeOS registry lookup includes `complete` work rows, and a native probe confirmed WorkCompletionLearning still captures after SessionCleanup finishes. The bridge now dispatches SessionEnd handlers concurrently, as Claude Code does. See [the follow-up record](2026-09-28-session-end-parallel.md).
