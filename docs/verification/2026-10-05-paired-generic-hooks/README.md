# Paired generic file and output comparison

Date: 2026-10-05. Twelve cases run one native hook each through actual Claude Code 2.1.272 and Hermes clients with one successful private FlashNext response. Each case compares every file below `.claude/LIFEOS` and `.local/state/lifeos` before and after the run, every hook output, and the delivery of each hook context into the model request. All 24 clients pass. The runs use the development container and the current plugin commit.

## Method

The driver normalizes values that differ by run only: the home path, the session identity, clock values, epoch milliseconds, digests and UUIDs, the transcript location of each client, and the work event offset, which counts session identity bytes. Each case then requires equal files and outputs on both sides and the measured effect below. [generic-proof.json](generic-proof.json) recomputes the changed file set from the raw captures for each side.

| Registration | Hook | Required effect |
| --- | --- | --- |
| `UserPromptSubmit.3.1` | ReminderRouter | A reminder prompt without a configured work repository changes nothing. |
| `UserPromptSubmit.5.1` | MemoryTurnStart | The memory context reaches the model request; injection and heartbeat state are written. |
| `UserPromptSubmit.7.1` | AlgorithmNudge | Nudge state and the skill index are written; no output. |
| `UserPromptSubmit.9.1` | ModelRungGuard | One rung log row with the pinned `fable` model. |
| `UserPromptSubmit.1.1` | PromptProcessing | Work events and the work registry are written. |
| `Stop.1.2` | TabState | No change without a terminal. |
| `Stop.1.3` | VoiceCompletion | A skipped voice event for the remote channel. |
| `Stop.1.5` | SpendAuditor | Audit row and state. |
| `Stop.1.6` | StopGates | Format, verification, and writing gate rows. |
| `Stop.1.7` | MemoryReviewFire | Review state rows. |
| `Stop.2.1` | MemoryHealthGate | No change for this fixture. |
| `SessionEnd.1.6` | IntegrityCheck | No change and no output. |

## Findings

- The first run found that the StopGates format gate saw no final answer under Hermes. The [timing correction](../2026-10-05-stop-transcript-timing/README.md) fixes the bridge. This run uses the corrected plugin, and both clients write the same three gate rows.
- The model rung patch adds `reasoning_effort` to the Hermes rung log. The comparison removes that field on both sides; it is a deliberate patch difference.
- In print mode, Claude Code exits before an asynchronous Stop hook finishes and then emits no SessionEnd. `Stop.2.1` therefore runs synchronously here; its pinned setting is asynchronous with a 15 second timeout.
- Four cases have no file change. They prove a quiet branch only: the disabled reminder router, TabState without a terminal, the memory health gate on an empty tree, and the integrity check without system changes.

## Evidence

[runtime-check.json](runtime-check.json) verifies the 18,153 files of the [runtime](runtime-manifest.json), which adds the complete prepared `LIFEOS` tree to the earlier runtime. The two clients run different LifeOS trees. See [source differences](../../parity/source-differences.md).

The new tests fail before the implementation ([before-output.txt](before-output.txt)). The focused suite passes 115 tests. Each case is one selected branch. The cumulative ledger contains 96 equal selected cases for 51 registrations. Complete compatibility remains unverified.
