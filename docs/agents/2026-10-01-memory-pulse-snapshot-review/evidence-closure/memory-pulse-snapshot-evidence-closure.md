# PULSE snapshot evidence-path closure

Date: 2026-10-01

Role: Independent code and behavior reviewer, Cerebo

Question: Does the exact evidence-path correction close the reproduced double-prefix defect while preserving the previously verified snapshot behavior and focused regression gate?

Model: GPT-6. The exact model variant is not exposed in this agent context.

## Outcome

**The reproduced double-prefix defect is closed. No remaining material finding was identified within this bounded re-review.** The independent focused gate passes all **72 tests in 45.155 seconds**, and all seven archived probes pass.

The original namespace probe now reports all three expected outcomes: the declared health reviewer status survives, the double-prefix content key is removed, and the ordinary error-content key is removed. All earlier correction, dynamic-key, state/proposal schema, authority, cardinality, old-report, and cooperating-writer probes pass unchanged.

This is bounded closure of the governed snapshot projection and its reproduced defects. HTTP identity, authenticated relay, ownership activation, and broader native inventory remain outside this review.

## Reviewed source

Repository: `/home/outsider/Projects/Hermes_agent/LifeOS_plugin`

Branch: `feature/lifeos-memory`

HEAD: `c2198bd3b295a3676dcde8d9f5d0db0b7e242eca`, with the reviewed working changes.

Interpreter: `/home/outsider/.cache/lifeos-plugin-memory/memory-plugin-test-env/bin/python`

Native source: `/home/outsider/.cache/lifeos-plugin-memory/source-gate-20261001-cortex-final/lifeos/LifeOS/install`

| File | SHA-256 |
|---|---|
| `memory_pulse.py` | `634953117fd3b30acd27fb3b486b34101408c38d48cc9dbb797a0902c457c7ae` |
| `memory_preferences.py` | `d451a4d7cb3ea50be04fc169a386d3fd900f4f16c68f38d6a445e15820926eb5` |
| `memory_native.ts` | `f3e561beaf5f00becc596eac2062345e9eee11a14bb9aadc4ae80733b4ab79f3` |
| `memory_diagnostics.py` | `e981bb0c80a7921538cb3438ec240eb9e6266a27a1c3fb80c58e6a219ced7057` |
| `test_memory_pulse.py` | `db1879faf1ec42d4daa35d3f7f10b210fab34e6a155d25d7afabd94b8e58f9f9` |
| Native `LIFEOS/PULSE/modules/memory.ts` | `daf44ab1f0a0333feab01fc2a268d2f2eb5af7523c5974fb37512cf409441449` |

All six reviewed hashes remained identical before and after the gate and probes. Exact absolute paths and stability evidence are recorded in `raw/hashes-before.json`, `raw/hashes-after.json`, and `raw/hash-check.txt`.

Exact source copies are in `raw/sources/`; `raw/correction.diff` shows the bounded production correction relative to the prior review. The native module, preferences binding, native worker action, and current-hot transaction code are unchanged from the preceding reviewed snapshot.

## Correction review

The change captures `_evidence_field(path)` before stripping an optional `evidence` prefix for the other declared health sections. The reviewer/retrieval/index field exemption therefore uses the original health-relative path.

The actual native health and snapshot regression performs a governed remember and forget of `RULE: status`. It then exercises three paths in synthetic native health JSON:

| Path | Expected and observed |
|---|---|
| `evidence.reviewer.status` | Declared operational field preserved |
| `evidence.evidence.reviewer.status` | Arbitrary nested field removed |
| `error.reviewer.status` | Arbitrary nested field removed |

The unchanged archived namespace probe confirms the same results through both governed views. Its final line is:

```json
{"fixed_health_status_preserved": true, "nested_content_status_removed": true, "error_content_status_removed": true}
```

No new inventory exploration was performed. The narrow production diff and the test outcomes support closure of this concrete defect.

## Preserved behavior

All seven archived probes run against the current code without modifying their scripts:

1. `probe_current.py`: the authoritative corrected hot entry remains visible.
2. `probe_keys.py`: the original retired dynamic key is removed from native state and runs.
3. `probe_controls.py`: authority rejects before a synthetic FIFO read; path redirects fail; native windows/counts remain; nested and encoded retired values are removed; native data files remain unchanged.
4. `probe_structural.py`: fixed proposal status remains and arbitrary state reviewer status is removed. Both reported booleans are true.
5. `probe_lock.py`: a real cooperating forget waits through snapshot projection; the following snapshot observes zero hot entries.
6. `probe_namespace.py`: exact single-prefix metadata survives and double-prefix content is removed. All reported booleans are true.
7. `probe_old_fields.py`: old free-text values are filtered without deleting unrelated keys; exact retired dynamic keys are removed; typed metadata remains.

The probes use real native tools and private synthetic fixtures. The concurrency probe uses an observational trace to coordinate actual operations, without replacing their implementations. The native read-only control distinguishes unchanged native files from normal registry SQLite byte changes.

## Commands and raw evidence

All commands ran from the repository root with:

```sh
export PYTHONPATH=.:tests
export LIFEOS_MEMORY_SOURCE=/home/outsider/.cache/lifeos-plugin-memory/source-gate-20261001-cortex-final/lifeos/LifeOS/install
```

`python` below refers to the complete interpreter listed above.

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

`raw/run_tests.sh` records the exact interpreter and detached gate command. Full output is in `raw/tests.txt`, with its exit marker in `raw/tests.done`. `raw/probe-results.json` records exact archived-probe commands and zero exit codes. The corresponding complete outputs are saved in `raw/current.txt`, `keys.txt`, `controls.txt`, `structural.txt`, `lock.txt`, `namespace.txt`, and `old_fields.txt`.

The structural and namespace scripts report explicit booleans rather than raising for each mismatch. Those booleans were checked directly; successful exit status alone was not treated as sufficient evidence.

## Limits and review handoff

The tests support governed owner snapshot behavior and the named neighboring diagnostic contracts. They do not establish HTTP authentication, delivery identity, full lifecycle, all native writers/readers, same-UID hostile-process isolation, or arbitrary-volume behavior. Ownership activation remains outside scope.

No implementation, live configuration, account, dependency, or external system changed during this review. Only this evidence directory and temporary synthetic fixtures were written. Prior reports and failure evidence remain intact.
