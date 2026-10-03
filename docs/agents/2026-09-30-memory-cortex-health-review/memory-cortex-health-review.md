# Governed Cortex health review

Date: 2026-09-30 (America/Toronto; native raw timestamps use October 1 UTC)
Role: Independent bounded implementation reviewer
Question: Do governed CortexHealth collection and MemoryHealthCheck publication preserve native health decisions while enforcing authority, path confinement, and retained-text exclusions?
Model: GPT-6. The exact model variant is not exposed in this agent context.

## Result

**Three concrete defects remain in the reviewed snapshot.**

1. The optional health-report output path is not included in managed publication preflight. A report can overwrite a fixture configuration file.
2. Text filtering happens before the caller assesses Cortex evidence. Filtering a valid timestamp can create a false critical health finding.
3. A large invalid-hot-entry diagnostic exceeds the existing inbound RPC limit. Managed HealthCheck throws without JSON output; unmanaged native HealthCheck reports the same corrupt file successfully.

The requested independent gate passes: **92 tests in 72.592 seconds**, no failures or skips. Additional controls confirm ordinary managed/unmanaged finding IDs, severities, and counts match. Unknown, changed, restricted, and broken contexts do not publish. The actual HealthGate hook completes in **1.415830 seconds**, publishes its report, and emits the expected critical summary under its real five-second child deadline.

The findings were sent to the parent with saved reproductions. This is the stable initial review, not a closure of subsequent fixes. Ownership activation is not approved.

## Scope and reviewed revision

Repository: `/home/outsider/Projects/Hermes_agent/LifeOS_plugin`, branch `feature/lifeos-memory`.

HEAD: `8970c41d321f7c7b57a5b702d521853994d95db2`, plus the current governed health working diff.

Fresh distributed public native source:

`/home/outsider/.cache/lifeos-plugin-memory/source-gate-20260930-cortex-health/lifeos/LifeOS/install`

Interpreter:

`/home/outsider/.cache/lifeos-plugin-memory/memory-plugin-test-env/bin/python`

Reviewed production paths: `memory_diagnostics.py`, `memory_sources.py`, `memory_service.py`, native `CortexHealth.ts`, `MemoryHealthCheck.ts`, and `lib/MemoryAccess.ts`. Supporting reads covered the existing RPC input parser, structured retained-text projection, and actual `MemoryHealthGate.hook.ts`. Both distributed patch copies are identical. The current native memory patch covers 17 files.

Source snapshots are in `raw/sources/`; exact before/after SHA-256 maps are `raw/hashes-before.json` and `raw/hashes-after.json`. `raw/hash-comparison.json` records no changes through the tests and probes.

| File | SHA-256 |
| --- | --- |
| memory_diagnostics.py | `7d5074b6a3729128c0a13e4c561e6ff06ddc8e069f3102c241d78103bd02d331` |
| memory_sources.py | `6dd11cfe84d1c661103ba084114faea57b7f289f914f0fac6b062ff2eee6a850` |
| memory_service.py | `aae20b85114ef811a636f5875f5e1100af7c28f28a033fa5471ffc15ea8f868f` |
| test_memory_cortex_health.py | `77f12e420a713ce8028abb91d5c1830135546a2a81fa7c2236e2487ea7c98114` |
| Both LifeOS memory patches | `2e95de759097240ab538987c39df962021c3c84e3f030b079883dbb83608cbe4` |
| Native CortexHealth.ts | `8e1dce8f06dbd4beee91739d52ea8163f2a9d4fc1dba88409a4a008f10ff58f9` |
| Native MemoryHealthCheck.ts | `6bfccd851bcf56018702c151f6ba77e1229b821e3af2c52cc26ff220b385bcf5` |
| Native lib/MemoryAccess.ts | `9468d3a69d77cee7af47075fb579571638a5df04d64867c46643909e74e6e4d3` |

## Commands and independent results

From the repository:

```sh
PYTHONPATH=.:tests \
LIFEOS_MEMORY_SOURCE=/home/outsider/.cache/lifeos-plugin-memory/source-gate-20260930-cortex-health/lifeos/LifeOS/install \
/home/outsider/.cache/lifeos-plugin-memory/memory-plugin-test-env/bin/python \
-m unittest test_memory_cortex_health test_memory_diagnostics test_memory_delta.MemoryDeltaTests test_memory_sources test_memory_delegation test_memory_proposal_delegation -v
```

Result: **92 passed in 72.592 seconds**, exit 0. This comprises 18 new Cortex/health cases, 21 diagnostic cases, and 53 preceding neighboring cases. The exact detached runner, output, and completion code are `raw/run_tests.sh`, `raw/runner.txt`, `raw/tests.txt`, and `raw/tests.done`.

Additional scripts:

