# Governed Cortex health closure review

Date: 2026-10-01 (America/Toronto)
Role: Independent bounded closure reviewer
Question: Do the report-path, operational-clock, and bounded-RPC corrections close the initial Cortex health findings while preserving managed and standalone native behavior?
Model: GPT-6. The exact model variant is not exposed in this agent context.

## Result

**The three original reproductions now produce the corrected outcomes. Two followup defects remain.**

1. The clock exemption is based on field name at every object depth. A retired ISO value in structured error data, such as `reviewer.error.ts`, escapes filtering.
2. The new clean-unavailable wrapper also changes unmanaged exceptional behavior. An invalid native clock override now returns a policy-unavailable JSON result instead of the original standalone exception behavior.

The independent focused gate passes: **105 tests in 89.910 seconds**, no failures or skips. Both unchanged archived probe programs exit 0 with empty parent-process stderr. The actual HealthGate control completes in **1.568672 seconds** and publishes normally. Exact request-byte controls also pass.

No implementation or installed runtime was changed by this reviewer. The parent received the followup reproductions and the stable hash capture before beginning corrections. This report applies to that captured snapshot, not to later fixes.

## Scope and snapshot

Repository: `/home/outsider/Projects/Hermes_agent/LifeOS_plugin`, branch `feature/lifeos-memory`.

HEAD: `8970c41d321f7c7b57a5b702d521853994d95db2`, plus the corrected Cortex working diff.

Fresh distributed native source:

`/home/outsider/.cache/lifeos-plugin-memory/source-gate-20260930-cortex-closure/lifeos/LifeOS/install`

Interpreter:

`/home/outsider/.cache/lifeos-plugin-memory/memory-plugin-test-env/bin/python`

Review scope is the three initial corrections, their diagnostic source/service/RPC support, and the associated native health functions. The unmanaged exception control additionally executes the earlier owned public `source-gate-20260930-cortex-health` HealthCheck against the same private fixture HOME. It never reads an installed live home or runtime.

Exact snapshots are under `raw/sources/`. Before/after maps and comparison are `raw/hashes-before.json`, `raw/hashes-after.json`, and `raw/hash-comparison.json`. All reviewed hashes matched through the completed gate and probes. Both regenerated 17-file patch copies are identical.

| File | SHA-256 |
| --- | --- |
| memory_diagnostics.py | `4466476600b28b1a2ca388fb4db3dc87caf440bf6b563b9b77edac91ae9f9917` |
| memory_sources.py | `dc72afff2ea31dcd3552f62674109981a66298c39a29624999e6d5e17a08d87b` |
| memory_service.py | `c5f57fafa719e8761cfcf5e5cafa78cbf00b3ef55cb6e45112f9764bd3f418a0` |
| memory_rpc.py | `91960f96929697a9c3e0e2e155456ed7d121fa162ed379049639d55cf2068587` |
| test_memory_cortex_health.py | `d02f3b383abf96a0bf06b100f3e7e411e6b7ac3e51824899fd5c590dc0465376` |
| Both LifeOS memory patches | `ea3b6f424180c5cd0164536e466a295a650175be28b26a77391b1b4e8fb86dee` |
| Native CortexHealth.ts | `8e1dce8f06dbd4beee91739d52ea8163f2a9d4fc1dba88409a4a008f10ff58f9` |
| Native MemoryHealthCheck.ts | `0c30fa4d5d525fa16b8d9d62b4d51277352cdcc00d0cdbfd721f6d36bda19f58` |
| Native lib/MemoryAccess.ts | `8fd736748d13d76c16e75e4311bd8ad2f4f6d2dfde1a915282c483c6c9a9adf1` |

## Commands and results

Focused gate, from the repository:

```sh
PYTHONPATH=.:tests \
LIFEOS_MEMORY_SOURCE=/home/outsider/.cache/lifeos-plugin-memory/source-gate-20260930-cortex-closure/lifeos/LifeOS/install \
/home/outsider/.cache/lifeos-plugin-memory/memory-plugin-test-env/bin/python \
-m unittest test_memory_cortex_health test_memory_diagnostics test_memory_delta.MemoryDeltaTests test_memory_sources test_memory_delegation test_memory_proposal_delegation -v
```

Result: **105 passed in 89.910 seconds**, exit 0. This comprises 31 Cortex/health cases, 21 diagnostics, and 53 neighboring cases. The detached runner, complete stdout/stderr, and exit marker are `raw/run_tests.sh`, `raw/runner.txt`, `raw/tests.txt`, and `raw/tests.done`.

