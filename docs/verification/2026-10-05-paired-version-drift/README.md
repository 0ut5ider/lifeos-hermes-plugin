# Paired version-drift warning

Date: 2026-10-05. Seven cases exercise the native VersionDrift hook through actual Claude Code 2.1.272 and Hermes clients. All 14 clients complete with status zero and one successful private FlashNext response.

Each fixture is a disposable Git repository with ten tagged core files, a `VERSION` file, and a selected number of later edits. The hook compares the working tree with tag `v1.0.0`.

| Case | Execution mode | Required effect | Result |
| --- | --- | --- | --- |
| Ten changed files | Synchronous control | Emit the warning for ten files, write the warning state, and deliver the warning into the first model request. | Both clients pass. |
| One changed file, tag 72 hours old | Synchronous control | Emit the warning with the tag age, write the warning state, and deliver the warning. | Both clients pass. |
| One changed file, new tag | Synchronous control | Emit nothing and write no state. | Both clients pass. |
| `VERSION` ahead of the tag | Synchronous control | Emit nothing and write no state. | Both clients pass. |
| Warning state ten minutes old | Synchronous control | Emit nothing and preserve the existing state bytes. | Both clients pass. |
| No release tag | Synchronous control | Emit nothing and write no state. | Both clients pass. |
| Ten changed files | Original asynchronous registration | Emit the warning and write the state. The first model request has no warning. | Both clients pass. |

The synchronous controls override the original execution mode. The asynchronous case retains `async: true` and the pinned ten-second timeout. This result does not establish next-turn delivery or exact asynchronous ordering.

[drift-proof.json](drift-proof.json) independently reads the raw captures. It checks the seeded edits, the tag, the exact warning prefix, the state timestamp against each client interval, the unchanged working tree, the model request contents, and the successful response status. Generated prose requires a nonempty response, with no equality claim.

[runtime-check.json](runtime-check.json) verifies all 16,925 prepared source files and records 603 native program hashes. Raw synthetic logs and file captures remain in this bundle. Full model wire bodies remain private outside Git. No product code changes in this unit.

The new required-effect tests fail before implementation ([before-output.txt](before-output.txt)). The focused suite passes 67 tests. These selected cases leave next-turn asynchronous delivery, the 60-minute interval boundary, interrupted clients, complete groups, and Discord acceptance open. The cumulative ledger contains 59 equal selected cases for 17 registrations. Complete compatibility remains unverified.
