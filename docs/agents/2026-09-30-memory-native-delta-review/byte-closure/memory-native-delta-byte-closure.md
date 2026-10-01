# Native delta byte-volume closure review

Date: 2026-09-30 (America/Toronto; subprocess evidence uses October 1 UTC)
Role: Independent bounded closure reviewer
Question: Does the smaller diagnostic RPC projection close the byte-volume failure while preserving native counts, samples, cursor behavior, and unmanaged controls?
Model: GPT-6. The exact model variant is not exposed in this agent context.

## Result

**The byte-volume defect is closed in its unchanged reproducer. A cursor-dependent sample regression remains.**

- **52 focused tests pass in 45.149 seconds**, with no failures or skips.
- All four archived probe programs were rerun unchanged and exited 0 with empty process stderr.
- The original 5,121,152-byte service response is now **326 bytes**. The actual native delta displays the current byte-control update, with no unavailable-service error.
- Existing malformed-row, long retired-claim, latest-health, source-policy, and state-preservation probes continue to pass.
- A new real native continuation probe shows that after two older additions have been surfaced, the next current addition is counted but its sample disappears. With the same log and pre-followup cursor, the unmanaged native path still displays the current sample.

No code edits, commits, live imports, SSH, account changes, or memory/journal calls were made. The evidence and source snapshots are saved before returning. The broader native audit remains open and ownership activation is not approved by this review.

## Snapshot and commands

Repository: `/home/outsider/Projects/Hermes_agent/LifeOS_plugin`, branch `feature/lifeos-memory`, HEAD `c5abe4731382a37045a627563c78b9640f529255` plus the requested working diff. Metadata correction: the original draft carried forward the earlier `5cdb33d` baseline; that was not the active branch HEAD for this byte review.

Fresh public prepared source:

`/home/outsider/.cache/lifeos-plugin-memory/source-gate-20260930-delta-bytes/lifeos/LifeOS/install`

Native base: `5e2f2e8c0abde612da0e99c16c0d07d4ec21b88c`, with the distributed patch. The existing 13-file native patch bundle includes the delta optional count fields. No Hermes behavior change is claimed.

Interpreter: `/home/outsider/.cache/lifeos-plugin-memory/memory-plugin-test-env/bin/python`.

Inspected production paths:

- `lifeos_hook_bridge/memory_sources.py`: full-row validation, retirement filtering, autonomic-row selection, smoke exclusion, count and sample projection.
- `lifeos_hook_bridge/memory_service.py`: existing governed source dispatch.
- Native `hooks/MemoryDeltaSurface.hook.ts`: optional count consumption, cursor ordering, native sample limits, heartbeat count.
- Native `LIFEOS/TOOLS/lib/MemoryAccess.ts`: existing response-size limit and unavailable behavior.
- Native composer and registration, both patch copies, and `tests/test_memory_delta.py`.

Exact copies are under `raw/sources/`. `raw/hashes-before.json` and `raw/hashes-after.json` record the reviewed hashes and their final comparison. The final capture detects changes to memory_sources.py and test_memory_delta.py because the parent reproduced D5, added its regression, and changed projection after the 52-test run finished. The initial source copies and unchanged probe outputs preserve the reviewed failing snapshot. This report does not clear that subsequent correction; it belongs to a separate final closure.

Focused command, also recorded in `raw/run_tests.sh`:

```sh
PYTHONPATH=.:tests \
LIFEOS_MEMORY_SOURCE=/home/outsider/.cache/lifeos-plugin-memory/source-gate-20260930-delta-bytes/lifeos/LifeOS/install \
LIFEOS_HERMES_SOURCE=/home/outsider/.cache/lifeos-plugin-memory/source-gate-20260930-delta-bytes/hermes \
/home/outsider/.cache/lifeos-plugin-memory/memory-plugin-test-env/bin/python \
-m unittest test_memory_delta.MemoryDeltaTests test_memory_sources test_memory_delegation test_memory_proposal_delegation -v
```

Result: **52 passed, 45.149 seconds, exit 0**. See `raw/tests.txt` and `raw/tests.done`. The parent's earlier complete 639-test run predates this byte fix and was not rerun or claimed by this reviewer.

Archived probe runner:

```sh
/home/outsider/.cache/lifeos-plugin-memory/memory-plugin-test-env/bin/python docs/agents/2026-09-30-memory-native-delta-review/byte-closure/raw/run_archived.py
```

It records the exact child argv, environment, script hashes, outputs, stderr, and exit codes in `raw/archived-results.json`. The four original programs are shape, row-volume, policy/health controls, and byte-volume probes. Their bodies were not modified.

New cursor probe:

```sh
PYTHONPATH=.:tests \
LIFEOS_MEMORY_SOURCE=/home/outsider/.cache/lifeos-plugin-memory/source-gate-20260930-delta-bytes/lifeos/LifeOS/install \
/home/outsider/.cache/lifeos-plugin-memory/memory-plugin-test-env/bin/python \
docs/agents/2026-09-30-memory-native-delta-review/byte-closure/raw/probe_cursor_samples.py
```

Output: `raw/cursor-samples.txt`.