Archived programs ran unchanged through:

```sh
/home/outsider/.cache/lifeos-plugin-memory/memory-plugin-test-env/bin/python \
docs/agents/2026-09-30-memory-cortex-health-review/closure/raw/run_archived.py
```

`raw/archived-results.json` records exact argv, script SHA-256, return code, and stderr. Results are `raw/archived-health_edges.txt` and `raw/archived-controls.txt`. Original scripts and earlier failures remain untouched in the parent review directory.

Additional programs use the same interpreter and environment:

- `raw/probe_clock_shapes.py`, output `raw/clock-shapes.txt`.
- `raw/probe_unmanaged_clock.py`, output `raw/unmanaged-clock.txt`.
- `raw/probe_request_bounds.py`, output `raw/request-bounds.txt`.

All three programs exit 0. Their child failures or unavailable outcomes are deliberately captured, not ignored. Exact invocation details are also in `raw/commands.txt`.

## Initial finding closure

### Managed output destination: original defect closed

The optional output uses a distinct `check_diagnostic_report` RPC. Its permitted namespace is the installed `LIFEOS/MEMORY/OBSERVABILITY/reports/` directory with an ASCII basename ending in `.json`. The service checks both the supported logical name and expected physical private-data path. Preflight occurs before health-log or optional-report publication.

The unchanged configuration-override reproduction now leaves the sentinel unchanged and returns clean unavailable JSON with exit 2. The focused tests additionally prove:

- An approved report destination matches stdout and the health log.
- A report-file symlink cannot overwrite a configuration target.
- An optional report cannot replace an existing diagnostic input.
- Refused destinations cause no new health-log publication.
- Unmanaged callers retain the native optional destination behavior.

This closes the measured alternate-output defect. It does not establish protection against hostile same-UID changes between filesystem checks and publication.

### Operational timestamp assessment: original reproducer closed, exception too broad

The implementation now treats validated ISO values in selected clock fields as operational metadata, alongside counts and status. This is an explicit policy exception, not removal of the retired clock value. The original retired-timestamp control now retains its valid reviewer timestamp and produces the same warn assessment as unmanaged native collection.

Keeping a typed operational timestamp can preserve native validity/freshness decisions. The new exception must remain confined to those actual operational locations. Finding 4 below shows that the current field-name-only test also exempts structured error payloads.

Ordinary free-text timestamp strings remain filtered in the focused cases. The source validates date/time syntax and timezone rather than allowing arbitrary strings merely because a key is named `ts`.

### Large invalid-entry transport: original defect closed

The unchanged 500-entry corrupt-hot-file probe now completes with valid report JSON, exit 2, and empty native stderr in **1.706831 seconds**. Native warning/severity behavior and all 500 dropped-entry diagnostics remain available. The previous parser truncation and empty-stdout stack trace are absent.

Only `filter_diagnostic` receives the larger request allowance. The generic RPC reader counts bytes; the other operations retain their smaller allowance. The final filtered response also receives an exact serialized-envelope budget check.

Independent boundary measurements:

| Operation/input | Bytes | Result |
| --- | ---: | --- |
| check_sources | 131,072 | accepted |
| check_sources | 131,073 | structured input-limit refusal |
| filter_diagnostic | 3,145,728 | accepted |
| filter_diagnostic | 3,145,729 | structured input-limit refusal |
| filter_source with multibyte text | 140,109 bytes, 70,109 characters | structured input-limit refusal |

The focused suite also rejects oversized serialized responses and an actual 8,000-invalid-entry report. The latter returns clean unavailable JSON with exit 2 and writes neither the optional report nor the health log. This is deliberate bounded refusal; the implementation does not promise delivery of arbitrary-size diagnostic details.

## Finding 4: nested error clocks inherit the metadata exception

**Severity: medium. Confirmed retained-text filtering bypass for structured diagnostic payloads.**

Location: `memory_diagnostics.filter_report`, recursive `project(value, key)` and `_clock(key, value)`.

The projector tracks only the immediate key. It does not distinguish a native reviewer clock from a field with the same name inside arbitrary error/content/sample data.

`probe_clock_shapes.py` performs a real remember and forget for a synthetic ISO timestamp, then creates three native reviewer error forms. The actual collector returns:

| Error representation | Result |
| --- | --- |
| Plain retired ISO string | excluded |
| JSON-encoded string containing `ts` and the retired ISO | excluded |
| Object containing `ts: retiredISO` and `message: retiredISO` | `message` excluded; `ts` remains visible |

