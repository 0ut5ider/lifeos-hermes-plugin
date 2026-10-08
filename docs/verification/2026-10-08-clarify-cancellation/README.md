# Clarification cancellation outcome

Date: 2026-10-08. Scope: the pinned Hermes release candidate. The live gateway remains unchanged.

The October 7 Discord acceptance confirms that `/stop` releases the pending turn and allows a recovery reply. The model still reports `timed_out: true` after cancellation. The queue clears a pending response to an empty string, and the delivery layer maps that string to a timeout notice.

The [baseline](before.txt) finds three failures: cancellation becomes an inactivity notice, cancellation during a batch send becomes `timed_out`, and a deliberate empty answer becomes a timeout. Actual timeout and literal user text controls pass.

The queue now returns a typed cancellation notice. A real user answer with the same text remains ordinary text. The gateway retains the registered entry while it sends the card, so cancellation before the waiter starts also retains its outcome. A cancelled entry cannot remove a later request that reuses its identifier. The tool returns `cancelled: true`, an empty user answer, and the cancellation notice. A cancelled batch retains earlier answers and does not open the remaining questions. The retired card states that the prompt was cancelled. Actual timeouts keep their existing result.

The [final native gate](native-gate-final.txt) passes 98 tests with warnings treated as errors. Seven added controls exercise actual queue entries, wait events, callback dispatch, and tool serialization. The broader suite includes existing simulated transport unit controls. This gate does not replace live Discord acceptance.

The [warning probe](warning-all-probe.txt) identifies pending retirement work and unclosed event loops in the existing fallback test fixture. The fixture now awaits scheduled work and closes its loop. The [clean intermediate gate](native-gate-clean.txt) passes 97 tests before the final batch-marker control is added. The warning probe remains part of the evidence.

The [package gate](package-gate.txt) passes 24 patch and installation-source tests. The first package invocation selects a nonexistent module; the next lacks the Hermes source on `PYTHONPATH`. Both failed outputs remain recorded, and the corrected invocation passes. The [complete source preparation](prepared-sources.json) validates all 11 Hermes patch groups and all 23 LifeOS patch groups against their pinned commits. The [historical ledger](historical-ledger.txt) retains complete Step 1 evidence with unchanged artifact hashes.

Both runtime and repository copies of `hermes-session-lifecycle.patch` contain the change. No bot credentials, model routes, selected native data, or live source files change in this unit. The installed cancellation and recovery repeat remains part of the combined release acceptance.