## What the correction preserves

The service still validates the selected full 500-row window in one native batch. It checks original JSON and decoded text against native validation and retained claims before creating the smaller response. Retired text is not made safe merely by omitting it from the first displayed samples.

Only autonomic `MemorySystem.add` rows are projected. Rows containing smoke-test additions are skipped using the native skip pattern. Count fields are computed from the actual validated arrays rather than trusting any input count fields. The returned row retains its timestamp, file label input, writer, a sample subset, and full addition/eviction counts.

Native delta uses those optional counts for both current-turn totals and last-curation heartbeat. When the fields are absent, unmanaged logs retain the native array-length fallback. The new 40-entry test verifies `+40 learned`, the first two samples in order, and `last curation +40 new` on the next call. Its entries are real native curation output; the test explicitly sets the log's writer to the autonomic identity to exercise that branch.

The original byte-volume fixture uses 499 large genuine native curation-row copies plus one unchanged current update. The large nonautonomic rows no longer fill the response. Results:

| Measurement | Previous closure | Current |
| --- | ---: | ---: |
| Input log bytes | 5,065,665 | 5,065,665 |
| Projected source content bytes | 5,065,664 | 237 |
| Serialized service response bytes | 5,121,152 | 326 |
| RPC buffer limit | 4,194,304 | 4,194,304 |
| Actual delta output | unavailable, empty | current update present |
| Native delta stderr | service unavailable | empty |

The unchanged long-retired-claim case still excludes the complete removed claim before shortening. Malformed rows still permit later valid updates. The newest-health controls preserve current status without replaying older findings. After wildcard project access is narrowed, the source check refuses the caller and existing cursor/injection/heartbeat bytes remain unchanged.

These are bounded controls. The response is not proven byte-bounded for arbitrary fabricated multi-megabyte string fields. The confirmed normal native curation reproduction is fixed.

## Remaining finding D5: sample budgets are consumed before cursor filtering

**Severity: medium, ordinary authorized owner continuation. Confirmed with real native writes and a same-state unmanaged control.**

### Cause

`memory_sources._read_log` initializes `learned_samples` and `dropped_samples` once for the complete retained window. It allocates only the first two addition strings and first eviction string across that window.

The source request contains no cursor. The native consumer obtains the projected rows, then applies its cursor check:

```text
if (cursor && row.ts <= cursor) continue
```

Thus already-surfaced rows consume the service's sample budget even though the native consumer skips them. A later unsurfaced row retains its counts but has empty sample arrays. This changes native behavior after ordinary successful turns.

### Reproduction

The probe uses actual native remember operations in a private approved owner fixture:

1. Remember `Synthetic first sample alpha` and `Synthetic second sample beta`.
2. Run the standalone delta once. It displays both samples and saves its cursor.
3. Preserve the exact cursor bytes.
4. Remember `Synthetic later sample gamma`.
5. Run the managed delta.
6. Restore the preserved pre-followup cursor and remove only the private fixture's connector.
7. Run the same native delta against the same log under its unmanaged behavior.

Observed managed followup:

```text
MEMORY: +1 learned · freshness: no data
```

Observed unmanaged control:

```text
MEMORY: +1 learned ... "principal: RULE: Synthetic later sample gamma" ...
```

The ellipses above abbreviate presentation only. Exact unmodified output is in `raw/cursor-samples.txt`. Both native calls have clean stderr and exit 0. The result records `managed_has_new_sample: false` and `unmanaged_has_new_sample: true`.

The count remains correct, but the owner loses the new claim sample. The first two historical additions can consume the sample budget on every subsequent turn until those rows leave the tail or are excluded. The same selection ordering applies to the first eviction budget by source inspection; this review does not claim a separate empirically exercised eviction continuation case.

### Smallest correction

Return the first two additions and first eviction **per projected row**, with complete count fields. Let the native consumer retain its existing global sample limits after it applies the cursor. For normal native hot-entry sizes, 500 rows of these small per-row samples remain far below the previous full-row payload while preserving native ordering. Alternatively, supply and validate a caller cursor before service-level global sample selection, but that changes the protocol and must preserve heartbeat use of older rows.

Keep full-row validation and retirement filtering before sample projection. Do not restore raw full log bodies merely to recover sample selection.

Required regression cases:

- The saved three-write, two-turn reproducer, comparing the current sample with unchanged native behavior.
- Previously surfaced additions followed by several new rows: first two new samples in native order and full new counts.
- Previously surfaced eviction followed by a permitted new eviction: first new eviction sample, correct drop count.
- Smoke rows and denied/retired rows do not consume sample budget.
- Current volume, byte-volume, native heartbeat, and unmanaged controls remain green.

## Scope and disposition

D4, the measured byte-volume failure, is closed for its genuine native-row reproducer. D1-D3 remain closed by unchanged archived probes. D5 must be fixed and reviewed before claiming this bounded delta unit complete.

No additional broad native audit was performed. Other native readers/writers, authenticated PULSE delivery, static restricted prompts, full lifecycle behavior, installation recovery, and ownership activation remain open. Only temporary synthetic fixture data and repository evidence artifacts were changed by this reviewer.
