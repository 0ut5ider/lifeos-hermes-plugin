# Native delta boundary review

Date: 2026-09-30 (America/Toronto; subprocess evidence uses October 1 UTC)
Role: Independent bounded implementation reviewer
Question: Does the native delta fix enforce current authority and retirement filtering while preserving authorized owner status and cadence?
Model: GPT-6. The exact model variant is not exposed in this agent context.

## Result

**The original privacy defect is reproduced as closed on the fresh distributed source. The bounded unit still needs corrections before closure.** All 47 requested tests pass, but independent probes establish one substantial owner-path performance regression and two diagnostic correctness cases.

The unchanged original audit probe now returns empty stdout and stderr for the missing-context composer. The approved owner receives the current pelican fact and `+1 learned`, with no forgotten cormorant claim. A separate long-claim probe confirms that filtering occurs before sample truncation. This is real Bun execution against the Python service and synthetic native records, not a mocked reader.

Remaining findings:

1. **High: log validation exceeds the registered hook deadline.** A 500-row, 169,500-byte log takes 34.440 seconds to render. The hook has an 8-second registration timeout. Python launches a native validation subprocess per row while holding the cooperating memory transaction, before the native caller applies its 500-row tail bound.
2. **Medium: a malformed row aborts later valid delta output.** A string-valued `additions` field passes source text validation, then causes `.some is not a function`. The subsequent valid row is not rendered and the hook writes unexpected stderr.
3. **Medium: filtering a newer health snapshot can replay an older critical status.** The newest snapshot is excluded because it contains retired text; the consumer then treats an earlier permitted critical row as current. The probe obtains a verbatim critical warning despite the newest row declaring a noncritical result. This is a snapshot-semantics problem, not a retired-text leak.

No code changes, commits, or live-system operations were made by this reviewer. The parent was notified promptly and is responsible for fixes and independent reproduction.

## Reviewed snapshot

Plugin branch: `feature/lifeos-memory`, committed baseline `5cdb33d39d82d4cb60f250e4df855d4dffcf83c2` plus the requested working diff.

Fresh public prepared source:

`/home/outsider/.cache/lifeos-plugin-memory/source-gate-20260930-native-delta/lifeos/LifeOS/install`

Pinned native base remains `5e2f2e8c0abde612da0e99c16c0d07d4ec21b88c`, with the distributed patch. The sibling `hermes` fixture was the only allowed host source. No host/native live imports were used.

Inspected changes:

- `lifeos_hook_bridge/memory_sources.py`: source collection authorization; exact write/health log paths and freshness cache; per-row JSON decoding, native validation, and retained-history filtering.
- `lifeos_hook_bridge/memory_service.py`: `check_sources` dispatch through a current configuration/policy snapshot.
- Native `LIFEOS/TOOLS/lib/MemoryAccess.ts`: `canReadMemorySources`, strict response validation and refusal on exceptions.
- Native `hooks/MemoryTurnStart.hook.ts`: early authorization before injection state and system-delta clearing.
- Native `hooks/MemoryDeltaSurface.hook.ts`: source authorization before heartbeat/cursor work; governed log, health, and freshness reads.
- `tests/test_memory_delta.py` and the specified existing source/delegation suites.
- Both distributed LifeOS patch copies and native hook registration.

`raw/hashes-before.json` and `raw/hashes-after.json` contain SHA-256 for the reviewed production, test, patch, and native files. **All captured hashes remained identical through this review.** Exact reviewed copies are saved under `raw/sources/`.

## What is verified correct

### Admission precedes ordinary denied-call side effects

`canReadMemorySources()` returns false for failed RPC results and connector parsing/permission errors. The composer calls it before `shouldInject` and `clearSystemDelta`. Standalone delta calls it before `touchHeartbeat` and `readCursor`.

The service resolves the current caller from one loaded configuration and requires all native read categories plus wildcard project access. `check_sources` does not accept arbitrary path arguments. The ordinary unknown author, changed participants, absent context, restricted category/project grant, and invalid connector cases return no delta and do not consume existing cursor/injection/heartbeat state in the tests.

This verifies the denied-call cases tested. It is not a proof of an atomic transaction spanning every separate RPC, filesystem state update, and concurrent configuration change in the whole composer.

### Added source paths remain confined

