# Paired generic tool comparison

Date: 2026-10-05. Three cases apply the [generic file and output comparison](../2026-10-05-paired-generic-hooks/README.md) to tool hooks with real shell calls in Claude Code 2.1.272 and Hermes. All six clients pass with two successful model requests each.

| Registration | Hook | Command | Required effect |
| --- | --- | --- | --- |
| `PostToolUse.12.1` | PostToolObserver | `printf` | Loop detector and nudge state for the session; no output. |
| `PostToolUseFailure.2.1` | AlgorithmNudge | `ls` of a missing name | Nudge state for the session; no output. |
| `PreToolUse.1.1` | ContextReduction | `printf` | No output and no change, because the optional `rtk` program is absent. |

The registered command of ContextReduction is a shell script. The driver ran every hook with Bun before this unit; it now runs a `.sh` hook as its own program. The first exploratory run of that case therefore failed on both clients with exit code 1.

## Model call count

The model chooses how many shell calls it makes. In one exploratory run, Claude Code called the shell twice, and that run stopped. The equality check rejects a run with unequal calls, because loop state counts calls. [attempts.txt](attempts.txt) lists every final attempt. The first final attempt passes; earlier attempts used an older driver and expectation set.

[generic-tool-proof.json](generic-tool-proof.json) recomputes the changed file set from the raw captures and checks the exact command in each hook input. [runtime-check.json](runtime-check.json) verifies the 18,153 runtime files. See [source differences](../../parity/source-differences.md).

The focused suite passes 115 tests. Each case is one selected branch. The cumulative ledger contains 99 equal selected cases for 54 registrations. Complete compatibility remains unverified.
