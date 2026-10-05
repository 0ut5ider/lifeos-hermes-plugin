# Paired per-turn format contract effects

Date: 2026-10-05. Five cases run the actual `DriftReminder.hook.ts` through Claude Code 2.1.272 and Hermes UserPromptSubmit events. All ten clients complete with status zero and one successful private FlashNext response. The selected hook runs synchronously, as its pinned registration specifies.

| Case | Required effect | Result |
| --- | --- | --- |
| `format-contract-empty` | Initialize turn state and emit the default 15-line contract without a cached response. | Both clients pass. |
| `format-contract-clean` | Emit again after a recent prior turn, report a clean three-line response, and advance state from turn 6 to turn 7. | Both clients pass. |
| `format-contract-violations` | Report the missing banner and closer, three prose punctuation violations, one banned word, and 17 lines against the default cap. | Both clients pass. |
| `format-contract-depth` | Lift the line cap for a depth request and retain the other measured violations. | Both clients pass. |
| `format-contract-stale` | Preserve the old cache but exclude its violations when it is more than 30 minutes old. | Both clients pass. |

[paired-results.json](paired-results.json) retains exact state and output assertions. The hook persists the current turn as `last_fired_turn`, advances `turn_count`, and stores the exact emitted contract as `last_text`. The fixture confirms that a preceding fire does not suppress the next contract. These are successive persisted turn states in separate real sessions; the fixture does not claim a multi-turn client conversation.

[format-proof.json](format-proof.json) independently checks actual hook inputs, startup and session-end boundaries, unchanged cache bytes, cache age, emitted output, persisted state, and exact wire hashes. It verifies that the complete emitted contract appears in each actual model request. Full wire bodies remain in mode-0600 files outside Git. Raw hook payloads, synthetic files, and final client logs remain here.

[runtime-check.json](runtime-check.json) verifies 16,925 unchanged prepared source files against the preceding [runtime manifest](../2026-10-05-paired-context-response/runtime-manifest.json). It pins 603 native program files and the experiment runtimes. Each selected hook definition also pins `banned-vocab.ts`. Bubblewrap confines writable files to a synthetic home and device mount, with private temporary storage. Production services, personal data, and tier mappings receive no changes.

The characterization and required-effect tests fail before implementation. The final focused suite passes 54 tests and ten subtests. No product code changes in this unit.

These cases cover selected unmanaged format-reminder effects. Code-block exclusions, malformed state and input, write failure, repeated prompts in one client session, the exact stale boundary, complete hook groups, managed-memory admission, and Discord remain open. The cumulative ledger contains 43 equal selected cases for 15 registrations. Complete compatibility remains unverified.