```sh
PYTHONPATH=.:tests \
LIFEOS_MEMORY_SOURCE=/home/outsider/.cache/lifeos-plugin-memory/source-gate-20260930-cortex-health/lifeos/LifeOS/install \
/home/outsider/.cache/lifeos-plugin-memory/memory-plugin-test-env/bin/python \
docs/agents/2026-09-30-memory-cortex-health-review/raw/probe_health_edges.py
```

Use the same environment for `raw/probe_controls.py`. Both programs exit 0 and preserve child stdout, stderr, outcomes, and fixture data in `raw/health-edges.txt` and `raw/controls.txt`.

`raw/probe_rpc_volume.py` runs with the complete interpreter and uses only the saved synthetic report. Its output is `raw/rpc-volume.txt`. It deliberately passes a nonexistent fixture configuration path because request parsing fails before configuration access. This confirms the transport cause independently of memory state.

All probe scripts and commands are retained. `raw/commands.txt` records command details and a harmless read-only artifact lookup before the hash-comparison file was created.

## Finding 1: optional report destination bypasses publication preflight

**Severity: medium. Confirmed unintended publication destination within an isolated owner fixture.**

Location: native `MemoryHealthCheck.ts` preflight near the top of the module and the final `CORTEX_HEALTH_REPORT_PATH` publication block.

Managed preflight attests the root, selected diagnostic inputs, the normal health log, relevant directories, and hot files. The optional machine-readable report path is then passed directly to `atomicWriteJSON` without equivalent attestation.

The saved `report-path-override` case:

1. Creates a private owner fixture with the governed connector.
2. Writes a sentinel into `LIFEOS/USER/CONFIG/synthetic-protected-output.json`.
3. Runs actual `MemoryHealthCheck.ts` with `CORTEX_HEALTH_REPORT_PATH` set to that file.
4. Observes exit 2 for the fixture's critical health status and the sentinel replaced by the complete health report.

The result records `target_changed: true` and the exact replacement. The default health-log path check does not constrain this other destination.

This is not an operating-system sandbox bypass or a claim against a hostile same-UID process. It is a gap in the new managed publication boundary: the health operation accepts an alternate output destination that was not checked along with its normal destination. The environment override is native functionality and remains useful for unmanaged fixture/automation callers.

### Smallest correction and tests

When managed, bind the optional report output to an explicitly permitted diagnostic destination and attest it before publishing either output. Reject unsupported destinations or provide a narrow approved report location. Preserve unmanaged native automation behavior.

Add a direct configuration-file target, a redirected target, an alternate-root target, and a permitted destination control. Verify refused destinations remain byte-identical and that partial publication does not occur before the preflight failure.

## Finding 2: filtered evidence changes the native assessment

**Severity: medium. Confirmed false critical finding.**

Location: `collectCortexEvidence` returns `filterMemoryDiagnostic(evidence, ...)`; its caller then invokes `assessCortexEvidence` on that filtered object.

The Python projection protects status/severity enums, but other strings can be replaced by the unavailable-details marker. Those strings are not all presentation-only. Native assessment parses reviewer and retrieval timestamps and uses them to determine validity and freshness.

The `retired-timestamp` case uses a real governed remember/forget operation for an exact ISO timestamp. It then writes a structurally valid native skipped-reviewer row with that timestamp. This is a synthetic edge case designed to exercise the distinction between a diagnostic value and its displayed text.

Against the same log:

| Observation | Managed | Unmanaged |
| --- | --- | --- |
| Reviewer status | skipped | skipped |
| Reviewer timestamp | unavailable-details marker | original valid ISO timestamp |
| Reviewer finding | reviewer-evidence-invalid, critical | no reviewer failure |
| Overall | critical | warn from unrelated absent fixture evidence |

The raw result preserves both evidence and assessment objects. No invalid timestamp existed in the source. The new critical finding is caused by projection before assessment.

### Smallest correction and tests

Compute the native assessment from validated original evidence before text projection. Preserve the resulting finding IDs, severities, counts, and freshness decisions while filtering displayable details. Do not restore a retired timestamp merely to avoid the false finding.

The collector API and callers must make clear which representation is authoritative for assessment. A string placeholder is not a valid substitute for an operational value that will be parsed later.

Keep the saved valid-skip case, plus valid-success and retrieval timestamp controls. Verify that permitted severity/codes match unmanaged assessment while retired text stays absent from returned evidence, stdout, and published health records.

## Finding 3: large invalid-entry diagnostics exceed the request boundary

**Severity: medium. Confirmed loss of the health report for a corrupt hot file.**

Location: `filterMemoryDiagnostic` serializes the entire report into the generic native RPC request; `memory_rpc.main` reads at most 131,073 characters. The final native HealthCheck filter call is not caught as a structured unavailable result.

