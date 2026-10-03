# Governed PULSE snapshot review

Date: 2026-10-01

Role: Independent code and behavior reviewer, Cerebo

Question: Does the new owner PULSE snapshot projection preserve current native facts, diagnostic state, and route shapes while enforcing source authority and excluding retired claims?

Model: GPT-6. The exact model variant is not exposed in this agent context.

## Outcome

The bounded unit has **two confirmed defects**. The requested 66 tests pass independently in 39.288 seconds, but real native fixture probes show a retired claim leaking through dynamic JSON keys and a valid current corrected fact being hidden. Both findings were sent to the primary agent before this report. No implementation was changed during this review.

This report covers the new snapshot projection and its shared diagnostic filter changes. It does not approve ownership activation or PULSE HTTP authentication. The existing raw native HTTP routes and the planned authenticated relay are explicitly outside this unit.

## Reviewed snapshot

Repository: `/home/outsider/Projects/Hermes_agent/LifeOS_plugin`

Branch: `feature/lifeos-memory`

HEAD: `c2198bd3b295a3676dcde8d9f5d0db0b7e242eca`, with the working diff captured in `raw/working-diff.patch`.

Public prepared native source: `/home/outsider/.cache/lifeos-plugin-memory/source-gate-20261001-cortex-final/lifeos/LifeOS/install`

Interpreter: `/home/outsider/.cache/lifeos-plugin-memory/memory-plugin-test-env/bin/python`

| Reviewed file | SHA-256 |
|---|---|
| `lifeos_hook_bridge/memory_pulse.py` | `cf43884076568170bf7bc59176e22f65ebf60fb6a1bc34795b032e7e4de9f2f5` |
| `lifeos_hook_bridge/memory_preferences.py` | `d451a4d7cb3ea50be04fc169a386d3fd900f4f16c68f38d6a445e15820926eb5` |
| `lifeos_hook_bridge/memory_native.ts` | `f3e561beaf5f00becc596eac2062345e9eee11a14bb9aadc4ae80733b4ab79f3` |
| `lifeos_hook_bridge/memory_diagnostics.py` | `2483d29054038bdb0ccb69f3fee7747679603434255c2c3c8a3f1ac12e89d641` |
| `tests/test_memory_pulse.py` | `884e3dda370dae076812bad8087e8c2ae35d0c0d9464afbf04c74811a3ed3097` |
| Native `LIFEOS/PULSE/modules/memory.ts` | `daf44ab1f0a0333feab01fc2a268d2f2eb5af7523c5974fb37512cf409441449` |

Every listed hash remained unchanged at the end. Exact absolute paths are in `raw/hashes-before.json` and `raw/hashes-after.json`. Source copies are in `raw/sources/`. No native or host patch changed in this unit.

## Finding 1: Retired text survives in dynamic JSON keys

Priority: High for the promised retained-text boundary.

`memory_diagnostics.py:filter_report` checks that dictionary keys use ASCII structural syntax, then collects and projects only their values. The PULSE native reader exposes arbitrary review-state objects and JSON parsed from a dispatch log's `By type:` field. A retained claim that is a valid key passes the syntax check and is returned unchanged.

The real fixture probe performs these operations:

1. Remember `RULE: SyntheticPulseRetiredKey` through the governed native service.
2. Forget the returned reference successfully.
3. Write a synthetic historical dispatch row containing `By type: {"SyntheticPulseRetiredKey":1}`.
4. Write a synthetic review-state object containing a nested field with the same key.
5. Call governed `runs`, `state`, and `snapshot` views.

All three views return the forgotten claim. Run counts and the nested state object retain their raw shape, including the key. This does not depend on bypassing source attestation or using the raw HTTP route.

Evidence: `raw/probe_keys.py` and `raw/keys.txt`. The final absence assertion fails against actual returned native output.

Smallest correction to evaluate: distinguish declared structural keys from dynamic content keys. Apply retained-text and decoded-content inspection to dynamic keys, with a clear collision-safe omission or replacement rule. Preserve fixed operational field names and legitimate counts. Add real run/state cases, including a nested dynamic key and an encoded object key. The reproduction directly writes synthetic historical diagnostic rows; it does not assert that the normal reviewer emits arbitrary item type names.

## Finding 2: Valid current corrected hot entries are masked

Priority: Medium for owner functionality and truthful current-fact display.

`memory_pulse.py:snapshot` first verifies hot contents against active registered records through `_hot_snapshot`. It then sends the entire native result, including those verified current entries, through the historical diagnostic text filter. That filter can match a shorter superseded claim inside a valid longer replacement.

