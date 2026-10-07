# Paired evaluation trigger branches

Date: 2026-10-05. Two cases exercise the native ConfigEvalFire hook through real Write calls in Claude Code 2.1.272 and Hermes. All four clients complete with status zero, and every model request succeeds. The runs use the development container and the current plugin commit.

The target file is `example.hook.ts`. A file name that ends in `.hook.ts` is a sentinel for this hook. The name `CLAUDE.md` is not usable, because Hermes has an approval gate for instruction file names. See the [write gate note](../../../notes/2026-10-05-instruction-file-write-gate.md).

| Case | Seeded state | Required effect | Result |
| --- | --- | --- | --- |
| Debounce | Evaluation state one moment old | The hook returns no output and preserves the state bytes. | Both clients pass. |
| Missing runner | No state, no runner program | The hook returns no output and writes no state. | Both clients pass. |

Both cases also run AtlasEventCapture, which writes no hint for this file name.

[config-eval-proof.json](config-eval-proof.json) independently reads the raw captures. It checks every hook payload, the matcher, the written file, the unchanged or absent state, and the absent runner program.

[runtime-check.json](runtime-check.json) verifies the 17,583 prepared source files of the [current runtime](../2026-10-05-paired-tool-failure-text/runtime-manifest.json). The two clients run different LifeOS trees; `ConfigEvalFire.hook.ts` differs in identity text only. See [source differences](../../parity/source-differences.md).

The new tests fail before the implementation ([before-output.txt](before-output.txt)). The focused suite passes 100 tests. The fire branch starts the evaluation runner, which makes model requests; that branch remains open. The cumulative ledger contains 79 equal selected cases for 28 registrations. Complete compatibility remains unverified.
