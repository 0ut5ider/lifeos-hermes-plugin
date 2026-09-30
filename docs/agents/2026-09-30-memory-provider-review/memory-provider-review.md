# Hermes memory provider and admission review

Date: 2026-09-30  
Role: Independent bounded code and synthetic integration reviewer  
Question: Does the proposed Hermes provider and required admission integration preserve current conversation permissions, retained-context invalidation, route binding, and existing bridge behavior?  
Model: GPT-6. The exact model variant is not exposed in this agent context.

## Outcome

Four concrete defects were confirmed. Three affect the proposed LifeOS integration. The fourth affects the generic required-middleware contract, although the current LifeOS check itself is synchronous.

The baseline tests pass: 73 plugin memory tests, 4 provider tests, and 12 host tests in the two requested host files. Passing unit tests did not expose the actual host admission worker boundary or general plugin discovery behavior. The independent probes exercised those real host paths against disposable synthetic profiles.

The reviewed files remained unchanged between the initial snapshots and the final source hash comparison. The primary agent received each confirmed finding while this review was in progress and is responsible for implementation. This report records the pre-fix state; it does not claim the fixes have been reviewed.

## Findings

### 1. High: prompt admission does not bind the caller thread

Locations: `lifeos_hook_bridge/memory_runtime.py:102`, `lifeos_hook_bridge/memory_provider.py:69`, prepared Hermes `hermes_cli/plugins_dispatch.py` bounded hook execution.

`MemoryRuntime.admit()` records the admission on disk and sets `_BOUND`, a context variable. Hermes executes the required `pre_prompt_admission` hook in a bounded worker under `contextvars.copy_context()`. Changes made in that copied context do not propagate back to the caller.

The independent probe registered the actual runtime admission callback with an actual prepared-host `PluginContext`, then invoked it through `manager.invoke_hook('pre_prompt_admission')`. The worker observed a valid admitted context. After the hook returned, `runtime.context()` on the caller was `None`.

The same probe then invoked the real `run_llm_execution_middleware()` boundary with a recording terminal callback. The required check raised `MemoryAdmissionError: This model call has no admitted memory context`, and the terminal callback did not run. The provider status tool also rejected the conversation for lack of an admitted context.

This prevents an ordinary enabled conversation from reaching the model or using provider tools. Existing tests call `admit()` directly on their own thread, so they do not exercise the failing integration boundary.

The fix must reconstruct or transfer admission through a trusted host path and bind the caller only after verifying the stored context and current policy. Do not solve it by exporting unverified metadata into process-global environment variables or by removing the required hook timeout. Verify through actual host dispatch, then through model admission and a provider tool in the caller.

Evidence: `raw/provider-probes.jsonl`, case `actual_host_admission_worker_context`. The expected warning from the denied middleware call is preserved in `raw/provider-probes.stderr`.

### 2. High: disabling or removing configuration bypasses checks for retained private context

Locations: `lifeos_hook_bridge/memory_runtime.py:33` and `lifeos_hook_bridge/memory_runtime.py:113`.

`check_call()` returns immediately when `enabled()` is false. That behavior does not distinguish a never-enabled installation from a previously admitted conversation that already contains private memory.

The first probe admitted a synthetic conversation, then saved `ownership_enabled=False` and removed its account grants. It called `check_call()` with a retained private system message and an unapproved endpoint. The check returned successfully, and the old bound context still existed.

A second probe admitted a conversation and deleted its synthetic configuration file. The same retained-context check again returned successfully. Deleting the configuration is a synthetic test action only; no real configuration was touched.

The intended inactive behavior can remain for contexts that have never received governed memory. A previously admitted or persisted context must remain subject to invalidation when ownership is disabled or its configuration disappears. The durable path also needs to cover resumed conversations after restart, not just a live `_BOUND` value.

Evidence: `raw/provider-probes.jsonl`, cases `ownership_disabled_with_retained_context` and `configuration_removed_with_retained_context`.

### 3. High: general discovery stops loading the existing hook bridge

Locations: `lifeos_hook_bridge/__init__.py:22`, `lifeos_hook_bridge/plugin.yaml`, prepared Hermes plugin manifest classification and discovery.

The new initializer contains the `register_memory_provider` source marker. Without an explicit manifest kind, Hermes classifies a directory containing this marker as an exclusive memory plugin. General plugin discovery records exclusive plugins but does not load them, even when their name is in `plugins.enabled`.

The installed-copy probe copied the current plugin into a synthetic profile, configured `plugins.enabled=[lifeos-hook-bridge]`, left `memory.provider` unset, and set memory ownership to false. Actual `discover_and_load()` returned this state:

- `kind`: `exclusive`
- `enabled`: `false`
- `module_loaded`: `false`
- registered prompt-admission hooks: `0`
- error: exclusive plugin requires activation through the category provider setting

The result removes existing bridge hooks from users who have not enabled the new memory feature. This contradicts the intended inactive behavior and affects the entire bridge, not only memory.

Keep ordinary bridge discovery independent of memory selection. When fixing the manifest or registration arrangement, test both general discovery and memory-provider loading. These loaders use different Python module namespaces. Their relative imports therefore create different module-local context variables. Repeated provider loading also needs to preserve effective admission registration without relying on a context variable from another module instance. This is a concrete integration consideration for the fix, not a separately reproduced fourth LifeOS failure.

Evidence: `raw/provider-probes.jsonl`, case `general_plugin_discovery_without_memory_selection`. The script uses a real copied plugin and actual loader, not a mocked manifest classifier.

### 4. Medium: asynchronous required callbacks are accepted but never run

