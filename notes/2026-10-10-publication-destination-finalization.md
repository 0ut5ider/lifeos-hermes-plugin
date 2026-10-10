# Publication inputs and destinations need separate checks

Date: 2026-10-10. Reviewed code: `cc14475f`. Correction: `5511bbb9`.

The targeted review passes 61 checks but reproduces premature finalization in three publishers. Algorithm summaries and LocalIntelligence digests report success after a real destination edit. Conduit refuses delivery after its operation has already committed. All three remove the recovery journal. The primary agent repeats the tests and independently reproduces those outcomes.

The earlier correction handles source changes and nested conflicts. These checks deliberately exclude destinations from unchanged-input comparisons because the operation writes those destinations. That exclusion requires a separate comparison against the operation's expected output. Without it, a later destination edit can become the accepted post-write snapshot.

The new regression changes all six destinations at two boundaries: after the actual publisher returns, and after the actual post-write snapshot returns. Three test methods produce 12 expected failures before the correction. All 12 cases pass after the correction. The tests retain actual native planning, authorization, file writes, and SQLite receipts.

Each affected callback now compares every destination with its expected bytes before returning a committed receipt. A mismatch raises the recoverable failure exception. The tests require an unknown receipt and retained journal. A fresh transaction refuses to overwrite the changed destination and leaves all other group members untouched. Restoring the operation's expected bytes in the synthetic fixture then permits complete recovery to the original state.

This correction uses the existing transaction and expected-digest recovery contracts. It makes no source-pin, patch, server, Discord, or deployment change. The [verification record](../docs/verification/2026-10-10-publication-destination-fix/) retains commands, source hashes, failures, and passing checks.
