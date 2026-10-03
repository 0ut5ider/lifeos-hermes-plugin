# Memory history repair third closure

Date: 2026-09-30

Role: Independent bounded closure reviewer

Question: Do generalized auxiliary scanning and decoded system instructions close the remaining admission gaps without regressing accepted calls or prior repair behavior?

Model: GPT-6. The exact model variant is not exposed in this agent context.

## Conclusion

**Bounded closure verified. No further material defect found in the reviewed changes.**

All **71 focused tests passed in 126.297 seconds**, with no failures or skips. The unchanged archived child programs reproduce the corrected behavior: the compressor accepts benign generated input, primary user quotes remain permitted, and an auxiliary Responses string containing an exact retired claim is refused before HTTP dispatch.

The new decoded-instructions denial passes through the actual SDK. Additional independent positive controls confirm that clean JSON instructions and clean non-compression auxiliary Responses input still reach the endpoint successfully.

This closes the reported implementation defects for this bounded unit. It does not close resume repair, changed installed SOUL repair, compression rotation, Responses history repair, restricted prompts, delivery, or ownership activation.

## Reviewed changes and source stability

I reviewed the current memory_runtime.py, memory_history.py and memory_provider.py changes and the related host, runtime, history, model-request and provider tests. The key changes since the preceding report are:

- Every trusted auxiliary task receives recursive generated-input inspection, including a string-valued Responses input.
- Compression retains its specific refusal label. Other auxiliary tasks report an auxiliary-prompt refusal.
- System and developer content, top-level system, and top-level instructions first undergo materialized-form validation and then recursive decoded-text inspection.
- Primary human-input proof handling, fact-generation-only refresh, and lock-protected registry revalidation remain in place.

Exact file snapshots and SHA-256 hashes are saved in `raw/source-hashes.json` and adjacent files. The final comparison found **no source drift**. `raw/source-changes.json` is empty. Original reports and reproduction artifacts were preserved.

## Independent tests

| Module | Tests | Result |
| --- | ---: | --- |
| test_memory_agent | 6 | Passed |
| test_memory_history | 16 | Passed |
| test_memory_runtime | 25 | Passed |
| test_memory_model_calls | 13 | Passed |
| test_hermes_memory_provider | 7 | Passed |
| test_memory_host | 4 | Passed |
| Total | 71 | Passed |

The full stdout/stderr is `raw/tests.txt`. The runner executes the unchanged unittest methods and saves actual full-agent wire outcomes for the six agent cases. It does not replace the host, provider, native functions, or SDK calls.

These tests retain the concurrent-admission regression, inactive-lineage refusal, actual governed native LoadMemory correction and forget turns, transcript preservation, current-user prefix proof, policy/identity/route checks, malformed-container refusal, and required-instruction protection.

## Archived original reproductions

I invoked the archived child programs directly. I did not regenerate them through source-string substitutions against the changed helper. `raw/rerun_archived.py` records the exact child hashes and verifies outcomes. Copies and hashes are retained in `raw/archived-hashes.json` and the archived child files.

| Unchanged child case | Result | Actual HTTP requests |
| --- | --- | ---: |
| Original proof-bearing primary request | Success; clean stderr | 1 |
| Original proof-bearing ContextCompressor request | Non-null successful summary; clean stderr | 1 |
| Retired quote in primary Responses input | Allowed primary quote control | 1 |
| Same retired input under trusted memory_review auxiliary context | Refused with auxiliary-prompt error | 0 |

Exact output and request bodies: `raw/archived-results.txt`.

The archived compressor child retains SHA-256 `c2b282f189216feac004ae21e41ebfa811b1a4f3575b4f9b7aa7973ca5ed6223`. Its clean result confirms the original summary-helper regression remains corrected after generalizing auxiliary inspection.

The auxiliary Responses case now fails at required admission rather than reaching the endpoint. The primary control still sends the intentional current user quote. This verifies the intended distinction at the real SDK boundary.

## Escaped instructions and accepted controls

The new regression test puts the retired claim inside JSON-encoded top-level Responses instructions with an escaped newline. It receives the model-system-prompt refusal and observes zero HTTP requests. Recursive inspection now applies to that decoded content after validating its materialized form.

I added two review-only controls, saved in `raw/probe_allowed_responses.py`:

| Current permitted content | Result | HTTP requests |
| --- | --- | ---: |
| JSON-encoded Responses instructions | SYNTHETIC-MODEL-OK; clean stderr | 1 |
| memory_review auxiliary Responses string input | SYNTHETIC-MODEL-OK; clean stderr | 1 |

Exact results are in `raw/allowed-responses.txt`. These controls show that the fix accepts the exercised supported forms when they contain no retired claim. It does not simply disable those paths.

The primary's earlier escaped-instructions failure capture is preserved separately as `raw/primary-instructions-before.txt`. I did not rerun the old implementation and do not count that capture as independent evidence.

## Safety and execution record

All runs use `/home/outsider/.cache/lifeos-plugin-memory/memory-plugin-test-env/bin/python`, PYTHONPATH=.:tests, and explicit owned app-startup Hermes and LifeOS source paths. Exact commands are in `raw/commands.txt`. All records, profiles, configuration writes, and HTTP endpoints are synthetic local fixtures.

No implementation edits, commits, live Hermes import/bootstrap, live server or fleet access, SSH, account changes, or memory/journal calls occurred.

A preliminary positive-control launch contained a reviewer shell assignment error and exited before Python ran. The corrected recorded command completed successfully. It was not a fixture or production-code failure; the command record preserves the distinction.

## Limits and what Adrian should review next

The evidence covers explicit native mutation turns, request-only chat-history projection, required admission, and the tested auxiliary/request representations. Original transcripts retain their content. Exact normalized retired-claim checks do not prove semantic erasure of paraphrases.

The compressor check exercises the real summary helper and SDK transport, not a complete compression rotation. The Responses checks prove accepted requests and denial of retired generated content, not automatic Responses history repair.

**Resume repair, changed installed SOUL repair, compression rotation, Responses repair, restricted prompts, delivery, and ownership activation remain open.** Those gates must retain their own verification requirements. This report supplies closure only for the reviewed history-repair and request-admission unit.
