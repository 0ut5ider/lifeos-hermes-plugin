# Interview seed fixture isolation

Date: 2026-10-05. Role: Cerebo, primary implementation. Question: why does an interruption control report a synthetic generator failure? Model: gpt-6.1-sol.

The native memory fixture links its `LIFEOS/TOOLS` directory directly to the prepared source. A new test replaces `UpdateLifeosState.ts` to inject a second-generator failure. Writing through the linked directory changes the shared prepared source. Later tests then execute that injected failure.

The candidate gate reports four failures, 12 passes, and eight subtests in 3.63 seconds. Inspection of the prepared generator confirms the injected throw. The fixture declaration confirms a directory symlink. This is a test isolation error. It does not identify a product cause for the later generator failures.

The failure-injection control needs a private copy of tool code and a link to the frozen dependencies. Both affected prepared generator files are restored from the unchanged scratch source before the corrected gate. Fresh distributed preparation remains the final source acceptance step.

The earlier native control still establishes the original aggregate behavior: the parent reports `written: true` and leaves the first artifact updated when the second generator fails. Its source-isolated replacement must establish the same intended failure boundary before accepting grouped recovery.

The source-isolated original control reproduces the failure in 0.67 seconds without changing the prepared generator. The corrected focused gate passes 23 tests and 25 subtests in 13.44 seconds. A new distributed preparation then passes 198 tests and 116 subtests in 202.26 seconds. All 55 native source hashes remain unchanged after that run.
