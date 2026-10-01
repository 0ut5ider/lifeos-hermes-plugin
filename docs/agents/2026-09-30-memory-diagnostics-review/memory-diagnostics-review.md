# Governed native diagnostic readback review

Date: 2026-09-30 (America/Toronto; raw native timestamps use October 1 UTC)
Role: Independent bounded implementation reviewer
Question: Do governed MemoryStatus and MemoryInsights preserve native operational statistics and authorized samples while excluding unavailable callers and retained claims?
Model: GPT-6. The exact model variant is not exposed in this agent context.

## Result

**Three concrete defects remain in the reviewed snapshot.** All are availability or output-preservation failures. No unauthorized text disclosure was observed in the tested paths.

1. A valid native proposal with a 40,043-character edit loses its authorized diagnostic sample and identifier because diagnostic validation duplicates its contents into an oversized idea payload.
2. The 3 MiB guard measures inner content, allowing a successful service response whose serialized RPC envelope exceeds the native 4 MiB buffer.
3. A large numeric JSON value raises an uncaught `OverflowError`, making the diagnostic unavailable instead of dropping the invalid field.

The independent focused gate passes: **69 tests in 56.283 seconds**, no failures or skips. Additional real fixture controls preserve exact managed/unmanaged owner statistics, refuse changed routes and dangling connectors, exclude a Unicode-escaped superseded claim, and reject a genuinely over-limit projection.

The parent was notified with reproduction paths and plans separate corrections. This report records the initial stable snapshot and does not review or approve those subsequent changes. Ownership activation remains outside scope.

## Scope and exact snapshot

Repository: `/home/outsider/Projects/Hermes_agent/LifeOS_plugin`.

Branch: `feature/lifeos-memory`.

HEAD: `3c825af22fc3650b24f181ba2a9458f74e2578cd`, plus the working diagnostic changes.

Fresh public prepared native source:

`/home/outsider/.cache/lifeos-plugin-memory/source-gate-20260930-diagnostics/lifeos/LifeOS/install`

Interpreter:

`/home/outsider/.cache/lifeos-plugin-memory/memory-plugin-test-env/bin/python`

The reviewed implementation comprises `memory_diagnostics.py`, the diagnostic path extension in `memory_sources.py`, the `read_diagnostic` service dispatch, native `MemoryStatus.ts`, `MemoryInsights.ts`, and `readMemoryDiagnostic` in `lib/MemoryAccess.ts`. I also read the existing native sanitizer, transaction/native worker, retained-claim filter, policy source guard, and test fixture setup to establish the relevant behavior.

Exact source copies are under `raw/sources/`. Complete SHA-256 maps are in `raw/hashes-before.json` and `raw/hashes-after.json`; `raw/hash-comparison.json` records no differences across all tests and probes. Both distributed patch copies are identical.

| Reviewed file | SHA-256 |
| --- | --- |
| memory_diagnostics.py | `de6f0fd25050c8eb87df1ee5ec24fe46a84a0725fd031d61f26366e9da2bd686` |
| memory_sources.py | `a32cbc99a917f4a327cbb95ff2d79269db9d4bfb37ebfba585704c99315e2e00` |
| memory_service.py | `cab84e3be8611218b57d4c366824b87d35b57936e2e92de8c0daabf8e89f0851` |
| test_memory_diagnostics.py | `e6dd55446cd8660738757170be8931e770406ac7bbb6e2b7fc9ddd94507d44b4` |
| Both LifeOS memory patches | `bdc418e96c7c3b0ae4bddae4668ac54a0db9169c15d8687a8576c7dbf59bc925` |
| Native MemoryStatus.ts | `06789102585fa5f40e610792d1c6f76669781c4c15137e8e4017c12062c190b5` |
| Native MemoryInsights.ts | `4760e16c2d3e83bf57ab330837e5950f516fb5133a9be20ab53fe284f9e7f42f` |
| Native lib/MemoryAccess.ts | `7e084dc6cfe177112a6f414d1307b6016682406a4b54b602392d7286aa270730` |

## Independent tests and commands

Run from the repository:

```sh
PYTHONPATH=.:tests \
LIFEOS_MEMORY_SOURCE=/home/outsider/.cache/lifeos-plugin-memory/source-gate-20260930-diagnostics/lifeos/LifeOS/install \
/home/outsider/.cache/lifeos-plugin-memory/memory-plugin-test-env/bin/python \
-m unittest test_memory_diagnostics test_memory_delta.MemoryDeltaTests test_memory_sources test_memory_delegation test_memory_proposal_delegation -v
```

