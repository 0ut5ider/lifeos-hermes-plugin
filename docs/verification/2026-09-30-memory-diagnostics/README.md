# Native memory diagnostics, 2026-09-30

This unit governs MemoryStatus and MemoryInsights through the private native connector. It preserves authorized operational history. It does not activate lasting-memory ownership or establish the CortexHealth and PULSE boundaries.

## Source and fixture

The public Hermes base is `758ad514eb0e800547e015edf05aa18f78b78d82`. The public LifeOS base is `5e2f2e8c0abde612da0e99c16c0d07d4ec21b88c`. Fresh ordered preparation uses the distributed patches. Each test creates synthetic user data and a private connector. Actual Bun commands call the actual Python memory service. No running installation changes.

Current native source:

`/home/outsider/.cache/lifeos-plugin-memory/source-gate-20260930-diagnostics-closure/lifeos/LifeOS/install`

## Repeat

```sh
PYTHONPATH=.:tests \
LIFEOS_MEMORY_SOURCE=/home/outsider/.cache/lifeos-plugin-memory/source-gate-20260930-diagnostics-closure/lifeos/LifeOS/install \
/home/outsider/.cache/lifeos-plugin-memory/memory-plugin-test-env/bin/python \
-m unittest test_memory_diagnostics -v
```

## Evidence

- `before.txt`: 12 initial cases, eight failed expectations before implementation.
- `first-fix.txt`: those 12 cases pass after the source boundary change.
- `focused.txt`: 16 diagnostic cases and 53 neighboring cases pass in 59.589 seconds.
- `distributed.txt`: all 16 cases pass against freshly prepared distributed source.
- `review-before.txt`: real large proposal, escaped response, and extreme numeric regressions fail before their corrections.
- `typed-fix.txt`: the 20-case suite passes after typed projection and sample controls.
- `limits-primary-after.txt`: the unchanged reviewer probe preserves the large sample and receives the escaped-history response in 118,724 bytes.
- `controls-primary-after.txt`: exact native owner statistics match standalone LifeOS. Scope, path, retirement, and response-limit controls pass.
- `availability-before.txt`: one test reproduces three malformed-edit availability failures.
- `availability-final.txt`: the availability correction exposes one obsolete assertion that also rejects the intended per-sample message.
- `availability-final-corrected-test.txt`: the corrected 21-case diagnostic suite passes in 10.450 seconds.
- `cortex-before.txt`: the separate CortexHealth unit has four open failed expectations in seven cases. This file is not a passing diagnostic gate.

The independent initial report records three limit findings. The first closure passes 73 cases and closes those three findings. It records a smaller malformed-edit availability finding. Final independent closure follows the correction of that flag.

The final independent closure passes all 21 diagnostic cases in 9.959 seconds and reruns the unchanged limits, availability, and controls probes. It finds no remaining material defect in this bounded unit. The earlier 53 neighboring cases remain covered by the preceding 73-case closure. Its report is `docs/agents/2026-09-30-memory-diagnostics-review/final-closure/memory-diagnostics-final-closure.md`.

## Limits

Operational history counts include retained activity after a fact is forgotten. Unclassified diagnostics require unrestricted source authority. The diagnostic projection omits unsupported fields, unsafe numeric values, and excluded display samples. It refuses responses above three mebibytes after serialization. It does not truncate the requested time window to fit that limit. Whole-file input and native validation volume remain unbounded. Independent read operations do not protect against a hostile process with the same operating-system identity.

PULSE request identity, CortexHealth, alternate corpus readers, restore, staged publication, capture and synthesis, lifecycle, ownership transactions, and the release gate remain open.
