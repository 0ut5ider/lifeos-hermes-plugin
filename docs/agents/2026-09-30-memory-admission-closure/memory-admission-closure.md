# Memory admission closure review

Date: 2026-09-30  
Role: Independent bounded implementation and synthetic integration reviewer  
Question: Are terminal admission and fingerprint-bound SSH revocation corrected, and do the actual child adapters enforce current admission across route, configuration, and retained-context changes?  
Model: GPT-6. The exact model variant is not exposed in this agent context.

## Outcome

The previous terminal and SSH key-collision findings are closed in their unchanged reproduction scripts. The child adapters correctly refuse unapproved routes, missing admission under enabled ownership, mismatched configuration paths, and forgotten context in the tested paths.

One high-severity defect remains: disabling or deleting ownership configuration can release a retained child prompt after admission and environment rebinding remove its inherited context. A real localhost recorder received the private synthetic marker in both failing cases.

All baseline test gates passed: 85 memory tests, 7 provider tests, 7 adapter tests, and 131 canonical host tests. The reviewed files did not change between their initial snapshots and the final hash comparison.

## Finding: high, environment rebinding removes the evidence that a child prompt requires admission

Locations: `lifeos_hook_bridge/memory_runtime.py`, `admit()`, `bind_environment()`, and the inactive branch of `check_call()`; consumed by `lifeos_hook_bridge/bin/claude_direct.py`.

When ownership is disabled, `admit()` clears `_BOUND` and returns without checking whether the current conversation was previously admitted. `bind_environment()` removes `LIFEOS_MEMORY_CONTEXT` and restores it only when ownership is enabled and a context remains bound. A new raw child therefore receives the sealed configuration path but no inherited context identifying its retained conversation.

The standalone raw adapter then constructs `MemoryRuntime` for that configuration. With disabled or missing configuration, no inherited context, and no available caller session metadata, `check_call()` treats the request as inactive and permits it. The durable admission record still exists, but the child has lost the session identity needed to select it.

### Reproduction

The probe uses actual runtime methods, the standalone adapter process, and a localhost HTTP server:

1. Create a synthetic native store and approved child route. Admit the parent conversation.
2. Bind a child environment from that admitted conversation.
3. Disable memory ownership in the synthetic configuration.
4. Call `admit()` for the same conversation, then `bind_environment()` again, as the host admission and hook path does.
5. Invoke `claude_direct.py` with a retained private synthetic system prompt and the rebound environment.

The child exits 0 and sends the system prompt to the recorder. Deleting the configuration and using that rebound environment also exits 0 and sends the prompt.

The controls are useful: retaining the original inherited context causes both disabled and deleted configuration requests to exit 1 with zero HTTP requests. The problem is the removal of retained-context identity, not a failure of the existing denial when that identity survives.

The private marker was supplied directly as the retained child prompt in this boundary probe. The test does not invoke an entire native reviewer. It proves that the runtime-to-environment-to-adapter sequence can convert a previously admitted prompt into an ungoverned network request. The registered prompt-admission wrapper invokes runtime admission before native bridge hooks, so refusing this state before those hooks is an appropriate place to preserve the guarantee.

Keep previously admitted conversation identity subject to revocation when ownership becomes inactive or unavailable. Do not erase that identity and then classify the child as a never-enabled caller. A safe fix can reject the revoked conversation at prompt admission before any native hook runs, with a child-side guard for inherited retained context. Preserve the intended inactive behavior for installations that have never admitted governed context.

Evidence: `raw/probe_children.py`, `raw/child-probes.jsonl`, and `raw/child-extra-probes.jsonl`, cases `raw_disabled_after_admission_and_environment_rebind` and `raw_deleted_after_environment_rebind`. The finding was sent to the primary agent as soon as the first real HTTP reproduction completed.

## Previous fixes verified

### Terminal worker handoff

The unchanged terminal probe now records an approved terminal admission and dispatches its recording model callback once. Gateway metadata still has an empty platform field, as in the original failure. The guard now fills platform and session metadata from the actual host arguments before comparing the recorded context.

The seven provider tests also pass, including actual bounded terminal and gateway dispatch and provider use through separate loader namespaces. This closes the previous CLI finding within the reproduced path.

### Fingerprint-bound SSH revocation

The unchanged collision probe now removes the enrolled restricted key and preserves the unrelated key with the same comment. `enrolled_line()` requires the restricted-command prefix, an Ed25519 entry, the exact client marker, and the stored credential fingerprint. The full memory suite also reruns the real localhost SSH test, including denial on an open connection after revocation.

The separate-process configuration probe still preserves all 32 concurrent updates and the disabled client state. This closes the previous key-collision finding within the reproduced path.

## Child admission verification

The additional probe drives both actual child implementations:

- The raw gateway branch executes `claude_direct.py` as a separate process.
- The Hermes provider branch imports the adapter from the repository, loads the copied plugin through actual discovery in a disposable profile, and calls the actual prepared-host `agent.auxiliary_client.call_llm()` path. It uses a custom provider connected only to the localhost recorder. No model API is mocked and no external provider receives a request.

