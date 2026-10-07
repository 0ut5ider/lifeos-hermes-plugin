# Paired asynchronous feedback capture

Date: 2026-10-05. Five cases repeat the [synchronous feedback controls](../2026-10-05-paired-feedback/README.md) with the pinned SatisfactionCapture execution settings: `async: true` and a 20-second timeout. All ten actual Claude Code 2.1.272 and Hermes clients complete with status zero, one hook invocation, and one successful private FlashNext response.

| Prompt | Required effect after normal client completion | Result |
| --- | --- | --- |
| `8 great result` | Append explicit rating 8 with the comment and current session context. | Both clients pass. |
| `10` | Append a bare explicit rating 10 without a comment. | Both clients pass. |
| `great job` | Append implicit rating 8 with confidence 0.95 and the native praise summary. | Both clients pass. |
| `2 of the files were inspected` | Preserve the existing rating without capturing a new rating. | Both clients pass. |
| `4 needs clearer details` | Append explicit rating 4 and create one learning record with the full cached context. | Both clients pass. |

[paired-results.json](paired-results.json) retains equal selected outcomes. The hook uses each actual session identifier, preserves the unrelated rating and response cache, and includes the first 500 response characters in eligible ratings. The low-rating learning includes the explicit feedback and synthetic principal `FixtureOwner`.

[feedback-proof.json](feedback-proof.json) independently checks raw inputs, complete client boundaries, stored effects, source identities, and wire hashes. It reads the captured settings and verifies the asynchronous flag and original timeout on both sides. Full model wire bodies remain private outside Git. Raw synthetic file captures, hook inputs, and client logs remain in this bundle.

The experiment changes no feedback text. Its synthetic system instruction confines the conversation to a response without work. It requires a nonempty final response, with no equality claim for generated prose. [runtime-check.json](runtime-check.json) verifies the 16,925 prepared source files, pins 603 native programs, and records interpreter and driver identities.

The new fixture and required-effect tests fail before implementation. The final focused suite passes 56 tests and 15 subtests. No product code changes in this unit.

These cases verify final effects after normal completion with the original asynchronous setting. They do not establish an exact ordering relative to model generation. Interrupted clients, rapid shutdown, failure and cancellation, complete groups, other feedback branches, managed-memory admission, and Discord remain open. The cumulative ledger contains 48 equal selected cases for 15 registrations. Complete compatibility remains unverified.