The `invalid-hot-volume` case puts 500 overlength entries in the private principal hot file. This intentionally exercises health inspection of a corrupt file, not ordinary valid curation beyond the native entry cap.

Observed behavior:

| Observation | Managed | Unmanaged |
| --- | --- | --- |
| Native process duration | 1.307644 seconds | 0.044850 seconds |
| Exit | 1, thrown filter error | 2, native critical health |
| Stdout | empty | 228,828 characters of valid report JSON |
| Stderr | Bun stack trace | empty |
| Invalid-entry diagnostics | no delivered report | complete native report |

The recorded failure is at the final `MemoryHealthCheck.ts` call to `filterMemoryDiagnostic`. The direct followup constructs the compact request from the captured native report: **207,100 bytes** versus the **131,073-character** read ceiling. Actual RPC parsing returns a structured error for an unterminated JSON string before reading any configuration.

This is a request-size failure, not a five-second timeout. The actual HealthGate implementation catches child failures and only surfaces a warning if it can parse report JSON from stdout. Empty stdout therefore removes its usual health summary. That consequence is source-traced; the separate real-hook control below verifies the normal summary path.

### Smallest correction and tests

Bound diagnostic detail transport while preserving full invalid-entry counts and native findings, or introduce a bounded transport that can carry the required report. Do not merely increase an unrelated limit without testing the complete request/response path.

Ensure excessive diagnostic volume produces a deliberate structured result rather than an uncaught stack trace. Keep current health codes/counts available where text can be safely summarized. Test the saved 500-entry corrupt file, escaped entry text, final publication, and the actual HealthGate wrapper under its five-second child deadline.

## Controls that passed

### Authority and path refusal

Existing tests confirm missing context, alternate root, reviewer-file redirect, reviewer-directory redirect, index-directory redirect, and health-log redirect refusal. The output-redirect test preserves the configuration sentinel for the normal `memory-health.jsonl` path.

The independent controls additionally exercise unknown author, changed model route, restricted category grant, and a dangling connector. All return unavailable and leave the fixture health log absent. There is no raw fallback after those failures.

These controls verify the normal governed paths. They do not clear the unchecked optional report-output override in Finding 1, nor do they establish an OS security boundary against a same-UID process.

### Diagnostic-only invalid hot inspection

A fixture contains one actual committed valid fact and one overlength entry. The `diagnose_hot` RPC returns exactly one `dropped_invalid` record, with reason `overlength`, and no fact entries or valid fact body. The ordinary governed read remains refused with `Native hot memory needs repair before governed curation`.

Thus the small diagnostic path does not silently make an invalid hot file eligible for ordinary recall or curation. The volume failure is separate.

### Severity, counts, publication, and malformed rows

The focused tests preserve current reviewer errors, critical status after retirement, malformed-line numbers, invalid latest-row classification, missing-hot critical findings, and exclusion of decoded retired errors before output/publication.

The independent owner/unmanaged control compares actual HealthCheck reports from identical fixture data. Finding IDs and severities match. Both report **2 critical, 9 warn, and 19 OK** checks. The extra critical in this fixture is the expected absent delta heartbeat after its actual native remember operation; it is not a production health claim.

The suite confirms that published `memory-health.jsonl` content equals stdout and that retired error/state/invalid-entry strings do not reappear there. It also confirms missing identity causes no new publication.

### Actual five-second gate

The control invokes the real prepared `hooks/MemoryHealthGate.hook.ts`, which invokes HealthCheck with its own `timeout: 5000` setting. It completes in **1.415830 seconds**, exits 0, produces empty stdout, publishes a health row, and emits the expected critical summary for two blockers on stderr.

The stderr line is expected native output and is explicitly asserted. It is not ignored test noise. This establishes the deadline for this bounded fixture, not for arbitrarily large source files or system load.

## Disposition and limits

The 92 passing tests do not cover the three new reproductions. The unit requires corrections followed by another bounded review. No optional broad audit was added after the findings were established.

PULSE HTTP authentication, corpus readers, restore and other writers, full lifecycle behavior, restricted static prompts, and ownership activation remain outside scope and open. Whole-file I/O remains unbounded as already declared. The review does not claim sandboxing against hostile same-UID filesystem changes or universal concurrency protection outside cooperating operations.

Only evidence artifacts and disposable synthetic fixtures were modified by this reviewer. No implementation edits, commits, dependencies, live imports/bootstrap, SSH, account changes, or memory/journal calls occurred. No installed configuration or runtime changed, so there is no deployment to undo.

For Adrian's review, the main requirement is to retain native health meaning while filtering only what can be displayed. Publication must also honor every managed output destination. The current normal-case controls support those goals, but the saved edge cases show where the implementation still differs.