The real fixture probe remembers `RULE: Synthetic PULSE baseline setting`, then corrects it to `RULE: Synthetic PULSE baseline setting now revised`. The correction commits and `get` returns the full replacement. Governed PULSE returns:

```json
{
  "entries": ["Memory diagnostic details are unavailable under the current policy."],
  "count": 1,
  "charsUsed": 50
}
```

The current owner fact is authoritative and allowed, but its body disappears while the native count and character total survive.

Evidence: `raw/probe_current.py` and `raw/current.txt`, including both committed receipts, current `get`, actual snapshot, and the failed equality assertion.

Smallest correction to evaluate: treat verified current hot entries as current records rather than historical diagnostic strings. Bind that exemption to the exact canonical field, entry value, and current registry verification. Revalidate under the same publication/projection lock if the implementation separates those steps. Do not create a general text exemption for matching words in historical state or proposal fields. Add a committed correction test where the replacement contains the old claim and a concurrent correction/forget control if the exemption crosses transactions.

## Independent verification

| Check | Result |
|---|---|
| `test_memory_pulse test_memory_cortex_health test_memory_diagnostics` | 66 passed, 39.288 seconds |
| Corrected current hot entry probe | Confirmed finding 2 |
| Retired dynamic key probe | Confirmed finding 1 |
| Restricted scope with review-state FIFO | Rejected in approximately 8 microseconds, before any blocking body read |
| Native snapshot and runs cardinality | Snapshot 10 runs, runs route 20, from 21 directories |
| Native reviewer fire window | 200 rows considered, five recent rows returned, from 205 input rows |
| Native proposal window | 50 pending rows counted, five recent rows returned, from 55 input rows |
| Nested and JSON-escaped string values | Forgotten marker removed from state, proposal, health, and fire output |
| Rendered run filename | Hyphen-rendered forgotten claim removed |
| Typed clocks, health counts, and derived state | Preserved in the same fixture; critical state and count agree with raw native output |
| Cadence file symlink and reviewer-runs directory symlink | Refused before native snapshot read |
| Native data read-only control | Native data/source file hashes unchanged across raw and governed reads |

The standard tests also verify missing native fields, default cadence/current hot counts, configuration root changes, unsupported views, hot and dispatch redirection, extra cadence configuration exclusion, and native dispatch item/count preservation.

The raw native source reads and governed source reads in the additional controls use the actual `handleRequest` implementation. No tool/native reader/model internals were simulated. The synthetic fixture links only public prepared source code. All user data belongs to a temporary private home.

### Probe corrections retained in evidence

The first controls run expected `PermissionError`, but this service raises `MemoryUnavailable`, a `RuntimeError`. It correctly denied authority. The fixture exception handler was corrected; the first output remains `raw/controls-fixture-error.txt`.

The second controls run asserted byte identity for the registry SQLite database as well as native files. Normal connection/schema bookkeeping changes `MEMORY/STATE/memory-access.sqlite` bytes. The final control records that sole changed path and checks native files separately. The original failed assertion remains `raw/controls-hash-fixture-error.txt`. This establishes read-only native data, not byte-identical SQLite storage. No claim of a separate database mutation defect follows from that observation.

## Commands and raw artifacts

All commands ran from the repository root with:

```sh
export PYTHONPATH=.:tests
export LIFEOS_MEMORY_SOURCE=/home/outsider/.cache/lifeos-plugin-memory/source-gate-20261001-cortex-final/lifeos/LifeOS/install
```

The complete interpreter is shown above. Exact rerun commands are in `raw/commands.txt`; the detached suite command is `raw/run_tests.sh`. Suite output and exit marker are `raw/tests.txt` and `raw/tests.done` (0).

Additional artifacts:

- `raw/current.txt`: full correction receipts, current canonical fact, and defective snapshot.
- `raw/keys.txt`: complete leaking runs/state/snapshot results.
- `raw/controls.txt`: full raw and governed snapshots, cardinality, native hash comparison, and redirect outcomes.
- `raw/probe_current.py`, `raw/probe_keys.py`, `raw/probe_controls.py`: reproducible synthetic fixture operations.
- `raw/snapshot.txt`, `raw/status-after.txt`, `raw/hash-check.txt`: repository state and source stability.

## Limits and next review

Fix both reproduced defects, then rerun their unchanged probes and the focused gate. This review does not prove HTTP caller identity, relay authentication, same-UID process isolation, all PULSE routes, arbitrary oversized source handling, every native writer, or lifecycle/ownership activation. Native whole-file I/O remains outside the bounded performance checks here. The current-source binding and full owner scope apply to this preferences API; they are not evidence that an HTTP caller is authenticated.

No implementation, live configuration, account, dependency, or external system changed during this review. Only this evidence directory and temporary synthetic fixtures were written.
