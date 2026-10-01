# Governed native turn-start summaries

Date: 2026-09-30. All facts, contexts, proposals, and diagnostics are synthetic.

The public LifeOS base is `5e2f2e8c0abde612da0e99c16c0d07d4ec21b88c`. Hermes remains at prepared base `758ad514eb0e800547e015edf05aa18f78b78d82`. `source-manifest.json` records the ordered distributed patch identities. The fresh fixture is `~/.cache/lifeos-plugin-memory/source-gate-20260930-native-delta/`.

## Evidence

- `tests-before.txt`: seven expected delta failures, three passing native controls, and ten additional existing cases from a fixture import exposed to discovery.
- `empty-guard-failed.txt`: six owner controls reject the attempted empty-text authorization guard. The implementation uses explicit source authorization instead.
- `managed-tests.txt`: all 14 delta cases pass against the editable owned native fixture.
- `fresh-tests.txt`: all 47 delta, retained-source, native delegation, and proposal-delegation cases pass against the fresh distributed bundle. No failures or skips.
- `native-reads-before.jsonl` and `native-reads-after.jsonl`: primary execution of the reviewer's unchanged real native read probe. The corrected composer excludes forgotten log samples and missing-caller output. Other native findings remain open.
- `native-writers-primary.jsonl` and `native-secondary-primary.jsonl`: primary verification of the wider audit's native restore, context, harvester, and diagnostic observations. Process success records measurements, not safe outcomes.
- `patch-identity.json`: patch size, hash, file count, and equality of the root and plugin copies.
- `review-findings-before.txt`: two failing health/shape regressions and one actual eight-second timeout before the review fixes.
- `review-findings-after.txt`: all 50 focused cases pass after the review fixes, with no skips.
- `volume-primary-after.jsonl`: primary execution of the unchanged reviewer volume probe. Five hundred rows complete in 0.603 seconds; the preceding independent result was 34.440 seconds.

## Repeat the focused suite

```sh
PYTHONPATH=.:tests \
LIFEOS_MEMORY_SOURCE=/home/outsider/.cache/lifeos-plugin-memory/source-gate-20260930-native-delta/lifeos/LifeOS/install \
/home/outsider/.cache/lifeos-plugin-memory/memory-plugin-test-env/bin/python \
-m unittest test_memory_delta.MemoryDeltaTests test_memory_sources \
test_memory_delegation test_memory_proposal_delegation -v
```

The 17 new tests cover current delta and heartbeat preservation, unmanaged behavior, real forgotten and corrected native log records, missing identity, unknown authors, changed participants, restricted grants, invalid connectors, existing cursor preservation, source redirects, decoded claims, health findings, and freshness metadata. They also verify malformed-row handling, the native 500-row window under the actual eight-second deadline, and exclusion of older health replay. Full selected log rows receive batched native validation and filtering before sample truncation. Excluded text remains in the native file and does not return as a current sample. The newest excluded health snapshot keeps its enum status and a fixed unavailable-details message when critical.

This evidence does not establish all 132 native source candidates, authenticated PULSE routes, managed restore, staged publication, restricted static prompts, lifecycle coverage, or ownership activation. The preceding full regression has 622 cases and 77 fixture-dependent skips. It predates this 17-case delta addition. No running installation changes.
