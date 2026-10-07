# Verified conversation resume

Date: 2026-10-04. Product revision: `f84931c`. The fixtures use synthetic data and actual native LifeOS operations. The SDK and complete-agent cases use a scripted local HTTP endpoint.

The [initial gate](before.txt) records six failures and two passing refusal controls. Restart admission blocks a retired fact before repair. Live request projection also accepts an applied operating-rule proposal. The correction binds proposal state separately and preserves a stale fact generation until a foreground request passes history repair and final admission.

The [runtime gate](runtime-gate.txt) passes 33 tests and 22 subtests. The expanded [resume and SDK gate](sdk-gate.txt) passes 12 tests and seven subtests. It covers Chat Completions, Responses, an overridden input body, preserved protocol identifiers, failed repair, and a proposal applied after restart admission. The two [complete-agent cases](agent-gate.txt) restart Hermes after a native correction or forget operation. Each case captures one repaired model request and preserves the transcript.

The [regression](regression.txt) passes 100 tests and 68 subtests in 367.25 seconds. It has no skips, failures, errors, or warnings. The [command](regression-command.json), [result](regression-result.json), and [completion marker](regression.done) retain its environment and outcome. The selected tests cover adjacent runtime, history, SDK, complete-agent, ownership characterization, child, context, and provider behavior.

The sources use the prepared Hermes base `758ad514eb0e800547e015edf05aa18f78b78d82` and LifeOS base `5e2f2e8c0abde612da0e99c16c0d07d4ec21b88c` with the existing distributed patches. The command records the exact local fixture paths. The change adds no patch group or dependency.

This evidence closes the bounded fact-only resume contract. Changed prompt reconstruction, full compression rotation, restricted delivery, coherent ownership recovery, and release acceptance remain open. Saved state without verified proposal metadata requires a fresh conversation. No live server changes or memory ownership activation occur.
