# Rendered memory and managed startup verification

Date: 2026-09-30. All facts, identities, credentials, endpoints, and marker text in these probes are synthetic. The HTTP server binds to loopback. No running server account changes.

The prepared Hermes base is `758ad514eb0e800547e015edf05aa18f78b78d82`. The LifeOS base is `5e2f2e8c0abde612da0e99c16c0d07d4ec21b88c`. The source preparation command applies the distributed patch bundle. The fresh trees are in `~/.cache/lifeos-plugin-memory/source-gate-20260930-app-startup/`.

The Python interpreter is `~/.cache/lifeos-plugin-memory/memory-plugin-test-env/bin/python`. It has the complete declared core, development, and plugin dependencies, including OpenAI SDK 2.24.0. Native calls use Bun with automatic installation disabled and the owned fixture dependencies.

## Results

| Evidence | Expected and observed result |
| --- | --- |
| `plugin-tests.txt` | 582 tests, 505 pass, 77 skip, no failures or errors |
| `closure-primary.txt` | 52 focused runtime, SDK, and native source tests pass |
| `original-sdk-probes-primary.txt` | Five unchanged archived SDK children stop with the expected policy error and zero requests |
| `responses-probes-primary.txt` | Unchanged string and tool-output Responses probes stop before transport |
| `compression-primary.txt` | Actual host summary helper returns no summary and sends zero requests |
| `startup-primary.txt` | Four source markers reach the approved owner; all negative cases expose none |

The full regression collected cases before the last nesting test was added. The subsequent 52-test closure includes that test. The earlier `original-sdk-probes-fixture-error.txt` records missing dependencies, not a successful denial. The corrected runner asserts the error reason and the request count.

The independent final report and unchanged reproduction scripts are in `docs/agents/2026-09-30-memory-rendered-prompts/third-closure/`. Previous review findings remain in the parent and earlier closure directories.

## Limits

These checks verify actual required middleware, SDK calls, the host summary helper, the native SOUL loader, and native startup. They do not establish complete agent invocation, automatic compression rotation, restricted static prompts, final delivery, or ownership activation. Excluded generated input is refused; automatic repair is unfinished. Exact normalized claims are checked. Semantic paraphrase detection and hostile same-user file replacement are not established boundaries.