The allowlist expands by two exact observability files and one exact freshness cache file. Existing prefix readers remain under the previous source policy. `_source_path` checks scope before content access, verifies the plugin user boundary, and requires the resolved file to equal the expected physical location beneath the private user tree. The adjusted path calculation still maps ordinary MEMORY sources to the same physical MEMORY subtree.

The redirect tests preserve authorized current output while excluding configuration-only cache content, and refuse the redirected write-log read through the service. Existing 17 retained-source tests pass against the changed path calculation.

### Retirement filtering precedes native presentation

The log reader checks original JSON plus decoded string keys/values before returning rows. `_filter_history` uses each string `ts`, or source mtime when absent, against retained-state timestamps and normalized exact claims. The log bytes themselves are unchanged. Native delta truncation happens later, after the governed result is returned.

Both forgotten and superseded log cases pass. Escaped newlines are decoded before exact-claim exclusion. The independent long-claim case includes retired words beyond the 56-character sample cutoff; it is excluded while a current row remains visible.

### Owner and standalone controls remain present in small fixtures

The authorized owner sees current hot facts, delta counts, heartbeat, freshness grade and counts, and current health findings. Subsequent turns switch to the expected heartbeat form. A no-connector fixture retains the native standalone behavior. These controls are useful, but the volume finding below prevents claiming the production-sized owner path is preserved.

## Finding D1: per-row native processes make normal log growth exceed the hook timeout

Relevant implementation:

- `memory_sources.py:61` holds `memory._transaction()` around the read and complete filtering loop.
- Lines 65-80 iterate every parsed dictionary row in the entire file.
- Line 76 calls `memory._validate` once per row.
- `memory_access.py:195-196` implements `_validate` by `_native("validate", ...)`, spawning a real Bun worker.
- `MemoryDeltaSurface.hook.ts` selects the final 500 lines only after `readMemorySource(WRITES_LOG)` has returned.
- Native `hooks/hooks.json` registers MemoryTurnStart with an 8-second timeout.

The probe used an approved owner, a real current hot record, and controlled counts of a valid native-shaped append-only write row. It changed only timestamps across copies. It did not call a model or external network.

| Rows | File bytes | Complete native composer time | Exit | Stderr |
| ---: | ---: | ---: | ---: | --- |
| 1 | 339 | 0.580 seconds | 0 | empty |
| 100 | 33,900 | 7.932 seconds | 0 | empty |
| 500 | 169,500 | 34.440 seconds | 0 | empty |

The expected current delta eventually appears in all three outputs. The 500-row result is over four times the registered deadline, so the registered caller cannot wait for that result under its stated timeout. The unbounded historical scan also means the native tail limit does not cap validation work. A larger append-only log will encounter the 40-second RPC timeout independently of the 8-second hook deadline. I did not run that larger case or claim a measured RPC timeout.

The per-row process count is established directly from the inspected call graph, not inferred solely from elapsed time. The 100-row measurement overlapped the small shape probe; the 500-row case ran after that probe completed. This was not an isolated operating-system benchmark, but the margin between 34.440 and 8 seconds is material. The source of growth is deterministic.

Smallest correction: select a bounded native-equivalent source window before expensive validation, and validate that window with a bounded number of native worker calls. Keep per-row retained filtering, full-string inspection before shortening, and current owner functionality. Do not solve this by disabling deltas or raising timeouts to follow indefinitely growing logs. Avoid holding the global publication transaction through hundreds of process launches.

Regression evidence should include a real native log containing at least 500 rows and more than the displayed tail window, a fixed bound on worker invocations, a current owner output control, a retired-row control, and completion within the native hook's actual deadline. A deterministic worker-count assertion can complement wall-clock evidence.

## Finding D2: valid JSON with invalid row shape poisons subsequent valid output

The new log branch accepts any dictionary whose textual contents pass the native idea sanitizer. That validates private or transformed content, but it does not validate the native write-row structure.

In `probe_delta_shapes.py`, a row has `additions` set to the string `synthetic wrong shape`, followed by an unchanged valid native current row. The source reader returns the malformed dictionary. Native delta reaches:

```text
MemoryDeltaSurface error: (row.additions ?? []).some is not a function.
```

The test fixture's clean-stderr assertion fails. Delta processing aborts before the valid following row is emitted. `raw/delta-shapes.txt` preserves the actual assertion diagnostic and native error text.

