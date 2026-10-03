# Governed native turn-start summaries

Date: 2026-09-30. All facts, contexts, proposals, and diagnostics are synthetic.

The public LifeOS base is `5e2f2e8c0abde612da0e99c16c0d07d4ec21b88c`. Hermes remains at prepared base `758ad514eb0e800547e015edf05aa18f78b78d82`. `source-manifest.json` records the ordered distributed patch identities. The fresh fixture is `~/.cache/lifeos-plugin-memory/source-gate-20260930-native-delta/`.

The subsequent byte correction uses `~/.cache/lifeos-plugin-memory/source-gate-20260930-delta-bytes/`. `source-manifest-bytes.json` and `patch-identity-bytes.json` record its current bundle. The patch still changes 13 native files and adds no Hermes patch.

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
- `full-regression-before-byte-fix.txt`: 639 cases complete, with 562 passes, 77 skips, and no failures. This run predates the later byte and sample corrections.
- `byte-tests-before.txt`: the real large-curation connector test fails, while the native count preservation control passes.
- `cursor-test-before.txt`: the following update loses its sample when the service chooses global samples before native cursor filtering.
- `byte-tests-final.txt`: all 53 focused cases pass after the byte and cursor corrections.
- `byte-probe-primary-final.txt`: genuine native operations build a 5,065,665-byte log. The corrected summary response uses 326 bytes, retains the current update, and completes with clean stderr.
- `cursor-probe-primary-final.txt`: the unchanged reviewer probe produces identical managed and unmanaged follow-up samples.
- `controls-primary.txt` and `shapes-primary-after.txt`: primary reruns of the unchanged health, policy, long-claim, and malformed-row controls.

## Repeat the focused suite

```sh
PYTHONPATH=.:tests \
LIFEOS_MEMORY_SOURCE=/home/outsider/.cache/lifeos-plugin-memory/source-gate-20260930-delta-bytes/lifeos/LifeOS/install \
/home/outsider/.cache/lifeos-plugin-memory/memory-plugin-test-env/bin/python \
-m unittest test_memory_delta.MemoryDeltaTests test_memory_sources \
test_memory_delegation test_memory_proposal_delegation -v
```

The 20 new tests cover current delta and heartbeat preservation, unmanaged behavior, real forgotten and corrected native log records, missing identity, unknown authors, changed participants, restricted grants, invalid connectors, existing cursor preservation, source redirects, decoded claims, health findings, and freshness metadata. They also verify malformed-row handling, the native 500-row window under the actual eight-second deadline, exclusion of older health replay, the connector byte budget, full curation counts, and sample selection after the cursor. Full selected log rows receive batched native validation and filtering before response projection. Each returned row keeps at most two addition samples and one eviction sample, plus their full counts. Native rendering selects global samples after cursor filtering. Excluded text remains in the native file and does not return as a current sample. The newest excluded health snapshot keeps its enum status and a fixed unavailable-details message when critical.

This evidence does not establish all 132 native source candidates, authenticated PULSE routes, managed restore, staged publication, restricted static prompts, lifecycle coverage, or ownership activation. The current focused result has 53 cases without skips. The 639-case full regression predates the last three test additions and byte correction. Its 77 fixture-dependent skips remain release requirements. No running installation changes.

Final independent closure passes 53 cases in 51.271 seconds and finds no remaining material defect in the bounded delta scope. The report is `docs/agents/2026-09-30-memory-native-delta-review/final-closure/memory-native-delta-final-closure.md`. Its five unchanged probes and additional sample-order control pass. `sample-parity-primary.txt` records the primary rerun of that control. Whole-file I/O remains unbounded, and arbitrary fabricated oversized fields are not covered by the normal native curation result.
