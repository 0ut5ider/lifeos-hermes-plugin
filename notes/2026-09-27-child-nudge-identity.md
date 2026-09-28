# 2026-09-27: Delegated child tool identity

LifeOS's `AlgorithmNudge` uses `agent_id` on tool events to avoid treating delegate calls as primary work. Hermes creates a distinct child session ID and marks execution with `delegated_child_context`, but the bridge had been passing only `session_id` into native hooks.

The failure was measured with the installed native hook on isolated `.212`. A synthetic Read result ran inside Hermes's real delegated-child context. The context predicate returned true, but the native nudge state recorded `primaryEvents: 1` and `delegateEvents: 0`. This showed that the native hook did not recognize the event as a child call.

The bridge now adds the child session ID as `agent_id` and `general-purpose` as `agent_type` to child tool events. It leaves primary tool events without those fields. The explicit model and task description for a Hermes delegation still travel through the separate `Agent` tool payload.

After installing the change on `.212`, the same native probe recorded `delegateEvents: 1` and `primaryEvents: 0`. Both probes used a temporary home and the installed native hook. No real delegation task was created.