Result: **69 passed in 56.283 seconds**, exit 0. This is 16 diagnostic cases plus the 53 requested neighboring cases. `raw/run_tests.sh`, `raw/runner.txt`, `raw/tests.txt`, and `raw/tests.done` preserve execution details. The run was detached with `setsid` and checked through its completion artifact.

Each probe used the same interpreter and environment:

```sh
PYTHONPATH=.:tests \
LIFEOS_MEMORY_SOURCE=/home/outsider/.cache/lifeos-plugin-memory/source-gate-20260930-diagnostics/lifeos/LifeOS/install \
/home/outsider/.cache/lifeos-plugin-memory/memory-plugin-test-env/bin/python \
docs/agents/2026-09-30-memory-diagnostics-review/raw/probe_limits.py
```

Substitute `probe_controls.py` and `probe_long_control.py` for the other two programs. All three exited 0. Their raw combined outputs are `limits.txt`, `controls.txt`, and `long-control.txt`. The limit probe deliberately catches and prints the numeric exception to preserve its exact traceback. Commands and the harmless initial source-search miss are recorded in `raw/commands.txt`.

The new CortexHealth tests belong to a different unit and were not run or assessed here.

## Finding 1: valid large proposals lose diagnostic samples

**Severity: medium. Confirmed with a real governed native proposal publication and an unmanaged native control.**

Location: `memory_diagnostics.read`, the construction of `text = line + '\n' + '\n'.join(_strings(row))` and its subsequent `validate_batch` idea payload.

The native proposal sanitizer accepts edit text up to 65,536 characters. Diagnostic validation instead combines the entire serialized row and all decoded string values into one idea content string. That includes the edit twice and also includes metadata. A valid source proposal can therefore fail the unrelated diagnostic idea limit.

`probe_limits.py` enqueues a proposal with a **40,043-character edit** through `NativeMemory.native_add` with the explicit owner proposal grant. Native publication returns `ok: true`, status `pending`, and a revisioned proposal reference. No correction or forget has occurred in this fixture.

The diagnostic service then returns only timestamp, status, and kind. It omits the proposal ID, target path, and edit. Actual `MemoryInsights.ts` reports one pending proposal but renders its recent sample as a blank `?` entry.

The independent `probe_long_control.py` repeats the real publication, records the exact native validation rejection, and compares both native paths against the same queue:

- Managed Insights omits `Synthetic long authorized proposal marker`.
- Unmanaged Insights displays the marker as part of its normal first-80-character sample.
- The combined diagnostic validation payload exceeds the native idea limit and is rejected with `content exceeds size limit`.

This changes authorized owner behavior even though publication succeeded. Counts remain available, so the loss can look like an intentionally excluded proposal rather than an unrelated size check.

### Smallest correction and regression

Separate full-record retained-claim checking from validation of the fields that can actually be displayed. Do not create a duplicated, artificially oversized validation item from an otherwise valid source record. Preserve native first-80-unit display behavior and full-record exclusion before sampling, including a retired claim beyond the displayed prefix.

Add a real native valid proposal near the existing edit size limit. Assert that its diagnostic ID, target, and native display sample remain available and match unmanaged output. Include an over-limit or invalid source control and a retired claim beyond the first display sample.

## Finding 2: the byte cap excludes JSON envelope expansion

**Severity: medium. Confirmed with real native proposal content and actual Bun RPC failure.**

Location: the final `len(rendered.encode())` guard in `memory_diagnostics.read`; transport limit in native `memoryAccess`.

The service puts `rendered` into a JSON string field named `content`. Serializing the outer response escapes backslashes, quotes, and newlines again. Measuring only `rendered` does not measure the bytes passed to the native process.

`probe_limits.py` creates a real valid native proposal whose edit has **5,028 characters**, including a synthetic run of backslashes. Publication succeeds with a pending receipt. The probe repeats that genuine row 230 times in its private synthetic queue to exercise volume. This is a stress reproduction, not a claim that normal production queues contain such duplicates.

Measured result:

| Value | Bytes |
| --- | ---: |
| Projected inner content | 2,357,499 |
| Configured inner-content guard | 3,145,728 |
| Serialized service response | 4,663,294 |
| Native RPC buffer | 4,194,304 |

Direct `MemoryService.native` returns `ok: true`. Actual `MemoryInsights.ts` cannot receive the response and prints that diagnostics are unavailable. The failure is closed to text disclosure, but the intended service size contract does not hold and permitted activity becomes unavailable.

The separate control writes 30,000 valid numeric reviewer rows. A projection that truly exceeds the current inner-content limit is correctly rejected with a structured error, and native Status reports unavailable. Thus this finding concerns envelope expansion, not a missing limit altogether.

### Smallest correction and regression

Enforce the budget against the exact serialized response envelope and leave appropriate space within the native buffer. Reduce data to the fields and samples the native diagnostic consumes where that preserves behavior; do not silently truncate operational counts or the requested time window.

