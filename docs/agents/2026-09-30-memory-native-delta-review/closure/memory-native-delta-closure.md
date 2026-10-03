# Native delta closure review

Date: 2026-09-30 (America/Toronto; raw subprocess timestamps use October 1 UTC)
Role: Independent bounded closure reviewer
Question: Do the batching, row-shape, and latest-health fixes close the three measured delta defects while preserving the governed native owner path?
Model: GPT-6. The exact model variant is not exposed in this agent context.

## Conclusion

**The original three findings are closed by the reviewed snapshot. One adjacent transport-size defect remains.**

- All **50 focused tests passed in 39.163 seconds**, with no failures or skips.
- The unchanged archived 500-row probe completes in **0.589 seconds**, compared with **34.440 seconds** before batching.
- The unchanged malformed-row probe now skips the invalid row and renders the following valid update with clean stderr.
- The unchanged health probe no longer replays an older critical warning when the newest snapshot contains excluded text.
- Additional controls preserve the newest `critical`, `warn`, or `ok` enum while removing retired diagnostic details, and preserve native state after project permission is narrowed.

However, a 500-row window can exceed the existing RPC byte limit. An actual native 40-entry curation row, repeated 499 times and followed by one current update, produces a **5,121,152-byte serialized service response**. Native `MemoryAccess.ts` caps that response at **4,194,304 bytes**. The service returns a valid current update, but the real native delta command emits no output and reports that the service is unavailable.

This review therefore closes D1-D3 from `../memory-native-delta-review.md`, but does not close the bounded delta unit until the transport budget is handled. It does not clear any other native audit finding or approve ownership activation.

## Reviewed source and limits

Plugin: `/home/outsider/Projects/Hermes_agent/LifeOS_plugin`, branch `feature/lifeos-memory`, committed baseline `5cdb33d39d82d4cb60f250e4df855d4dffcf83c2` plus the requested working changes.

Fresh public native fixture:

`/home/outsider/.cache/lifeos-plugin-memory/source-gate-20260930-native-delta/lifeos/LifeOS/install`

Public LifeOS base: `5e2f2e8c0abde612da0e99c16c0d07d4ec21b88c`, with the distributed memory patch. The native bundle was unchanged from the initial delta review. The new correction changes `memory_sources.py` and adds three delta regression cases.

Interpreter: `/home/outsider/.cache/lifeos-plugin-memory/memory-plugin-test-env/bin/python`.

The coding-rules skill was read before this review. No implementation files were edited, and no commit, push, SSH, account change, live import/bootstrap, memory call, or journal call occurred. All native operations used disposable synthetic records and the owned prepared sources.

Source copies are under `raw/sources/`. SHA-256 values are in `raw/hashes-before.json` and `raw/hashes-after.json`. **Every captured reviewed source hash remained unchanged between those captures.** The source copies include both patch variants, the affected Python service/source code, tests, native helper, composer, delta surface, and hook registration.

## Verified corrections

### D1: per-row validation cost

`_read_log` now selects the final 500 nonblank write-log rows before constructing native validation items. It calls the existing `validate_batch` operation once for those candidate rows. The worker applies the same native sanitizer to each item. Python then performs the retained-claim filtering per candidate.

This removes the former native worker launch for every historical row. Selection order matches the native delta reader's existing last-500 nonblank window. The raw source bytes are still read from disk, so this is a bound on expensive row processing, not a claim of constant file I/O or constant memory consumption for arbitrarily large log files.

The unchanged archived probe produced:

| Rows | Log bytes | Before | Current |
| ---: | ---: | ---: | ---: |
| 1 | 339 | 0.580 seconds | 0.609 seconds |
| 100 | 33,900 | 7.932 seconds | 0.617 seconds |
| 500 | 169,500 | 34.440 seconds | 0.589 seconds |

All current cases exit 0, have empty stderr, and contain the expected permitted update and counts. The focused regression also uses 1,000 rows and an actual 8-second subprocess timeout, asserting that only the native 500-row tail contributes to the displayed count. It passes.

No production timing instrumentation or alternate implementation was used. The archived probe files were executed unchanged and their hashes are saved.

