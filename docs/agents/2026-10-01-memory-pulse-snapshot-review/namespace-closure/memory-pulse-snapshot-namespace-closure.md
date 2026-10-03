# PULSE snapshot namespace closure review

Date: 2026-10-01

Role: Independent code and behavior reviewer, Cerebo

Question: Do the corrected state, proposal, and health schemas preserve native fields while filtering retired dynamic keys, without authority or concurrency regressions?

Model: GPT-6. The exact model variant is not exposed in this agent context.

## Outcome

**All prior reproductions and the 71-test gate pass. One narrow structural-key exemption remains overbroad.** A health object with two nested `evidence` prefixes inherits the reviewer metadata exemption intended for a single prefix. The retired word `status` therefore survives as an arbitrary nested field name in governed health and snapshot output.

The result is bounded to this synthetic namespace case. It is not evidence that the normal native health collector emits that shape. The PULSE reader accepts raw historical health JSON, so the new projection must distinguish this content from declared operational metadata.

The primary agent received the finding and confirmation that source capture was complete. This report covers the frozen hashes below. Subsequent corrections are not included.

## Snapshot and environment

Repository: `/home/outsider/Projects/Hermes_agent/LifeOS_plugin`

HEAD: `c2198bd3b295a3676dcde8d9f5d0db0b7e242eca`, branch `feature/lifeos-memory`, plus reviewed working changes.

Interpreter: `/home/outsider/.cache/lifeos-plugin-memory/memory-plugin-test-env/bin/python`

Public prepared native source: `/home/outsider/.cache/lifeos-plugin-memory/source-gate-20261001-cortex-final/lifeos/LifeOS/install`

| File | SHA-256 |
|---|---|
| `memory_pulse.py` | `634953117fd3b30acd27fb3b486b34101408c38d48cc9dbb797a0902c457c7ae` |
| `memory_preferences.py` | `d451a4d7cb3ea50be04fc169a386d3fd900f4f16c68f38d6a445e15820926eb5` |
| `memory_native.ts` | `f3e561beaf5f00becc596eac2062345e9eee11a14bb9aadc4ae80733b4ab79f3` |
| `memory_diagnostics.py` | `b6742cc7fe329466cb7c9f6c1fa01410f8b6de823fcc48dde9606537da0574f2` |
| `test_memory_pulse.py` | `164c51067ea0c0cd8f7aa145540e217b0476315ef25d6986ab1080efd2bdcb1b` |
| Native `LIFEOS/PULSE/modules/memory.ts` | `daf44ab1f0a0333feab01fc2a268d2f2eb5af7523c5974fb37512cf409441449` |

All six hashes match before and after testing. `raw/sources/` holds copies. `raw/hashes-before.json`, `raw/hashes-after.json`, and `raw/hash-check.txt` preserve exact absolute paths and stability evidence.

## Remaining finding: double evidence prefix inherits a fixed-field exemption

Priority: Medium for the declared exact retained-key boundary. The exposure is a field name, not an arbitrary string value or current fact body.

The real probe remembers and forgets `RULE: status`, then writes this synthetic native health row:

```json
{
  "overall": "ok",
  "counts": {"ok": 1},
  "evidence": {
    "reviewer": {"status": "ok"},
    "evidence": {"reviewer": {"status": 1}}
  },
  "error": {"reviewer": {"status": 1}}
}
```

The governed result preserves the legitimate `evidence.reviewer.status` field. It correctly removes `error.reviewer.status`. However, it also preserves `evidence.evidence.reviewer.status` in both `health` and `snapshot` views.

`_structural_field` strips one leading `evidence` component before calling `_evidence_field`. That helper already recognizes paths beginning with `evidence`. The combination admits two prefixes where only one is declared.

Evidence: `raw/probe_namespace.py` and `raw/namespace.txt`. The reported outcomes are:

```json
{
  "fixed_health_status_preserved": true,
  "nested_content_status_removed": false,
  "error_content_status_removed": true
}
```

Smallest correction: test exact reviewer/retrieval/index metadata paths before any normalization for other schema sections. Preserve the declared single-prefix locations; do not allow normalization to make an arbitrary nested path equivalent to a declared location. Add the actual health and snapshot case to the regression gate.

## Independent results

| Verification | Result |
|---|---|
| Requested focused suite | 71 passed, 44.047 seconds |
| Original current correction probe | Pass, unchanged script |
| Original retired dynamic key probe | Pass, unchanged script |
| Original authority/path/cardinality/value controls | Pass, unchanged script |
| Prior state/proposal structural probe | Both expected correction booleans true |
| Prior cooperating-lock probe | Pass, writer waits through projection and next snapshot sees forget |
| Old report field-name and value control | Pass |
| New double-evidence namespace control | Confirmed remaining finding |

The two health tests that errored in the prior review now pass. Fixed root clocks and required evidence fields survive. The state schema stops at its root, and the real pending proposal retains its native status field.

The old-report control uses a source timestamp from 2000 and a later real forget. Its unrelated `error` field name remains present while its old free-text value becomes unavailable. A dynamic key containing the exact retired claim is removed, an unrelated nested numeric field remains, and legitimate reviewer status and ISO clocks survive. This supports the intended separation between source-age filtering of values and current retained-claim filtering of field names.

The concurrency probe remains unchanged from the prior closure. An observational trace pauses at the real filter call, a second thread executes governed forget, and the native transaction prevents publication until the snapshot completes. The following snapshot has zero hot entries. No additional cache or authority bypass was found in these bounded checks.

## Commands and evidence

Every run uses:

```sh
export PYTHONPATH=.:tests
export LIFEOS_MEMORY_SOURCE=/home/outsider/.cache/lifeos-plugin-memory/source-gate-20261001-cortex-final/lifeos/LifeOS/install
```

`python` in the following list refers to the complete interpreter named above:

```sh
python -m unittest test_memory_pulse test_memory_cortex_health test_memory_diagnostics -v
python docs/agents/2026-10-01-memory-pulse-snapshot-review/raw/probe_current.py
python docs/agents/2026-10-01-memory-pulse-snapshot-review/raw/probe_keys.py
python docs/agents/2026-10-01-memory-pulse-snapshot-review/raw/probe_controls.py
python docs/agents/2026-10-01-memory-pulse-snapshot-review/final-closure/raw/probe_structural.py
python docs/agents/2026-10-01-memory-pulse-snapshot-review/final-closure/raw/probe_lock.py
python docs/agents/2026-10-01-memory-pulse-snapshot-review/namespace-closure/raw/probe_namespace.py
python docs/agents/2026-10-01-memory-pulse-snapshot-review/namespace-closure/raw/probe_old_fields.py
```

`raw/run_tests.sh` contains the exact detached command. `raw/tests.txt` holds all 71 outcomes, and `raw/tests.done` is 0. `raw/probe-results.json` records the exact archived-probe commands and zero return codes. The structural probe's booleans were checked directly because its original script reports failures without raising an assertion. Raw outputs are `current.txt`, `keys.txt`, `controls.txt`, `structural.txt`, `lock.txt`, `namespace.txt`, and `old-fields.txt`.

Previous reports, scripts, and results remain unchanged. No implementation was edited during this review.

## Limits

This is not final closure of the snapshot unit while the remaining namespace defect is open. Re-run the narrow new reproduction and regression gate after correction.

HTTP caller identity, authenticated relay, ownership activation, lifecycle, all native source/writer paths, hostile same-UID processes, and arbitrary-volume behavior remain outside this review. No live imports/bootstrap, SSH, accounts, dependencies, memory tools, or journal tools were used. Only review evidence and temporary synthetic fixtures were written.