Keep the escaped-content reproducer and assert a truthful structured result before the RPC buffer fails. Include a just-under-budget accepted case and an over-budget refusal case. Native counts, sample ellipsis, and Unicode display behavior should remain consistent.

## Finding 3: oversized integer escapes the structured error contract

**Severity: low. Confirmed malformed-input availability failure.**

Location: `_numbers` in `memory_diagnostics.py`.

The expression `math.isfinite(row[key])` converts Python integers to floating point. A syntactically valid JSON integer such as `10**400` raises `OverflowError` during this conversion. `MemoryService.native` does not catch that exception class.

The probe places this value in `duration_ms` of an otherwise ordinary reviewer row. Direct service invocation raises:

```text
OverflowError: int too large to convert to float
```

The captured traceback identifies `_numbers` and the `math.isfinite` call. The actual native Status command reports unavailable. An invalid numeric field therefore prevents inspection of the remaining valid diagnostic state rather than being omitted like the existing boolean, negative, or nonfinite controls.

This is synthetic malformed data. There is no claim that the current native reviewer normally emits a 401-digit duration.

### Smallest correction and regression

Validate the supported numeric domain without first converting an arbitrary-size integer to float. Account for the JavaScript consumer's representable numeric range. Drop invalid fields consistently and preserve the remaining valid row fields.

Add direct service and real native tests with oversized integers, finite floats, booleans, negative values, and ordinary counts. Assert a structured result and no traceback or whole-report loss from a single invalid value.

## Boundaries and preservation that passed

### Authority and source confinement

Both native diagnostic entry points call `canReadMemorySources` before building their report. The service derives scope from fresh configuration. The diagnostic source gate requires all native read categories and wildcard project access, checks an exact diagnostic allowlist, and checks the permitted physical private-data path.

The focused tests confirm missing/unknown/changed/restricted caller refusal, malformed connector refusal, and a diagnostic-file redirect to a private configuration path. The independent controls add an unapproved model route, a dangling connector symlink, non-string path values, and a direct request for the connector configuration file. All are refused; raw fallback is not observed.

These tests use local trusted context metadata within the existing same-UID boundary. They do not establish a new remote authentication boundary.

### Retained claims and operational activity

Existing tests exclude forgotten proposal text while retaining queue totals, preserve reviewer failure counts after text retirement, and retain numerical growth and health status. The additional control corrects a real governed fact, then writes its superseded quote into JSON using Unicode escapes. The diagnostic excludes that decoded sample while displaying a current control sample and preserving the two-row queue count.

The projection omits arbitrary reviewer/retrieval/error text and limits remaining scalar fields to known keys and enums. This avoids returning the former raw whole-row summaries. Retirement filtering is specifically needed for the permitted proposal ID, target, and edit strings.

Latest invalid reviewer rows remain placeholders rather than causing older successful rows to become the reported latest row. Requested Insights windows are not narrowed to the delta path's 500-row tail; the existing 1,001-row case passes.

### Actual unmanaged parity

The independent control uses four reviewer runs with latencies 10, 20, 30, and 40 ms, typed dispatch counts, a growth row, current health, one current accepted proposal, and one proposal outside a seven-day window. Managed and unmanaged native Insights outputs match exactly:

- Principal growth: seven entries.
- Knowledge additions: eight; idea additions: four.
- One accepted proposal in the requested window.
- Four successful reviewer runs.
- p50: 30 ms; p95: 40 ms.
- Current health: three OK checks, no warn/critical checks.
- Verdict: fresh.

Existing unmanaged tests also confirm raw Status details and current proposal samples when the connector is absent. Removing only the private fixture connector for these controls does not modify any installed system.

## Disposition and review limits

The unit needs the three focused corrections and another bounded review. The passing 69-test gate does not cover these newly measured failures. The initial source snapshot and all raw reproductions are preserved before the parent begins fixes.

No production code, patch, test implementation, dependency, account, or configuration outside disposable fixtures was changed by this reviewer. No commits or live memory/journal calls were made. There is no deployment to undo.

PULSE HTTP binding, CortexHealth, other corpus readers and writers, the broader native audit, whole lifecycle behavior, restricted static prompts, and ownership activation remain explicitly open and outside this review. Whole-file I/O and arbitrary-scale diagnostic history performance were not exhaustively profiled. The owner/unmanaged controls establish specific preserved statistics, not universal behavior for every possible malformed native log.

For Adrian's review, the main design choice is to preserve numerical operational history while suppressing disallowed textual samples. The fixes should retain that distinction, preserve the native requested window and sample semantics, and make refusal explicit at the actual RPC boundary.
