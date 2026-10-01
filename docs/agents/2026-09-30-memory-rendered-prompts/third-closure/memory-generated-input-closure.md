# Generated-input and managed startup closure review

Date: 2026-09-30
Role: Independent code reviewer
Question: Does recursive generated-input inspection close the structured Responses finding, and does managed remote startup preserve per-source policy checks across apps?
Model: GPT-6. The exact model variant is not exposed in this agent context.

## Conclusion

The remaining structured Responses tool-output finding is closed. All earlier SDK, extra_body, string-input, and summary-helper reproductions also remain closed. All 52 focused tests passed against the fresh distributed app-startup source. No additional material defect was found in this bounded review.

The managed startup change admits dynamic sources for an approved owner context across chat-a and chat-b. Unknown, missing, restricted, and invalid-connector contexts expose none of the four dynamic source markers tested. Standalone remote behavior remains isolated when no governed connector exists.

This supports closure of the generated-input and managed dynamic-startup unit. It does not establish full AIAgent invocation, compressor rotation, restricted static prompts, delivery, ownership activation, or automatic history rebuilding.

## Recursive generated input

_generated_text visits materialized mappings, their keys and values, lists, tuples, and strings. It also decodes JSON inside strings and inspects those decoded values. This covers Responses function_call_output.output and JSON encoded tool results, as well as arguments and nested tool-call fields that do not use content.

The traversal runs only when trusted host middleware identifies aux_task as compression. Ordinary primary user quotes retain their exception. System/developer instruction checks and effective extra_body merging still run separately, including the effective model identity.

The unchanged original structured Responses probe now records zero requests and no retired claim on the wire. The real SDK suite accepts clean direct and JSON tool outputs and denies their retired-claim counterparts. The original string-input probe is also denied, as are the archived tuple, generator, and extra_body system-prompt bypasses.

Depth is bounded at 32. Unsupported nonmaterialized values fail closed. Additional direct helper probes confirmed rejection of an excessively deep structure, a cyclic list, and a nested lazy iterator. The nested iterator remains unconsumed after rejection. The supplied runtime suite independently covers bounded and lazy generated inputs.

No automatic rebuild follows from refusal. The summary helper catches the admission error, returns null, and performs no model request. That behavior is verified explicitly rather than inferred from its process exit code.

## Managed startup behavior

The native LoadContext guard now skips remote dynamic loading only when no governed connector exists. Presence of a connector permits source evaluation; it does not grant source access by itself. Relationship notes, wisdom frames, advisories, session names, work metadata, and project progress continue to use their governed source paths and filters.

The supplied source tests verify:

- Unmanaged remote startup omits private owner context.
- Approved owner contexts can receive the same relationship source through two independently configured apps.
- Missing context, an unknown author, and a project-only restricted context omit private dynamic text.
- Existing retained-claim, JSON decoding, source redirect, private markup, and accepted standalone behavior still pass.

An additional actual Bun startup matrix populated four distinct synthetic sources simultaneously: relationship notes, wisdom frames, advisory findings, and project progress. The approved chat-a owner received all four markers. Missing context, an unknown author, restricted grants, and a dangling connector each produced zero markers. This confirms that permitting the managed remote branch does not turn a configured but invalid connector into an unmanaged read.

The initial custom startup probe used synthetic.json for progress. Native getProjectProgress enumerates only filenames ending in -progress.json, so that fixture yielded only three markers. The failed output is preserved in raw/startup-probe-fixture-error.txt. Changing only the probe filename to synthetic-progress.json made the valid control show all four markers; the empty objectives list and all negative assertions were preserved. No implementation fix was needed.

## Independent verification

| Gate or probe | Result | Evidence |
|---|---|---|
| test_memory_runtime.py | 25 passed, 11.756 seconds | raw/runtime.txt |
| test_memory_model_calls.py | 10 passed, 85.392 seconds | raw/model_calls.txt |
| test_memory_sources.py | 17 passed, 25.512 seconds | raw/sources.txt |
| Original Responses string probe | Denied, zero requests | raw/responses-string.txt |
| Original Responses tool-output probe | Denied, zero requests | raw/responses-tool.txt |
| Archived original SDK child payloads | All denied before transport | raw/archived-sdk.txt |
| Original compression helper probe | Null summary, zero requests | raw/compression.txt |
| Explicit benign SOUL tuple/extra_body controls | Three accepted requests | raw/accepted.txt |
| Four-source managed startup matrix | Four allowed; zero in each denied case | raw/startup-probe.txt |
| Deep, cyclic, and nested-lazy generated inputs | Rejected; lazy value unconsumed | raw/startup-probe.txt |

Total supplied tests: 52 passed, zero failures or skips. Timings are the observed concurrent fixture runs and are not performance benchmarks.

The archived probe drivers were run unchanged from their existing paths. In particular, the original SDK children were selected directly, rather than regenerated by text replacement against the current helper. Copies and hashes of those drivers are retained in raw/. Raw stdout uses .txt files and includes expected denial exceptions.

## Source and evidence

Python environment: /home/outsider/.cache/lifeos-plugin-memory/memory-plugin-test-env/bin/python.

Native source: /home/outsider/.cache/lifeos-plugin-memory/source-gate-20260930-app-startup/lifeos/LifeOS/install.

Owned host source: /home/outsider/.cache/lifeos-plugin-memory/source-gate-20260930-app-startup/hermes.

Exact commands, initial and ending hashes, source snapshots, host hashes, probe scripts, and complete outputs are saved in raw/. The paired LifeOS memory patches are byte-identical. The full detached plugin gate reported by the primary agent was not rerun or claimed as independent evidence here.

No implementation files were edited and no commits were made. All records, configuration, and network responses were isolated synthetic fixtures. The only HTTP server was temporary and local. No live systems, accounts, SSH, live Hermes bootstrap/imports, actual memories, or journal tools were accessed.

## Remaining limits

The primary model fixture is an explicit required-middleware call around the real SDK. Compression invokes the actual summary helper, not a complete AIAgent rotation. The remote startup fixtures verify dynamic source output; they do not prove restricted static-prompt safety or delivery to the correct external recipient.

Recursive JSON inspection covers the tested materialized generated text forms. It does not claim arbitrary encoded binary or semantic paraphrase detection. Conservative refusal of stale generated input is not an automatic history rebuild.

Full host/source/tool and routing inventories, lifecycle and delivery closure, activation, and release gates remain open. Those limits do not reopen the concrete reproduced request-boundary findings closed by this review.

All reviewed source hashes remained unchanged during the closure.
