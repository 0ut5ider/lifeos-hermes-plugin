# Paired current-time context

Date: 2026-10-05. Four cases exercise the native TimeContext hook through actual Claude Code 2.1.272 and Hermes clients. All eight clients complete with status zero and one successful private FlashNext response.

| Case | Execution mode | Required effect | Result |
| --- | --- | --- | --- |
| UTC | Synchronous control | Emit the current UTC minute and deliver the clock into the first model request. | Both clients pass. |
| America/Toronto | Synchronous control | Emit the current Toronto minute, weekday, timezone abbreviation, and day period. Deliver the clock into the first model request. | Both clients pass. |
| UTC | Original asynchronous registration | Emit a valid current clock. The first model request has no clock context. | Both clients pass. |
| Invalid timezone | Synchronous control | Return no clock context, preserve settings, and complete the user response. | Both clients pass. |

The synchronous controls override the original execution mode. The asynchronous case retains `async: true` and the pinned five-second timeout. Its first model request lacks the clock in both clients. This result does not establish next-turn delivery or exact asynchronous ordering.

[clock-proof.json](clock-proof.json) independently parses the raw emitted clock and checks it against each actual client execution interval. It verifies day periods, captured settings, hook input, complete session boundaries, model request contents, successful response status, and wire hashes. The invalid-zone case preserves configuration and returns no hook output. Generated prose requires a nonempty response, with no equality claim.

[runtime-check.json](runtime-check.json) verifies all 16,925 prepared source files and records 603 native program hashes. Raw synthetic logs and file captures remain in this bundle. Full model wire bodies remain private outside Git. Each clock interval has an independent hash in the proof. No product code changes in this unit.

The new required-effect tests fail before implementation. The focused suite passes 59 tests and 17 subtests. These selected cases leave next-turn asynchronous delivery, interrupted clients, complete groups, managed-memory admission, and Discord acceptance open. The cumulative ledger contains 52 equal selected cases for 16 registrations. Complete compatibility remains unverified.
