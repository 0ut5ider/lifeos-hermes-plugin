# PULSE snapshot closure review

Date: 2026-10-01

Role: Independent code and behavior reviewer, Cerebo

Question: Do the current-hot and dynamic-key fixes close the two snapshot findings without introducing authority, concurrency, or native schema regressions?

Model: GPT-6. The exact model variant is not exposed in this agent context.

## Outcome

**The two original reproductions are fixed, but this snapshot is not ready for bounded closure.** The unchanged current-fact, retired-key, and controls probes all pass. The 70-test gate finishes with **68 passing tests and two errors** in 42.382 seconds. A new real fixture probe also confirms that structural-key exemptions are both incomplete and applied to an incorrect view.

The primary agent independently reproduced these outcomes. It received the stable source capture before beginning further corrections. This report describes the archived reviewed snapshot, not subsequent changes.

## Source snapshot

Repository HEAD: `c2198bd3b295a3676dcde8d9f5d0db0b7e242eca`, branch `feature/lifeos-memory`, with working additions and corrections.

Native fixture: `/home/outsider/.cache/lifeos-plugin-memory/source-gate-20261001-cortex-final/lifeos/LifeOS/install`

Interpreter: `/home/outsider/.cache/lifeos-plugin-memory/memory-plugin-test-env/bin/python`

| File | SHA-256 |
|---|---|
| `memory_pulse.py` | `634953117fd3b30acd27fb3b486b34101408c38d48cc9dbb797a0902c457c7ae` |
| `memory_preferences.py` | `d451a4d7cb3ea50be04fc169a386d3fd900f4f16c68f38d6a445e15820926eb5` |
| `memory_native.ts` | `f3e561beaf5f00becc596eac2062345e9eee11a14bb9aadc4ae80733b4ab79f3` |
| `memory_diagnostics.py` | `9af81d9793c5957b46dd29ec18bf0a8da6a5ce77168d4cc9ac13c949183412ee` |
| `test_memory_pulse.py` | `0cc33db7aa3feabf9a560d6030882e51c7d74702f7558091ca97bc27ea2013b7` |
| Native `LIFEOS/PULSE/modules/memory.ts` | `daf44ab1f0a0333feab01fc2a268d2f2eb5af7523c5974fb37512cf409441449` |

Absolute paths, before/after hashes, and source copies are under `raw/`. All six hashes remained unchanged through the tests and probes. The native module and neighboring preferences/native worker changes remain identical to the initial review.

## Original findings verified fixed

### Current corrected fact preservation

The unchanged `../raw/probe_current.py` exits zero. The committed replacement remains visible in the canonical current hot field even though its text contains a superseded shorter claim. The implementation obtains entries from `_hot_snapshot`, removes raw native hot fields before historical filtering, then appends the exact verified current entries.

The new regression separately verifies that the same string in historical review-state content still receives retained filtering. The Unicode regression verifies native UTF-16 character counts.

### Retired dynamic keys

The unchanged `../raw/probe_keys.py` exits zero. The original forgotten marker is removed from the native `byType` map and nested state object across all three views. The implementation now collects dictionary keys for retained filtering and omits excluded dynamic fields. Encoded JSON objects are inspected through the existing decoded-value projection.

### Authority, path, and native controls

The unchanged `../raw/probe_controls.py` exits zero. Restricted scope still rejects before reading a synthetic FIFO. Cadence and run-directory redirects are refused. The native 10/20 runs limits, 200/5 fire windows, and 50/5 proposal windows remain unchanged. Health counts, native derived state, and typed timestamps remain correct in that fixture. Nested and encoded value markers are removed. Native data files remain unchanged; the original controls explicitly distinguish normal registry SQLite byte changes from native publication.

## Remaining findings

### 1. Incorrect state-view schema inheritance leaks a retired dynamic key

Priority: Medium, retained-key boundary defect.

`_structural_field` returns for the state view only when the path is empty. Non-root state paths fall through into health schema rules. A nested `reviewer.status` field consequently inherits the health `_evidence_field` exemption even though the state schema declares no reviewer object.

The real probe remembers and forgets `RULE: status`, then writes synthetic review-state data:

```json
{"pending_review":true,"reviewer":{"status":1},"nested":{"status":1}}
```

