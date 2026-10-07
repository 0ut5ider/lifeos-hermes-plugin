# Real configuration evaluation effects

Date: 2026-10-06. Target: isolated accounts on `192.168.8.252`.

Seven selected pairs pass through actual Claude Code and Hermes file tools. Successful Write and Edit sentinel changes run the configured evaluation suite. An intentionally failing assertion publishes `passed: false`. Debounce, absent-runner, and nonsentinel branches preserve their applicable state. The synthetic `CLAUDE.md` sentinel also runs the real evaluator after actual interactive Hermes approval.

The one-case suite requests `PAIR_EVAL_READY` from private FlashNext at medium effort. The actual native `EvalRunner` checks that output and publishes its score. The controls retain the full run result, fire log, lock state, exact tool input, changed target, and final user response. Native child inference uses the pinned native CLI. Hermes child inference uses the installed plugin shim and the same prepared Hermes entry point as its parent.

[wire-proof.json](wire-proof.json) verifies request and response hashes for all 14 clients. Full model request bodies stay private on the development server. [runtime-check.json](runtime-check.json) binds hook, tool, evaluator, native CLI, and plugin source hashes. Each frozen runner also retains its revision and file hashes. A revision in its manifest does not assert that an uncommitted runner already matches that revision.

## Retained failures and fixture corrections

Earlier fixtures lack the complete installed Evals source or call a Hermes executable from another account installation. Those runs fail and remain on the development server. They do not establish a product evaluation defect.

A real one-shot Hermes protected-file request exposes an approval queue wait without a human UI. The [protected-file correction](../protected-instructions/README.md) preserves per-operation human approval and makes unattended refusal immediate. The successful sentinel pair uses the actual interactive panel and operator input.

The seven-case sweep has six passing pairs. Its nonsentinel native tool changes the file correctly, but the final model reply omits the requested `READY` marker. That sweep remains failed in the retained runner log. The nonsentinel repeat adds an explicit final-response instruction to the user prompt and passes both clients. This export selects individually valid pairs and does not call the entire earlier sweep successful.

The first interactive fixture omits the Stop observer. A later fixture records the correct Stop response using the native result field instead of the Hermes text field. The corrected fixture records the actual Hermes response and completed shutdown. No model result is substituted.

These seven pairs add selected effects. Actual batch evaluation and concurrent sentinel edits remain separate acceptance scenarios.