### D2: parsed but malformed write rows

The source reader now requires string `ts` and `file` fields, a parseable timezone-bearing write timestamp, and arrays of string additions/evictions. It skips malformed row shapes individually before native presentation.

The unchanged original probe's `additions` string no longer produces a TypeError. The valid following row renders as `+1 learned`, and the fixture's clean-stderr checks pass. Additional independent cases cover an invalid timestamp, list-valued file, numeric addition element, and boolean evictions field before a valid current row. That control still renders exactly one valid update.

This verifies the inspected malformed types and existing registered caller path. It is not an exhaustive fuzzer result for all JSON resource-exhaustion shapes.

### D3: latest-health snapshot identity

For health logs, `_read_log` now chooses only the newest nonblank source row before validation/filtering. It cannot silently select an older surviving snapshot. If the newest row is well-shaped but its details are excluded, `_health_status` preserves only the controlled status enum and fixed safe findings. Excluded critical details become the fixed message:

`Memory diagnostic details are unavailable under the current policy.`

The unchanged original probe now omits the old critical warning. Additional controls verify:

- Newest excluded `critical`: current critical status remains, with the fixed unavailable-details message and no retired or older text.
- Newest excluded `warn` or `ok`: the same enum is returned by the service; the native critical-warning renderer does not emit a critical warning.
- Newest malformed JSON after an older critical row: the old finding does not reappear.

This preserves a useful owner health signal without claiming that excluded diagnostic bodies were reviewed or displayed.

## Remaining finding D4: a valid 500-row window can exceed the RPC response limit

**Severity: medium, authorized owner functionality. Confirmed with a real native producer row and actual native reader.**

The row-count bound does not imply a byte bound compatible with the connector. `LIFEOS/TOOLS/lib/MemoryAccess.ts` uses `spawnSync(..., maxBuffer: 4 * 1024 * 1024)`. The source service currently returns the complete permitted log lines as one JSON string.

### Reproduction

`raw/probe_delta_bytes.py` performs these operations in a disposable fixture:

1. Calls actual governed native curation to publish 40 valid hot entries, each 244 characters. The native operation commits and produces the real write-log row.
2. Calls actual remember to add `RULE: Synthetic current byte control`. That operation also commits.
3. Builds a synthetic 500-row history from 499 copies of the genuine large row and the unchanged current update row. This is a volume fixture, not a claim that the service actually performed 499 repeated identical replacements.
4. Runs the real approved standalone `MemoryDeltaSurface.hook.ts` through its configured native RPC connector.
5. Calls the real source service directly to measure its returned content and JSON envelope, without changing the implementation.

Observed results:

| Measurement | Result |
| --- | --- |
| Native curation entries | 40 |
| Entry characters | 244 |
| Large native row bytes | 10,150 |
| Window rows | 500 |
| Log bytes | 5,065,665 |
| Source content bytes | 5,065,664 |
| Serialized service response bytes | 5,121,152 |
| Native RPC maximum response buffer | 4,194,304 |
| Direct service result | `ok: true`, includes current control |
| Native delta elapsed time | 0.462 seconds |
| Native delta exit | 0 |
| Native delta stdout | empty |
| Native delta stderr | `MemoryDeltaSurface error: The native memory service is unavailable` |

The genuine curation row uses the normal governed writer identity. The delta's later writer filter would ignore that history and still render the current relevant update. The oversized RPC prevents the consumer from reaching that filter. Thus unrelated permitted historical rows can suppress a real current update.

The response size and source limit establish the transport mismatch; the native output confirms its externally visible behavior. No claim is made that this bypasses privacy checks or leaks the body. It fails closed for content but incorrectly reports a usable local service as unavailable and loses owner status output.

### Recommended correction and regression

Give managed diagnostic output an explicit byte contract compatible with the native connector. A bounded projection or paged read can preserve counts, permitted samples, current health, and cursor semantics without transporting every full historical field. If the existing complete-row contract is retained, its permitted maximum and transport buffer must agree. Do not silently drop the newest current update to fit a budget, and do not reintroduce filtering after truncation.

