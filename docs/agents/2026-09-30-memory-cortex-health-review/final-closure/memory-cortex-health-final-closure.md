# Governed Cortex health final closure

Date: 2026-10-01 (America/Toronto)
Role: Independent bounded closure reviewer
Question: Do the metadata-path restrictions and unmanaged exception correction close the remaining measured Cortex health defects without reopening prior publication, filtering, or transport failures?
Model: GPT-6. The exact model variant is not exposed in this agent context.

## Result

**No remaining material defect was found in this bounded final closure.** The saved nested-clock and unmanaged-exception reproductions now have the intended outcomes. The original destination, timestamp-assessment, and volume controls remain corrected.

- **56 tests passed in 38.914 seconds**, with no failures or skips.
- **Five archived programs ran unchanged**, all exit 0 with empty parent-process stderr. Expected native exception output is explicitly captured by the unmanaged comparison.
- An additional real retirement/RPC probe verifies operational clock, status, severity, and dropped-entry reason paths while excluding matching retired text in nested payload fields.
- The unchanged 500-invalid-entry health report completes in **1.698357 seconds** with clean native output.
- The actual HealthGate control completes in **1.530424 seconds** and publishes normally under its five-second child deadline.
- All reviewed source hashes remained unchanged across this final review.

The prior 105-test gate is separate evidence from the preceding closure snapshot. The 53 unchanged neighboring cases were not repeated for this narrow correction. This is not a whole-memory, whole-inventory, lifecycle, or activation approval.

## Scope and exact snapshot

Repository: `/home/outsider/Projects/Hermes_agent/LifeOS_plugin`, branch `feature/lifeos-memory`.

HEAD: `8970c41d321f7c7b57a5b702d521853994d95db2`, plus the final Cortex working diff.

Fresh public prepared source:

`/home/outsider/.cache/lifeos-plugin-memory/source-gate-20261001-cortex-final/lifeos/LifeOS/install`

Interpreter:

`/home/outsider/.cache/lifeos-plugin-memory/memory-plugin-test-env/bin/python`

Review scope is the structural metadata-path projector in `memory_diagnostics.py`, native unmanaged exception handling in `MemoryHealthCheck.ts`, their tests, and the unchanged neighboring diagnostic boundary needed to verify their behavior. Both LifeOS patch copies match and are 58,956 bytes. There are no Hermes changes in this unit.

Exact copies are in `raw/sources/`. Full maps and comparison are `raw/hashes-before.json`, `raw/hashes-after.json`, and `raw/hash-comparison.json`; the comparison reports no changes.

| File | SHA-256 |
| --- | --- |
| memory_diagnostics.py | `269b3d52bcbf411af6016a65c95152b8bd78e50f1c338b37c35d8b0356918a94` |
| memory_sources.py | `dc72afff2ea31dcd3552f62674109981a66298c39a29624999e6d5e17a08d87b` |
| memory_service.py | `c5f57fafa719e8761cfcf5e5cafa78cbf00b3ef55cb6e45112f9764bd3f418a0` |
| memory_rpc.py | `91960f96929697a9c3e0e2e155456ed7d121fa162ed379049639d55cf2068587` |
| test_memory_cortex_health.py | `c1d64ce9125d7b0377c87206701501524fcd34e8ea018b7cc268b05a70d9bf5d` |
| Both LifeOS memory patch copies | `4eff592aa53a6bcb7a528060f05b6dd3a776240bb626a488a8020f16b773bbfe` |
| Native CortexHealth.ts | `8e1dce8f06dbd4beee91739d52ea8163f2a9d4fc1dba88409a4a008f10ff58f9` |
| Native MemoryHealthCheck.ts | `d6b248278701510055fb3e157ff6b903ec0696557ba4a61138e364850764e6b3` |
| Native lib/MemoryAccess.ts | `8fd736748d13d76c16e75e4311bd8ad2f4f6d2dfde1a915282c483c6c9a9adf1` |

## Commands and raw results

Run from the repository:

```sh
PYTHONPATH=.:tests \
LIFEOS_MEMORY_SOURCE=/home/outsider/.cache/lifeos-plugin-memory/source-gate-20261001-cortex-final/lifeos/LifeOS/install \
/home/outsider/.cache/lifeos-plugin-memory/memory-plugin-test-env/bin/python \
-m unittest test_memory_cortex_health test_memory_diagnostics -v
```

Result: **56 passed in 38.914 seconds**, exit 0. This comprises 35 Cortex/health cases and 21 diagnostic cases. The exact detached runner, output, and completion marker are `raw/run_tests.sh`, `raw/runner.txt`, `raw/tests.txt`, and `raw/tests.done`.

Archived programs:

```sh
/home/outsider/.cache/lifeos-plugin-memory/memory-plugin-test-env/bin/python \
docs/agents/2026-09-30-memory-cortex-health-review/final-closure/raw/run_archived.py
```

The runner executes these original files without modifying them:

1. `closure/raw/probe_clock_shapes.py`
2. `closure/raw/probe_unmanaged_clock.py`
3. `raw/probe_health_edges.py`
4. `raw/probe_controls.py`
5. `closure/raw/probe_request_bounds.py`

Those paths are relative to the parent `memory-cortex-health-review` directory. Exact argv, script hashes, return codes, and stderr are recorded in `raw/archived-results.json`. Captured outputs in this final directory use the original script stem plus `.txt`.

Additional probe:

