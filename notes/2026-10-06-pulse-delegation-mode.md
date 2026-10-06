# Pulse delegation mode

The first live foreground guard comparisons disagreed. Claude Code emitted the foreground warning. Hermes marked the call as background, so Pulse omitted the warning. Tightening the fixture prompt did not settle the discrepancy. Hermes controls the model-facing background mode itself.

The dispatch implementation supplied the explanation: one-shot sessions do not support asynchronous delivery or persisted-history delivery. Hermes falls back to synchronous execution there. The bridge classified the requested mode before accounting for that fallback. A regression reproduced the wrong `run_in_background: true` value using the real session context, then passed with the finite-session correction.

The next live run passed all three paired cases: blocked skill, allowed skill, and foreground agent. All six clients called real Pulse daemons. The denial or warning reached the next real model request as applicable. The real watchdog test also confirmed a single process, parent session and thread metadata on its completion queue alert, and cleanup of its process and state. These tests do not establish Discord message delivery or the capacity-dependent async fallback.
