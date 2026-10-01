# Native memory publication and summary contracts

Date: 2026-10-01

The first correction gate passes 215 tests across 15 modules. A fresh review expands it to 316 tests across 27 modules. Eight tests fail and one errors, all in the native delta summary module. Native persistence and recall pass while the user-visible learning summary loses the acknowledged additions.

The explicit remember correction uses verified full-file curation to preserve the registry invariant. That changes the native audit row's `updated_by` from `MemorySystem.add` to the authenticated writer. Both delta readers select exactly `MemorySystem.add`. The real composer returns no learning summary. Changing only that label in a synthetic log restores `+1 learned` and its fact sample. The cause is an interface contract, not missing fact persistence or model behavior.

The correction supplies the native addition label for append operations. Registry records still contain the authenticated writer. Full curation and correction keep their other native labels. All 20 existing delta tests pass after this change. The closure gate includes the native consumers as well as the publication methods. A narrow passing gate does not establish integration completion.

Evidence: [the independent review](../docs/agents/2026-10-01-memory-correction-review/memory-correction-review.md) and [primary correction evidence](../docs/verification/2026-10-01-memory-corrections/README.md).
