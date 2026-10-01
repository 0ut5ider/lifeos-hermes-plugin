# Rendered memory prompt second closure review

Date: 2026-09-30
Role: Independent code reviewer
Question: Does the latest correction close Responses string compression admission, preserve accepted inputs and primary user quotes, and cover meaningful adjacent request forms?
Model: GPT-6. The exact model variant is not exposed in this agent context.

## Conclusion

The Responses string compression finding is closed. All prior archived SDK and compression probes now produce safe results, and all 32 supplied runtime/model-call tests pass. Clean materialized request controls remain accepted.

One adjacent structured Responses input form remains unchecked in trusted compression: function_call_output uses output rather than content. A real required-middleware and SDK probe sent a retired cached claim in that field. The current unit is therefore not fully closed at the request boundary.

The reproduction establishes the admission callback and actual SDK transport behavior. It does not establish that full host compression rotation currently passes this representation. That broader routing and lifecycle reachability remains explicitly outside scope.

## Latest fix verified

The runtime now appends a plain string input to the compression scan only when trusted aux_task is compression. The effective body is projected after extra_body merging, so the runtime regression checks both direct input and an extra_body replacement.

The original closure/raw/probe_responses.py was run unchanged. Its cached retired SOUL input is rejected with the compression-prompt error, requests=0, retired_claim_on_wire=false, and an empty wire capture.

The new real SDK test exercises a valid Responses JSON reply for three cases: clean compression input succeeds, retired compression input is denied before HTTP, and the same phrase in ordinary primary input remains allowed. The runtime test independently checks the primary-user exception for both direct and extra_body input.

## Prior fixes remain verified

- Five archived original SDK child programs, invoked through the unchanged archived driver, deny retired list/tuple/block/extra-body claims or reject lazy containers before transport.
- Generator rejection does not consume the iterator.
- The unchanged original compression helper probe returns null and sends zero requests.
- Effective extra_body model overrides are rejected when the resulting model is not approved.
- Explicit benign SOUL controls succeed for tuple messages, tuple content blocks, and extra_body messages, with the expected system and user text captured on the wire.
- Existing static SOUL tests still pass for stale rendered claims, regular-owner file checks, symlink refusal, fingerprint changes, restart invalidation, and fresh admission after refresh.

Conservative compression refusal is not automatic history repair. A null summary after denied admission is the expected helper outcome; it does not mean the conversation was rebuilt.

## Remaining finding: generated Responses tool output is silently skipped

Severity: Medium for the bounded request-admission surface. Full rotation reachability is unverified.

_messages accepts materialized mappings in input, but the compression branch reads only message.get('content'). A Responses function_call_output item stores its textual model input in output. The current guard silently extracts an empty string from this valid structured item.

The probe uses the same cached-SOUL setup and real PluginContext/required middleware as the original Responses reproduction. It supplies trusted aux_task='compression' and an approved Responses route. The input contains a matching function_call and function_call_output pair. The output field carries the retired cached SOUL text.

Actual result:

- One HTTP request reaches /v1/responses.
- The request body contains the retired claim in input[1].output.
- The SDK call completes against the synthetic Responses fixture.
- No admission error is raised.

Evidence: raw/probe_responses_tool.py, raw/responses-tool-child.py, and raw/responses-tool.txt. The raw capture records requests=1 and retired_claim_on_wire=true and preserves the complete wire body.

Recommended correction: use typed extraction for supported structured generated input, or explicitly reject unsupported input item/block forms in compression. Do not silently treat a materialized object without content as empty. Keep ordinary user-authored quote behavior separate from trusted generated compression input. A correction should cover accepted clean tool-result input or clearly document and test its deliberate rejection.

This finding does not assert full production rotation reachability or a complete tool inventory. The current helper is normally fed a generated user-message summary prompt, and the host adapter's broader replay behavior has not been traced in this bounded review.

## Test results

| Verification | Result | Raw output |
|---|---|---|
| test_memory_runtime.py | 23 passed in 4.050 seconds | raw/runtime.txt |
| test_memory_model_calls.py | 9 passed in 60.536 seconds | raw/model_calls.txt |
| Unchanged original Responses string probe | Denied; zero requests | raw/responses.txt |
| Unchanged archived SDK driver and child payloads | All denied; zero requests | raw/archived.txt |
| Unchanged original summary-helper probe | Null summary; zero requests | raw/compression.txt |
| Unchanged explicit benign SOUL controls | Three accepted requests | raw/accepted.txt |
| Structured Responses tool-output probe | Retired claim sent in one request | raw/responses-tool.txt |

The 32 supplied tests passed with zero failures or skips. Expected denial tracebacks are preserved in the probe outputs. Successful real SDK controls capture the actual body delivered to the local server.

## Evidence and constraints

Python: /home/outsider/.cache/lifeos-plugin-memory/memory-plugin-test-env/bin/python.

Owned host: /home/outsider/.cache/lifeos-plugin-memory/source-gate-20260930-retained-sources-fixed/hermes.

Native fixture: /home/outsider/.cache/lifeos-plugin-memory/source-gate-20260930-retained-sources-fixed/lifeos/LifeOS/install.

Exact commands, source environment, initial/final hashes, and source snapshots are saved in raw/. The unchanged probe drivers are copied and hashed for reproducibility. The original archived SDK child payloads remain in the earlier raw evidence directory referenced by the archived driver.

No implementation edits or commits were made. All state was synthetic and isolated; the only network destination was the temporary localhost fixture. No live systems, accounts, SSH, live Hermes bootstrap/imports, actual memories, or journal tools were accessed.

## Review limits

Full AIAgent invocation, compressor rotation, route and delivery inventory, activation, and automatic history rebuilding remain open. This report closes the last string-input reproduction, preserves all prior verified closures, and identifies one concrete structured-input gap at the same admission boundary.