The standalone governed state view returns `reviewer.status`, while the snapshot's `reviewState` removes it. The unrelated nested status key is removed in both cases. This difference isolates the incorrect health-path exemption.

Evidence: `raw/probe_structural.py`, `raw/structural.txt`. `dynamic_state_status_removed` is false.

Smallest correction: terminate state-view schema handling for all paths. Only its declared root fields should receive structural exemptions. Keep arbitrary nested content keys subject to retained filtering.

### 2. Incomplete structural schemas remove legitimate native fields

Priority: Medium, native output contract regression.

The same probe places a current pending proposal in the native queue. After retiring the word `status`, the raw native proposal has `status: pending`, but the governed `proposalsRecent` row loses that field. The snapshot has no structural exemptions for its proposal rows, despite having a separate value exemption for valid proposal statuses.

Evidence: `raw/structural.txt`. `fixed_proposal_status_preserved` is false. This affects the actual native row returned by `handleRequest`, not a simulated native object.

The requested neighboring tests independently expose the same omission class in health projection:

```text
ERROR: test_report_clock_exemption_requires_a_valid_structural_timestamp
KeyError: 'created_at'

ERROR: test_retired_operational_clock_does_not_change_reviewer_assessment
KeyError: 'evidence'

Ran 70 tests in 42.382s
FAILED (errors=2)
```

When the source timestamp falls before the retirement cutoff, key collection can exclude every text key. Incomplete fixed schemas then remove operational containers or fields before their typed values can be preserved. These are regressions in previously passing health tests and must remain in the closure gate.

Smallest correction: declare the actual fixed fields at each supported native output location, including proposal rows and the health clock/evidence shapes. Keep these exemptions path-specific. A field name at one native schema location must not exempt arbitrary nested content elsewhere. Re-run the existing health tests and the new exact-namespace probe together.

## Concurrency and cache check

An additional real fixture probe pauses execution at the entry to `filter_report` using an observational Python trace. A second thread calls the actual governed `forget` operation. The writer remains blocked while the snapshot is paused, then commits after projection completes. The first snapshot contains the pre-forget fact; the next snapshot has zero current hot entries.

Evidence: `raw/probe_lock.py`, `raw/lock.txt`.

This verifies that the new existing-connection path retains the cooperating native transaction lock across current-hot verification, diagnostic projection, and current-hot assembly. The second read observes the new generation. No snapshot cache was introduced. This is a synthetic cooperating-writer test, not a same-UID hostile-process sandbox guarantee.

## Commands and evidence

All commands use the repository root and:

```sh
export PYTHONPATH=.:tests
export LIFEOS_MEMORY_SOURCE=/home/outsider/.cache/lifeos-plugin-memory/source-gate-20261001-cortex-final/lifeos/LifeOS/install
```

The interpreter is the complete environment listed above.

```sh
python -m unittest test_memory_pulse test_memory_cortex_health test_memory_diagnostics -v
python docs/agents/2026-10-01-memory-pulse-snapshot-review/raw/probe_current.py
python docs/agents/2026-10-01-memory-pulse-snapshot-review/raw/probe_keys.py
python docs/agents/2026-10-01-memory-pulse-snapshot-review/raw/probe_controls.py
python docs/agents/2026-10-01-memory-pulse-snapshot-review/final-closure/raw/probe_structural.py
python docs/agents/2026-10-01-memory-pulse-snapshot-review/final-closure/raw/probe_lock.py
```

`raw/run_tests.sh` records the exact interpreter and detached test command. `raw/tests.txt` contains the full output; `raw/tests.done` is 1. `raw/probe-results.json` records exact interpreter commands and zero return codes for all three unchanged probes. Their new raw results are `current.txt`, `keys.txt`, and `controls.txt`; original evidence is untouched.

## Scope and next action

Correct the view inheritance and missing fixed-schema fields, then repeat the focused gate and unchanged probes. The original fixes and cooperating-lock behavior have positive independent evidence. No closure is claimed while the two regression errors and exact-namespace failures remain.

HTTP authentication, relay identity, lifecycle, unrestricted source inventory, arbitrary-volume performance, same-UID hostile processes, and ownership activation remain outside this review. No implementation, dependency, account, live configuration, or external system was changed. Only the evidence directory and temporary synthetic fixtures were written.
