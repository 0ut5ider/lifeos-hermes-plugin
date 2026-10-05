# Paired end-of-turn ISA render

Date: 2026-10-05. Six cases exercise the native ISARenderOnStop hook through actual Claude Code 2.1.272 and Hermes clients. All 12 clients complete with status zero and one successful private FlashNext response.

The fixture observer writes the per-session edit state at the real SessionStart event. The hook then runs at the real Stop event. Each fixture links the native tool directory, so the detached native renderer writes the actual page.

| Case | Required effect | Result |
| --- | --- | --- |
| No edit state | Return `continue`, write no log row, and write no page. | Both clients pass. |
| First authoring (phase `execute`, iteration 1) | Log a `pre-completion` skip, clear the state, and write no page. | Both clients pass. |
| Edited ISA is missing | Log a `missing` skip and clear the state. | Both clients pass. |
| Completed ISA | Log the render, clear the state, and write the rendered page. | Both clients pass. |
| Resumed ISA (iteration 2) | Log the render, clear the state, and write the rendered page. | Both clients pass. |
| Existing older page | Log the render, clear the state, and replace the prior page. | Both clients pass. |

[render-proof.json](render-proof.json) independently reads the raw captures. It checks the seeded document, the session-bound state file, the Stop payload, the exact log row with normalized paths, the page content, the unchanged ISA document, and the successful response status. The page hash is recorded for each client. The two clients write different absolute paths, so the proof makes no page equality claim.

[runtime-check.json](runtime-check.json) verifies all 16,925 prepared source files and records 603 native program hashes. Raw synthetic logs and file captures remain in this bundle. Full model wire bodies remain private outside Git. No product code changes in this unit.

The new required-effect tests fail before implementation ([before-output.txt](before-output.txt)). The focused suite passes 74 tests. These selected cases leave the spawn-failure branch, a page that is newer than its document, interrupted clients, complete groups, and Discord acceptance open. The cumulative ledger contains 65 equal selected cases for 18 registrations. Complete compatibility remains unverified.

The two clients run different LifeOS trees: the installed reference tree and the patched prepared tree. See [source differences](../../parity/source-differences.md). The `ISARender.ts` tool also differs between the two trees.
