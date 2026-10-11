# Atlas history needs capacity-driven retention

Date: 2026-10-11.

A fixed 64-run trigger does not prevent exhaustion for every admitted inventory. The actual native 100-device, 50-project fixture reaches 10,006 projected fields at the next sync, against a limit of 10,000. The previous graph still passes admission. The failed pressure test preserves the exact live bytes. This disproves the fixed-trigger-only policy.

The planner must try smaller retained history windows when the planned publication exceeds capacity. It always starts from the original admitted bytes. Every observation reference and each collector's latest run remain live. Exact prior database and snapshot bytes go into a private archive in the same publication transaction. A referenced run cannot be discarded to force a capacity pass.

Collector counts cannot reset when rows move into history. The native snapshot carries cumulative archived counts and adds them to the retained run counts. Structural insight metrics continue to come from the actual current native graph. Archive identifiers bind the provenance manifest as well as both preserved files. Current owner reads verify that identity and recheck current policy.

The initial packaged native source has no installed yaml dependency. The harness uses the retained complete prepared source with installed dependencies. That setup error remains recorded separately from the expected behavior regressions. No native patch or source pin changes for this implementation.
