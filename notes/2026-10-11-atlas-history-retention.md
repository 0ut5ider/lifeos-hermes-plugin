# Atlas history needs capacity-driven retention

Date: 2026-10-11.

A fixed 64-run trigger does not prevent exhaustion for every admitted inventory. The actual native 100-device, 50-project fixture reaches 10,006 projected fields at the next sync, against a limit of 10,000. The previous graph still passes admission. The failed pressure test preserves the exact live bytes. This disproves the fixed-trigger-only policy.

The planner must try smaller retained history windows when the planned publication exceeds capacity. It always starts from the original admitted bytes. Every observation reference and each collector's latest run remain live. Exact prior database and snapshot bytes go into a private archive in the same publication transaction. A referenced run cannot be discarded to force a capacity pass.

Collector counts cannot reset when rows move into history. The native snapshot carries cumulative archived counts and adds them to the retained run counts. Structural insight metrics continue to come from the actual current native graph. Archive identifiers bind the provenance manifest as well as both preserved files. Current owner reads verify that identity and recheck current policy.

The initial packaged native source has no installed yaml dependency. The harness uses the retained complete prepared source with installed dependencies. That setup error remains recorded separately from the expected behavior regressions. No native patch or source pin changes for this implementation.

The same raw-source dependency assumption fails on `.252`. Four installed native program files match the certified source bytes, including Atlas Store and the memory boundary. The corrected harness selects those installed program files and the guest Python interpreter. It does not install packages into the certified source or change live configuration.

The next remote gate passes the retention tests but fails three inference cases. The staging script gives every source file mode 0600, including the executable `bin/claude` launcher. Bun returns `null` for launcher discovery and `EACCES` for direct execution. The staging fix preserves executable intent as mode 0700 and records every staged file mode. The initial missing Anthropic SDK hypothesis does not explain the failure: the direct synthetic gateway path uses Python's standard library. This is a verification harness failure, with no inference implementation change.
