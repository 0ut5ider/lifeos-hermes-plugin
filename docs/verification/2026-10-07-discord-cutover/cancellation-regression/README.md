# Pending question interruption regression

Date: 2026-10-07. The first live `/stop` attempt resolves after 120.595 seconds. Adrian confirms that he selects Shiny Hermes Bot and sends the command while the question waits.

The offline regression uses the actual `GatewayRunner`, an actual `AIAgent`, and the actual clarification queue. It makes no model or Discord requests. The gateway invalidates the run generation but does not signal the question entry. The worker remains blocked until cleanup or timeout.

The [before output](before.txt) records two passing characterization cases and two failing interruption cases. The blocked waiter reaches the test's two-second deadline. The other failure shows that pending entries remain unresolved after synchronous interruption.

The [after output](after.txt) records four passing cases with clean output. The correction calls `clear_session` synchronously after generation invalidation. It releases the waiter, rejects late answers, preserves another chat's question, and permits a successor question after interruption. Existing queue tests cover answers that win before cleanup.

The source correction belongs to `hermes-session-lifecycle.patch`. Both distributed copies contain the same patch. Patch regeneration and source transaction checks pass 13 tests. The development recorder passes 34 tests, including token exclusion and unchanged slash callback return and exception behavior.

This regression proves a waiter cleanup defect. It does not prove where the original Discord slash interaction stopped. The recorder now observes interaction routing metadata, slash authorization, defer disposition, dispatch, and turn interruption. It excludes interaction tokens and option values from those routing records. A real Discord repeat remains required.