| Case | Child exit | New HTTP requests | Result |
| --- | --- | --- | --- |
| Approved raw gateway | 0 | 1 | Synthetic private marker reaches the approved recorder. |
| Raw gateway with missing context and enabled ownership | 1 | 0 | Refused. |
| Raw gateway with another configuration path | 1 | 0 | Refused with inherited context intact. |
| Disabled configuration with original inherited context | 1 | 0 | Refused. |
| Disabled configuration after admission and environment rebinding | 0 | 1 | Confirmed finding. |
| Deleted configuration with original inherited context | 1 | 0 | Refused. |
| Deleted configuration with rebound environment | 0 | 1 | Confirmed finding. |
| Approved actual Hermes provider | 0 | 1 | Synthetic private marker reaches the approved recorder. |
| Actual Hermes provider with unapproved resolved endpoint | 1 | 0 | Refused by required admission. |
| Actual Hermes provider with missing inherited context | 1 | 0 | Refused. |
| Actual Hermes provider after forgetting a fact | 1 | 0 | Refused as invalidated context. |
| Legacy native Claude fallback with inherited context | 1 | 0 | Refused before the temporary recording executable runs. |

The supplied `test_memory_children.py` also independently verifies the actual raw gateway's unapproved-endpoint and post-forget denials. The wrapper retains normal adapter behavior for the existing ungoverned fixtures.

The environment binding now overwrites `LIFEOS_MEMORY_CONFIGURATION` and `HERMES_HOME` with the active runtime's configuration and profile paths. The mismatched-configuration probe confirms that an inherited governed context cannot silently become inactive solely because a different missing configuration path is selected.

The provider branch verifies that the required middleware capability is available and an admission middleware is registered. The actual copied-plugin test demonstrates the expected registration and concrete resolved-route check. This review does not claim that arbitrary third-party middleware is equivalent to the LifeOS admission callback or that every native model-call site has now been inventoried.

## Test gates

| Gate | Result |
| --- | --- |
| SDK interpreter, `test_memory_*.py` | 85 passed in 54.860 seconds, exit 0. |
| Host test interpreter, `test_hermes_memory_provider.py` | 7 passed in 4.469 seconds, exit 0. |
| Host test interpreter, `test_claude*adapter.py` | 7 passed in 2.774 seconds, exit 0. |
| Canonical host runner, four requested files | 131 passed, 0 failed, across 4 files in 16.0 seconds, exit 0. |
| Unchanged terminal probe | Corrected outcome verified. |
| Unchanged sharing/configuration probe | Collision corrected; all 32 concurrent updates preserved. |
| Twelve-case child probe | Ten expected outcomes, plus the two failing variants of the one finding above. |

The canonical host runner used the owned prepared tree `source-gate-20260930-native/hermes`. The six inspected patched host files also compare byte-identically with the fresh `source-gate-20260930-sharing/hermes` tree. Top-level and bundled required-middleware patches compare equal.

Actual provider negatives report expected admission exceptions in captured stderr. The host test environment also reports its existing `mcp==2.0.0` dependency diagnostic when discovering the copied plugin. The SDK environment ran MCP and SSH tests successfully. This remains a test-environment boundary, not verification of a deployed unified environment.

## Evidence

The report directory contains:

- `raw/reviewed-*` and `raw/reviewed-hashes.json`: reviewed plugin, child, patch, and test snapshots.
- `raw/host-*`, `raw/host-hashes.json`, and `raw/source-verification.json`: patched host identity, fresh-tree comparisons, and confirmation of no reviewed source drift.
- `raw/memory-tests.txt`, `raw/provider-tests.txt`, `raw/adapter-tests.txt`, and `raw/host-tests.txt`: complete test output.
- `raw/terminal-probe.jsonl` and `.stderr`: unchanged terminal reproduction output.
- `raw/sharing-probes.jsonl`: unchanged sharing and process-concurrency output.
- `raw/probe_children.py`: complete reproducible child probe.
- `raw/child-probes.jsonl`: initial eight-case results that first established the finding.
- `raw/child-extra-probes.jsonl`: final twelve-case run, including actual provider negatives and legacy fallback refusal.
- `raw/child-probe-summary.json`: compact case, exit code, and HTTP request counts.
- `raw/commands.txt`: exact verification commands.

The child script was extended after its first successful run. The final script reproduces all twelve cases; both output sets are preserved rather than replacing the initial finding evidence.

## Scope and remaining work

The review covered terminal reconstruction, fingerprint-bound key removal, configuration/profile binding, the raw gateway child, the Hermes provider child, and inherited-context refusal in the legacy Claude fallback. It did not repeat the prior full memory foundation audit or inspect unrelated preference and status work.

The operating system user remains the local trust boundary. UI, proposal approval, backup, complete native-call inventory, and full activation remain open and are not claimed complete. The remaining finding must be fixed and reprobed before closing retained-context admission.

No implementation code was edited or committed. No live Hermes runtime, memory or journal tool, external model service, or fleet host was accessed. All network requests went to disposable localhost fixtures. The full suite's SSH test used only its generated temporary credentials and its own localhost daemon.