The exact surviving location is `evidence.reviewer.error.ts`. The source row's ordinary current reviewer timestamp is separate from that retired value. Native collection reads the source and returns the structured error object; this is not merely a direct unit call to the filter.

The direct governed RPC control additionally confirms the same exception under `content.ts` and `samples[].timestamp`. These are text-bearing payload locations, not the native operational clocks needed by assessment.

This is a malformed/structured source edge. The review does not claim that the normal current reviewer writer emits object-valued errors. However, the collector accepts and returns them, and the new generic clock exception exposes text that the plain and encoded forms correctly exclude.

### Smallest correction and regression

Track the structural path and exempt only actual native clock locations. Known root clocks and the exact reviewer/retrieval evidence paths can preserve their operational values. Arbitrary nested error, content, and sample payloads must continue through retained-text filtering. Alternatively normalize a non-string native error into a filtered textual representation before it enters the health evidence object, while preserving critical classification.

Retain the three-form real collector probe. Add equivalent final-report paths and controls for current permitted operational timestamps. The status/severity/reason exemptions use a similar immediate-key pattern; their analogous nested-payload risk is source-traced here, not independently reproduced as another finding. The parent has identified it for the same correction.

## Finding 5: clean-unavailable handling changes unmanaged exceptions

**Severity: low. Confirmed standalone compatibility regression.**

Location: native `MemoryHealthCheck.requireDiagnostics`.

The helper catches collection/filter errors whether or not a governed connector exists. The requested managed clean-failure behavior therefore changes the pre-existing unmanaged path.

The parent identified this candidate; `probe_unmanaged_clock.py` independently compares the earlier prepared public source and current source against the same private fixture with an invalid `CORTEX_HEALTH_NOW`:

| Source/mode | Exit | Stdout | Stderr |
| --- | ---: | --- | --- |
| Initial prepared source, unmanaged | 1 | empty | native RangeError stack |
| Current source, unmanaged | 2 | policy-unavailable JSON | empty |
| Current source, managed | 2 | policy-unavailable JSON | empty |

No case publishes a health row. The managed result is the desired clean refusal. The unmanaged result now misleadingly attributes an invalid clock configuration to memory policy and changes the standalone exit/output contract.

### Smallest correction and regression

Use the wrapper only for managed operations. Let an unmanaged collector/filter retain its native exceptional behavior, or explicitly authorize and document a broader standalone behavior change. The narrow unit requested unchanged unmanaged semantics.

Keep this actual source comparison, normal unmanaged optional-output controls, and managed clean-unavailable controls. No broader exception refactor is required to close the measured regression.

## Other preservation evidence

The unchanged controls continue to refuse unknown author, changed route, restricted grants, and a dangling connector without publication. Diagnostic-only hot inspection returns the invalid record while keeping the valid fact out of that response; ordinary hot reads still require repair.

Ordinary owner and unmanaged reports retain matching finding IDs, severities, and counts. The actual `MemoryHealthGate.hook.ts` control completes in **1.568672 seconds**, exits 0, produces empty stdout, writes its health row, and emits the expected two-blocker critical summary on stderr. The hook itself applies its native five-second subprocess timeout.

These are actual native subprocess and service operations over synthetic data. No model or native publication internals were mocked.

## Disposition and limits

The original destination and volume failures are closed. The operational-clock reproducer is corrected under an explicit metadata exception, but that exception needs the structural restriction in Finding 4. The unmanaged wrapper also needs the narrow compatibility correction in Finding 5. The passing 105-test gate does not cover those new failures.

The report and hashes were completed before the parent began further changes. No additional optional probes were run after confirming the remaining findings. This report makes no claim about the subsequent corrections.

Whole-file I/O remains unbounded. PULSE HTTP authentication, corpus readers, restore/other writers, lifecycle coverage, restricted prompting, the whole native source inventory, and ownership activation remain outside scope. A same-UID hostile process is not treated as contained by an OS sandbox.

Only evidence files and disposable synthetic fixtures were changed by this reviewer. No implementation edits, commits, dependencies, live imports/bootstrap, SSH, accounts, or memory/journal operations occurred. There is no installed deployment to undo.

For Adrian's review, the consequential policy choice is the operational metadata exception. It preserves health meaning only if it is restricted to actual native metadata, rather than arbitrary payload keys that happen to share the same name.