Locations: `patches/hermes-required-middleware.patch`, prepared Hermes `PluginContext.register_middleware()`, `PluginDispatchMixin.invoke_middleware()`, and `admit_llm_request()`.

The required registration wrapper accepts an `async def` callback. The dispatcher calls it synchronously, receives a coroutine object, and appends that object to the results without awaiting or rejecting it. The admission helper ignores returned values, so provider execution proceeds.

The probe registered an asynchronous required admission callback whose body records entry and raises a synthetic denial. The real execution middleware dispatched its terminal callback. The denial body never executed. Python emitted a captured warning that the coroutine was never awaited.

The current LifeOS callback is synchronous, so this probe does not show that this particular callback is bypassed. It shows that the new generic required API silently accepts a callback form for which its fail-closed promise is false.

Either resolve supported awaitable callbacks before dispatch, or reject unsupported asynchronous callbacks and awaitable results with a propagated error. A function can return an awaitable without being declared `async`, so registration-time coroutine-function detection alone does not cover every accepted callable.

Evidence: `raw/required-async-probe.jsonl` and `raw/probe_required_async.py`. The warning was captured explicitly; no provider API was called.

## Design fit within the reviewed scope

The division of responsibility fits the reviewed design. The Hermes provider exposes explicit memory tools through the existing service, while inherited provider recall and synchronization methods remain empty. Native LifeOS continues to own automatic recall and review. The tool schemas use the documented Hermes provider shape.

The runtime compares a current policy signature and a retained-record generation against durable per-conversation admission. Existing synthetic tests demonstrate invalidation after forgetting and account revocation. Actual request models and endpoints are checked against configured route identities, and unknown routes are refused. Those checks are useful, but findings 1 and 2 prevent the current implementation from satisfying the intended admission behavior as a whole.

The bridge clears incoming `LIFEOS_MEMORY_CONTEXT` and `LIFEOS_MEMORY_INTERNAL` before binding an admitted context. Context parsing requires the exact known fields and correct basic types. These are appropriate boundaries for the stated same-user operating system trust model. They are not authentication against arbitrary code running as the same operating system user.

The required host patch places a synchronous admission check before the primary execution terminal and before the selected synchronous and asynchronous auxiliary attempt boundaries. The canonical tests verify propagation of required exceptions and preservation of optional middleware behavior. This review does not establish complete coverage of every model call in the source tree.

## Tests and probes

| Verification | Result |
| --- | --- |
| Plugin `test_memory_*.py` discovery, SDK interpreter | 73 passed in 47.664 seconds, exit 0. |
| `test_hermes_memory_provider.py`, host test interpreter | 4 passed in 0.526 seconds, exit 0. |
| Canonical host runner, required middleware and auxiliary hook files | 2 files, 12 tests passed, 0 failed, exit 0. |
| Actual host admission worker probe | Confirmed finding 1. |
| Disable and remove synthetic configuration probes | Confirmed finding 2. |
| General discovery of synthetic installed copy | Confirmed finding 3. |
| Asynchronous required admission probe | Confirmed finding 4. |
| Bundled required-middleware patch | Byte-identical to top-level patch. |
| Initial and final plugin hashes | No reviewed plugin source changed during this review. |

The preliminary report of 127 related host tests refers to a broader test set. I ran the two files explicitly requested in this task; the canonical runner reported 12 tests. I do not claim to have rerun the broader 127-test set.

The test interpreters were `/home/outsider/.cache/lifeos-plugin-memory/sdk-env/bin/python` and `/tmp/lifeos-plugin-test-venv/bin/python`. The canonical host tests and host-dispatch probes used the owned prepared tree `/home/outsider/.cache/lifeos-plugin-memory/source-gate-20260930-provider/hermes`. The provider unit test uses its declared default prepared tree, `/home/outsider/.cache/lifeos-plugin-memory/source-gate-20260930-native/hermes`.

The probes use real plugin registration, dispatch, configuration persistence, and native synthetic fixtures. Recording terminal callbacks prove whether a model attempt would cross the boundary without sending data to a provider. They are boundary reproductions, not full end-to-end model conversations.

## Evidence and review scope

`raw/commands.txt` contains the verification commands. `raw/memory-tests.txt`, `raw/provider-tests.txt`, and `raw/host-tests.txt` contain complete test output. The two probe scripts and their JSONL results are preserved alongside the expected warning output.

`raw/reviewed-*` and `raw/reviewed-hashes.json` preserve the initial plugin code, patch, and tests. `raw/host-*` and `raw/host-hashes.json` preserve the prepared host sources used to inspect registration, dispatch, profile scoping, and model-call placement.

The review covered the requested provider, admission runtime, context parsing, RPC context boundary, service ownership validation, initializer registration, bridge event environment, generic required-middleware patch, and the supplied tests. It inspected relevant host callers and loaders to establish the concrete integration failures. It did not repeat the previous memory foundation audit or conduct the pending complete source inventory.

## Remaining gates

Restricted and shared prompts are deliberately refused until the installed identity prompt can be filtered. That is an acknowledged design limit, not a finding of this review. Raw child model calls outside Hermes provider routing remain an explicitly open boundary. Activation, native proposal approval, optional SSH enrollment, preferences, backups, and installation are also unfinished gates.

No implementation was edited or committed. No live runtime, live memory, journal, remote machine, or provider API was accessed. All configuration changes and deletion probes were confined to disposable synthetic profiles. The only persistent writes were review artifacts and test-runner output in the owned prepared source tree.

Review the four fixes through their reproduced boundaries before activation. In particular, the next verification must include actual host hook dispatch and actual plugin discovery, not only direct calls to runtime and provider methods.