The smallest useful regression is the saved native-row fixture, with clean stderr and the current byte-control update present through the real connector. Include a supported full curation row, not only short one-addition rows. Preserve the new batching and existing missing/restricted caller denials.

## Policy, path, and preservation controls

The 50-test focused gate includes all 17 delta cases, 17 source cases, 10 delegation cases, and six proposal-delegation cases. These cover the early source collection authorization, invalid connector refusal, missing context, unknown author, changed participants, restricted destination, existing state preservation, physical redirects, decoded retired claims, owner freshness and health, and unmanaged native behavior.

The additional `probe_controls.py` changes an already admitted destination from wildcard projects to only `lab` while retaining all native categories. `check_sources` returns a structured refusal. The composer returns empty output and preserves the previous cursor, injection-state, and heartbeat bytes exactly. This confirms wildcard project authority is required independently of category coverage.

The unchanged shape probe also continues to exclude a long retired claim whose identifying suffix falls beyond the native display cutoff, while retaining the current control.

## Commands and raw artifacts

The exact focused command is in `raw/run_tests.sh` and uses:

```sh
PYTHONPATH=.:tests \
LIFEOS_MEMORY_SOURCE=/home/outsider/.cache/lifeos-plugin-memory/source-gate-20260930-native-delta/lifeos/LifeOS/install \
LIFEOS_HERMES_SOURCE=/home/outsider/.cache/lifeos-plugin-memory/source-gate-20260930-native-delta/hermes \
/home/outsider/.cache/lifeos-plugin-memory/memory-plugin-test-env/bin/python \
-m unittest test_memory_delta.MemoryDeltaTests test_memory_sources test_memory_delegation test_memory_proposal_delegation -v
```

Result: **50 passed, 39.163 seconds, exit 0**. See `raw/tests.txt` and `raw/tests.done`.

The probe commands use `PYTHONPATH=.:tests` and the same `LIFEOS_MEMORY_SOURCE`:

```sh
/home/outsider/.cache/lifeos-plugin-memory/memory-plugin-test-env/bin/python docs/agents/2026-09-30-memory-native-delta-review/raw/probe_delta_shapes.py
/home/outsider/.cache/lifeos-plugin-memory/memory-plugin-test-env/bin/python docs/agents/2026-09-30-memory-native-delta-review/raw/probe_delta_volume.py
/home/outsider/.cache/lifeos-plugin-memory/memory-plugin-test-env/bin/python docs/agents/2026-09-30-memory-native-delta-review/closure/raw/probe_controls.py
/home/outsider/.cache/lifeos-plugin-memory/memory-plugin-test-env/bin/python docs/agents/2026-09-30-memory-native-delta-review/closure/raw/probe_delta_bytes.py
```

Outputs are respectively `raw/archived-shapes.txt`, `raw/archived-volume.txt`, `raw/controls.txt`, and `raw/delta-bytes.txt`.

Two reviewer fixture/setup errors are preserved rather than hidden:

- Initial evidence copying omitted the artifact `sources/` directory. No tests ran in that attempt. The directory was created and the runner was started again. See `raw/artifact-setup-error.txt` and `raw/initial-runner-error.txt`.
- The first byte-volume fixture included trailing spaces in generated desired hot entries. Native curation rejected that requested snapshot with `Native curation did not publish the complete requested snapshot`. The corrected fixture strips those trailing spaces; both actual publication operations then commit. The initial script and output remain `raw/probe_delta_bytes_initial.py` and `raw/delta-bytes-fixture-error.txt`. No runtime or production code was altered to make the probe run.

## What remains open

Only D4 remains from this bounded closure review. The broader source audit findings concerning other native readers, PULSE delivery, diagnostics, restore, staged publication, and app context remain open. No conclusion here covers the remaining inventory candidates, full reviewer/deriver lifecycle, restricted static prompts, whole history/rotation behavior, installation recovery, browser delivery, or ownership activation.

Adrian's relevant review point is the diagnostic transport contract: the owner must retain current status and useful bounded samples when native rows are large. The implementation should preserve both the native functionality and the existing authorization/retirement guarantees.