This is a synthetic malformed-input case. The ordinary MemoryWriter does not generate this string shape, and I do not claim it does. The module already tolerates malformed JSON lines, so a parsed but invalid row should not defeat the useful rows or cause uncontrolled diagnostics.

Smallest correction: validate the required write-row types before including a row, or make the native consumer skip invalid rows individually. Include `ts`, `file`, `updated_by`, additions and evictions arrays, and string element types. A string timestamp should also satisfy the expected time contract where required. Keep future unrelated metadata from becoming executable or user-visible text accidentally.

Tests should place malformed rows before and after a valid current row and assert the current delta remains, retired text is absent, cursor behavior is intentional, and stderr stays clean.

## Finding D3: health filtering changes which snapshot is reported as latest

`memory-health.jsonl` is handled with the same filter-all-rows algorithm as an event stream. `criticalHealthLine()` then parses the last surviving row. Consequently, an excluded current snapshot allows an older snapshot to become current again.

The probe creates two post-retirement timestamped health rows:

1. An older critical snapshot with `synthetic older critical marker`.
2. A newer noncritical snapshot whose diagnostic text includes the exact retired long claim.

The second row is correctly excluded for its retained text. The composer then emits the older marker in a `Memory subsystem health is CRITICAL` block, instructing the model to repeat it verbatim. `raw/delta-shapes.txt` contains the exact output. This proves the selection behavior; the rows are controlled synthetic snapshots, not claimed output from an actual new MemoryHealthCheck invocation.

The safe current outcome is either a permitted projection of the actual newest snapshot or an explicit unavailable/unknown result for that snapshot. Replaying a previous snapshot silently is not current diagnostic evidence. The fix should preserve the native owner's latest valid health information without returning retired error bodies.

Tests should cover latest excluded/malformed snapshot after older critical and older healthy rows, including a permitted newest current control. The consumer must not imply that a previous surviving snapshot is the newest source state.

## Independent execution and artifacts

Requested suite:

```sh
PYTHONPATH=.:tests \
LIFEOS_MEMORY_SOURCE=/home/outsider/.cache/lifeos-plugin-memory/source-gate-20260930-native-delta/lifeos/LifeOS/install \
LIFEOS_HERMES_SOURCE=/home/outsider/.cache/lifeos-plugin-memory/source-gate-20260930-native-delta/hermes \
/home/outsider/.cache/lifeos-plugin-memory/memory-plugin-test-env/bin/python \
-m unittest test_memory_delta.MemoryDeltaTests test_memory_sources test_memory_delegation test_memory_proposal_delegation -v
```

**47 passed in 35.893 seconds, exit 0.** Raw command and detached runner are in `raw/run_tests.sh`; output is `raw/tests.txt`, status `raw/tests.done`.

Additional exact probe commands use the same `PYTHONPATH` and `LIFEOS_MEMORY_SOURCE` above:

```sh
/home/outsider/.cache/lifeos-plugin-memory/memory-plugin-test-env/bin/python docs/agents/2026-09-30-memory-native-delta-review/raw/probe_delta_volume.py
/home/outsider/.cache/lifeos-plugin-memory/memory-plugin-test-env/bin/python docs/agents/2026-09-30-memory-native-delta-review/raw/probe_delta_shapes.py
/home/outsider/.cache/lifeos-plugin-memory/memory-plugin-test-env/bin/python docs/agents/2026-09-30-memory-native-audit/raw/probe_native_reads.py
```

Outputs are saved respectively as `raw/delta-volume.txt`, `raw/delta-shapes.txt`, and `raw/original-native-reads.txt`. The original audit probe was not regenerated or modified; its hash is in `raw/original-probe-sha256.txt`. It also executes previously identified diagnostic/PULSE/Cortex cases outside this delta fix. Their continued bypasses are audit evidence, not new failures attributed to this bounded change.

## Limits and review decisions

The original per-turn private/retired readback issue is closed for the tested managed boundary, including the unchanged reproducer. The three findings above concern preserving usable and truthful native status output. They require fixes and a new stable-source closure. This review does not clear the remaining native audit, authenticated PULSE delivery, static restricted prompts, all reader/writer routes, full reviewer lifecycle, history rotation, installation recovery, or ownership activation.

Adrian should review the choice for an excluded latest health snapshot: filtered current metadata versus an explicit unavailable state. The owner should continue to receive meaningful current diagnostics. No production feature was suppressed or changed by this reviewer; only evidence artifacts and temporary synthetic fixtures were written.