```sh
PYTHONPATH=.:tests \
LIFEOS_MEMORY_SOURCE=/home/outsider/.cache/lifeos-plugin-memory/source-gate-20261001-cortex-final/lifeos/LifeOS/install \
/home/outsider/.cache/lifeos-plugin-memory/memory-plugin-test-env/bin/python \
docs/agents/2026-09-30-memory-cortex-health-review/final-closure/raw/probe_metadata_paths.py
```

Result: exit 0. The complete input and projected response are in `raw/metadata-paths.txt`. `raw/commands.txt` records execution details.

Prior independent evidence remains in the sibling `closure/` report: **105 passed in 89.910 seconds**. That run included the 53 neighbors before this final change. It is not presented as a rerun of the final snapshot.

## Metadata-path correction

The recursive projector now carries tuple paths, including array indices. Clock and enum exemptions require declared structural locations rather than merely matching the final key name.

Valid operational clocks remain permitted at the root and declared Cortex reviewer/retrieval/index, final report evidence, and finding-detail locations. Status values are limited to those evidence locations. Severity is preserved at the report's overall field and finding severity fields. Dropped-entry reason enums are preserved only at the diagnostic dropped-invalid rows and the final finding's dropped-entry rows.

The saved actual native clock probe now excludes the retired timestamp in all three error forms:

| Error representation | Final result |
| --- | --- |
| Plain string | unavailable details |
| JSON-encoded object string | unavailable details |
| Structured object with `ts` and `message` | both values excluded |

The direct shaped-payload control likewise excludes retired values under `error.ts`, `content.ts`, and `samples[].timestamp`. The legitimate root operational timestamp remains available. Thus the metadata exception no longer extends into these arbitrary payloads.

### Independent status and reason controls

The additional probe performs real remember/forget operations for an ISO timestamp and the words `critical`, `failed`, and `overlength`. It then uses the governed RPC with native report-shaped data.

Observed preservation:

- Root overall severity and timestamp survive as operational fields.
- Reviewer and final evidence reviewer status/timestamp survive.
- Finding severity and declared evidence-detail status/timestamp survive.
- `dropped_invalid[].reason` and `findings[].detail.dropped[].reason` retain `overlength`.

Observed filtering:

- Matching values in nested reviewer errors are excluded.
- Matching values in finding messages and dropped-entry bodies are excluded.
- Matching clock/status/severity/reason keys inside arbitrary sample objects are excluded.

These controls verify the newly restricted exception paths independently of the new regression test. The focused suite also exercises actual native structured error collection and publication, verifying the retired timestamp stays absent from the final health log.

This remains an explicit operational-metadata policy exception. It does not remove permitted numeric activity or typed health values merely because their text matches a retired fact. New native report layouts would need corresponding schema review before inheriting an exception.

## Unmanaged exception correction

`requireDiagnostics` now calls the original collector directly when no governed connector is present. Managed calls retain the clean unavailable handler.

The unchanged comparison program runs the earlier owned prepared source and the final source against the same private fixture with an invalid clock override:

| Mode | Exit | Stdout | Stderr |
| --- | ---: | --- | --- |
| Initial native unmanaged control | 1 | empty | native RangeError |
| Final native unmanaged control | 1 | empty | native RangeError |
| Final managed control | 2 | clean unavailable JSON | empty |

No case publishes a health row. This closes the measured standalone regression while preserving managed refusal. The report does not claim parity for every possible standalone exception.

## Earlier boundary corrections remain verified

The unchanged original probes and the focused gate retain the following outcomes:

- A configuration-file report override is refused and leaves the sentinel unchanged.
- Approved reports are confined to the dedicated diagnostic report namespace and match stdout/log output.
- Diagnostic-input and symlink destinations are refused before publication.
- Operational timestamp preservation avoids the original false critical assessment.
- The 500-invalid-entry report preserves native warning/count behavior and completes cleanly in 1.698357 seconds.
- An oversized 8,000-entry report returns structured unavailability without a health log or optional report file.
- Exact request limits still accept 131,072 ordinary-operation bytes and 3,145,728 diagnostic-operation bytes, then refuse one byte more. Multibyte input is bounded by bytes.
- Unknown author, changed route, restricted grant, and broken connector controls do not publish.
- Diagnostic-only hot inspection does not return valid facts, and ordinary hot reads still require repair.

The actual HealthGate control completes in 1.530424 seconds, publishes its health row, and emits the expected critical summary under the native five-second subprocess deadline. This is evidence for the exercised synthetic workloads, not an arbitrary-input performance guarantee.

## Disposition and limits

All five measured findings across the initial Cortex review and its first closure are closed for their saved reproductions. The related enum path correction also passes its regression and the independent metadata-path probe. No additional material defect was found in this narrow final review.

The metadata paths are specific to the reviewed native report schema. This review does not treat arbitrary caller-supplied report schemas as trusted operational metadata. The existing same-UID process boundary and unbounded whole-file I/O remain declared limits.

PULSE HTTP authentication, corpus readers, restore and other writers, whole native inventory coverage, lifecycle behavior, restricted prompting, and ownership activation remain open and outside this closure. No full plugin regression was repeated here.

Only evidence artifacts and disposable synthetic data were written by this reviewer. No implementation edits, commits, dependencies, live imports/bootstrap, SSH, accounts, or memory/journal calls occurred. There is no installed deployment or configuration change to undo.

For Adrian's review, the important distinction is now enforced at the tested structural locations: native operational metadata keeps its health meaning, while error/content/sample data remains subject to retained-text filtering.
