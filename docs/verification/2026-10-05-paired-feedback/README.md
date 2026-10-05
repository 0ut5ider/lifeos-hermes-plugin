# Paired feedback capture effects

Date: 2026-10-05. Five cases run the actual `SatisfactionCapture.hook.ts` through Claude Code 2.1.272 and Hermes UserPromptSubmit events. All ten final clients complete with status zero and one successful private FlashNext response. Each client invokes the selected hook exactly once.

| Submitted prompt | Required effect | Result |
| --- | --- | --- |
| `8 great result` | Append explicit rating 8 and its comment. | Both clients pass. |
| `10` | Append explicit rating 10 without a comment, despite the normal minimum prompt length. | Both clients pass. |
| `great job` | Append implicit rating 8 with the native praise summary and confidence 0.95. | Both clients pass. |
| `2 of the files were inspected` | Preserve the existing rating without capturing numeric work text as feedback. | Both clients pass. |
| `4 needs clearer details` | Append explicit rating 4 and capture one native learning record. | Both clients pass. |

[paired-results.json](paired-results.json) contains equal selected assertions. Each new rating has a valid timestamp, the actual session identifier, and the first 500 characters of the seeded response. Both clients preserve the existing unrelated rating and the complete response cache. The low-rating learning includes the explicit source, feedback, full cached context, and synthetic principal `FixtureOwner`.

[feedback-proof.json](feedback-proof.json) records independent checks of raw hook inputs, client boundaries, captured files, and request and response hashes. The collector checks the actual submitted prompt without adding instructions to that text. Full wire bodies remain in mode-0600 files outside Git. Final raw hook payloads, synthetic file captures, and client logs remain in this bundle.

The [first run](failed-blocked-observer/run-output.txt) fails because its observer blocks the native prompt before the selected hook can run. It observes no feedback hook and no SessionEnd event. The [second run](failed-unconstrained-response/paired-results.json) reaches the hooks and captures the expected state. Some unconstrained responses need multiple model calls, so three cases fail the single-response fixture assertion. Neither run counts as passing evidence.

The final configuration supplies a synthetic system instruction through native `--append-system-prompt` and Hermes `HERMES_EPHEMERAL_SYSTEM_PROMPT`. It leaves feedback prompts unchanged. All final cases make one generation request and receive HTTP 200. The assertion requires a nonempty final response; it does not require identical model prose or literal `READY`. The instruction confines the experiment to a completed conversation without additional work.

[runtime-check.json](runtime-check.json) verifies 16,925 unchanged prepared source files against the preceding [runtime manifest](../2026-10-05-paired-context-response/runtime-manifest.json). It pins 603 native hook and tool source files, the native executable, Hermes interpreter, trace driver, and experiment files. Each client uses a synthetic home, a writable project, and private temporary storage under Bubblewrap. Production services, model tiers, and personal data receive no changes.

The new characterization tests fail before implementation. The successful-response requirements also fail before the fixture permits model completion. The final focused suite passes 48 tests and eight subtests. No product code changes in this unit.

These fixtures run the selected hook synchronously. The pinned SatisfactionCapture registration specifies asynchronous execution. The retained results establish the selected handler effects through real client events. They do not establish asynchronous timing or shutdown behavior.

These cases cover selected unmanaged feedback branches. Asynchronous registration, other rating syntax, system-message exclusions, missing context, write failure, very low ratings and FailureCapture, standing directives, complaints, ISA rating pulses, complete hook groups, managed-memory admission, and Discord remain open. The cumulative ledger contains 38 equal selected cases for 14 registrations. Complete compatibility remains unverified.
