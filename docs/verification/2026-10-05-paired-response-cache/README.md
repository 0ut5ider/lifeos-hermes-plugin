# Paired final-response cache effects

Date: 2026-10-05. Three cases run the actual `LastResponseCache.hook.ts` through real Claude Code 2.1.272 and Hermes Stop events. All six clients receive HTTP 200 from private FlashNext and exit with status zero. The hook creates, replaces, and limits the native response cache correctly.

| Case | Required effect | Result |
| --- | --- | --- |
| `response-cache-empty` | Create the missing cache from the actual Stop message. | Both clients cache `READY`. |
| `response-cache-replace` | Replace a seeded previous response with the current Stop message. | Both clients remove the previous marker and cache `READY`. |
| `response-cache-limit` | Cache exactly the first 2,000 characters of a Stop message longer than the limit. | Native input has 13,099 characters. Hermes input has 14,031 characters. Both caches contain the exact 2,000-character prefix. |

[paired-results.json](paired-results.json) retains equal selected effect assertions. The comparison checks each cache against that client's actual Stop payload. It does not require the private model to generate identical long prose through two different protocols. [request-cache-proof.json](request-cache-proof.json) records exact request and response hashes, Stop message identities, cache identities, character counts, and final result identities. The primary decodes each retained Stop payload and verifies the cache bytes independently. Full request and response body records remain in mode-0600 files outside Git.

Claude Code displays two leading newlines that it omits from `last_assistant_message`. The fixture verifies exact equality between the cache and the Stop message prefix. It separately compares the Stop message and final displayed result after removing surrounding whitespace. Raw Stop input and client output remain retained. This makes the native formatting difference explicit.

The [first run](failed-first-run.json) fails all three cases. Its assertion compares native cache bytes with untrimmed display bytes. Its repetition prompt also produces only 370 and 1,266 characters, so it cannot establish truncation. The corrected run uses a detailed prose prompt and reaches the limit on both sides. The failures remain visible and do not count as passing controls.

[runtime-check.json](runtime-check.json) verifies 16,925 unchanged staged source files against the preceding [runtime manifest](../2026-10-05-paired-context-response/runtime-manifest.json). It also pins the native executable, Hermes interpreter, trace driver, and candidate control files. The [configuration](configuration.json) identifies isolated homes, the prepared source, and the separate interpreter without development-recorder startup. The hook definitions retain the selected native program hashes. Bubblewrap limits writable paths to each synthetic home and device mount and provides private temporary storage.

Characterization tests preserve existing startup and session-end fixture events. The new cache assertion and fixture cases fail before implementation. The input-contract regression fails before the assertion uses the real Stop message. The final focused suite passes 42 tests and six subtests. Six actual client runs provide the hook and private-model evidence. No product code changes in this unit.

These cases verify selected unmanaged cache behavior. Transcript fallback, missing input, write failure, full Stop groups, managed-memory admission, and an actual Discord gateway remain outside this claim. The cumulative ledger contains 33 equal selected cases for 13 registrations. The completion check remains open.
