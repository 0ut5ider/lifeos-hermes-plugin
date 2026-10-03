# Native memory publication and summary contracts

Date: 2026-10-01

The first correction gate passes 215 tests across 15 modules. A fresh review expands it to 316 tests across 27 modules. Eight tests fail and one errors, all in the native delta summary module. Native persistence and recall pass while the user-visible learning summary loses the acknowledged additions.

The explicit remember correction uses verified full-file curation to preserve the registry invariant. That changes the native audit row's `updated_by` from `MemorySystem.add` to the authenticated writer. Both delta readers select exactly `MemorySystem.add`. The real composer returns no learning summary. Changing only that label in a synthetic log restores `+1 learned` and its fact sample. The cause is an interface contract, not missing fact persistence or model behavior.

The correction supplies the native addition label for append operations. Registry records still contain the authenticated writer. Full curation and correction keep their other native labels. All 20 existing delta tests pass after this change. The closure gate includes the native consumers as well as the publication methods. A narrow passing gate does not establish integration completion.

Evidence: [the independent review](../docs/agents/2026-10-01-memory-correction-review/memory-correction-review.md) and [primary correction evidence](../docs/verification/2026-10-01-memory-corrections/README.md).

The next fresh review interrupts a real native hot publication before registry commit. Recovery restores the authoritative fact, but the native write log retains the aborted addition. The actual registered composer reports it as learned. The smallest correction journals that audit log with the fact and verifies projected additions against current native records.

The first authority check memoizes individual facts but launches one native read per distinct fact. At 96 valid entries, the primary measures 12.700 seconds and the reviewer measures 13.027 seconds. Both exceed the eight-second hook limit. A repeated single-entry volume test passes and misses this case. One verified snapshot per category restores the valid maximum-capacity contract, measured at 7.194 seconds. Distinct-entry capacity needs its own regression. Persistence, recovery evidence, and consumer time limits are separate contracts.

An independent follow-up measures 8.294 seconds in the same capacity observation, despite a passing isolated timeout test. Instrumentation identifies another 96 per-record reads in the existing retrieval path. The whole turn makes 100 native hot reads, taking 6.460 of its 7.210 seconds. Transaction-local parsed-entry reuse removes 94 redundant retrieval reads while keeping per-record digest and category checks. The unchanged 96-fact observation then takes 0.948 seconds. The result changes the decision: the earlier eight-second passing run does not justify closing the marginal timing limit.
