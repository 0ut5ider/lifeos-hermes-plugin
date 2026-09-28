# Universal Stop gate withholding on `.212`

Date: 2026-09-28. The isolated `.212` Hermes checkout moved from `7c6b3b4d8` to `d713bdfec8` on branch `feature/universal-stop-hook`. Production `.211` and `.213` were not changed.

## Reproduction

The existing universal `pre_turn_stop` path emitted each blocked answer through `interim_assistant_callback` and flushed it to Hermes session storage. If the model iteration budget ran out, the finalizer returned that rejected candidate. At the eight-continuation cap, Hermes stopped consulting the hook and allowed the next candidate. Two real agent-loop regressions failed before the change: one saw `withheld candidate` in the interim callback, and one returned it as `final_response` after budget exhaustion.

The first fix treated the eight-continuation cap as a mandatory denial and failed the turn. The [Claude Code hook reference](https://code.claude.com/docs/en/hooks#stop-input) says Claude Code instead overrides the next block and ends the turn. The default was corrected to match Claude Code. The plugin can opt into a failed turn through its Stop hook limit setting.

## Change

The [Hermes Stop gate patch](../patches/hermes-stop-fail-closed.patch) keeps a rejected candidate and its synthetic nudge in the active model context but marks both rows ephemeral. Hermes excludes them from the session database, compression input, and final returned history. Iteration-budget exhaustion returns `stop_gate_blocked` with a safe incomplete-turn message. At the continuation cap, the default allows the last candidate as Claude Code does; a plugin result with `on_limit: fail` instead returns the incomplete-turn message. The hook still gets a decision on the candidate at the cap. Hermes does not stream model text to user callbacks while `pre_turn_stop` is registered, so the gate can decide before delivery. Existing edit-verification interim and fallback behavior remains separate.

The bridge writes each candidate into its private Claude-shaped hook transcript after executing native Stop hooks. A later [Claude Code reference probe](2026-09-28-stop-transcript-timing.md) confirmed that a Stop hook does not see its current candidate in the transcript, while the next Stop sees the prior blocked candidate.

## Verification

- The focused real agent-loop file passed 18 tests after the compatibility correction, including a SQLite session check that stored the allowed answer and neither the rejected candidate nor the synthetic nudge. Before the change, the two new withholding tests failed as expected.
- Nine nearby Hermes files passed 161 tests in the disposable worktree. Two focused files passed 106 tests in the installed `.212` checkout after the correction. No test was skipped in those runs.
- `scripts/prepare_sources.py` created fresh trees with nine Hermes and nine LifeOS patches. Four compared Hermes files exactly matched the tested worktree.
- The gateway service restarted and reported `active` on the patched checkout.
- A live `.212` CLI turn used the installed LifeOS bridge with a disposable native Stop hook and the configured local model. The hook recorded two Stop events, first with `stop_hook_active=false` and then `true`. The CLI output was only `ALLOWED-STOP-212`. The Hermes SQLite `messages` table contained one allowed assistant row, no rejected `FIRST-STOP-212` assistant row, and no internal nudge row.
- Before the compatibility correction, a second live CLI turn set `CLAUDE_CODE_STOP_HOOK_BLOCK_CAP=0`. It exited with code 2 and displayed only `The response did not pass a required final check. Please try again.` The Hermes SQLite table stored that safe assistant row and no rejected `FIRST-STOP-212-BLOCKED` assistant row. That observation documents the first fix, not the final default.
- After the correction, the same live cap-zero command exited with code 0 and displayed `FIRST-STOP-212-BLOCKED`, as Claude Code's continuation-limit contract requires. The focused bridge test verified that its default result omits `on_limit` and its `fail_closed` setting adds `on_limit: fail`. The packaged plugin passed Hermes Plugin Doctor with nine hooks registered; its dashboard save test passed on `.212`.
- A second live cap-zero command temporarily selected `fail_closed` in the `.212` plugin config and asked the local model to answer `STRICT-STOP-212-BLOCKED`. It exited with code 2 and displayed only the safe incomplete-turn message. Hermes SQLite stored that safe assistant row and no assistant row containing the rejected marker. The test restored the original config before returning; `stop_cap_policy` was absent afterward. The gateway and dashboard services remained active.

The live probes used disposable hook settings and did not post to Discord. The focused tests cover the `.212` OpenAI-compatible route. Other provider-specific streaming paths and interrupted/resumed turns need separate verification before this patch can become a general upstream contract.
