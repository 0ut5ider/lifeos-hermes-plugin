# Development capture implementation review

Date: 2026-09-30
Agent role: Independent implementation reviewer
Question: Does development/hook_capture preserve runtime behavior and capture useful evidence without credential leaks?
Model: GPT-6.1-Sol, high reasoning effort

## Scope and recommendation

Reviewed store.py, bootstrap.py, setup.py, analysis.py, instrument.py, development/tests/test_capture.py, native hook_runner.py and relevant bridge and remote transport boundaries. Reviewed the local upstream Discord adapter to establish available ingress boundaries. The deployed .212 host can differ.

The storage and external-overlay architecture is suitable. The implementation captures actual dispatch selection without a second dispatcher and keeps production source files unchanged. Activation needs the incomplete-frame credential fix described below. Several metadata and test gaps should be fixed or stated before relying on the recorder for parity decisions.

## Test evidence

Ran `python -m unittest discover -s development/tests -v` twice. First run: 7 tests passed in 3.239 seconds. Second run after the primary agent's fixes: 9 tests passed in 3.531 seconds. Exact outputs are implementation-tests.txt and implementation-tests-after-fix.txt.

Ran a separate real-process baseline versus traced probe with a hook returning `{"hookSpecificOutput":"not-an-object"}`. Baseline returned OUTCOME:null. Initial traced execution raised AttributeError in instrumentation decision extraction. The primary agent fixed decision shape checking and made after-observation optional. The second test run includes a passing regression test for this behavior.

Ran synthetic credential probes with no real credentials. encoded-credential-probe.txt shows that plaintext-only safe() cannot redact base64 transport representation. The primary agent added explicit transport protocol decode, redact, and re-encode, with a passing test in the second run.

Ran a truncated-frame probe against transport_output. partial-frame-credential-probe.txt shows that an encoded credential remains recoverable when the frame includes stdout but omits stderr. This was reported to the primary agent before activation.

## Findings

### P1: Incomplete transport frames bypass credential redaction

At review time, transport_output only sanitizes a recognized frame if all expected stream positions exist. A partial frame containing a status and stdout line bypasses that branch. The output still contains the base64 secret.

Reproduction input is a recognized `__LIFEOS_HOOK_<32hex>__` marker, status 0, and base64-encoded CANARY-CREDENTIAL-9472, without a stderr line or end marker. The helper returns a string from which the original canary can be decoded.

Fix each available frame stream position independently. Missing positions remain a visible incomplete frame. Undecodable positions must be omitted or replaced with a marker. Add an incomplete-frame credential test before .212 activation.

### P1, fixed and verified: Malformed hook output changes native behavior

The original decision() called .get on hookSpecificOutput without checking its type. This made successful native no-op responses become instrumentation exceptions. The fix and baseline/traced regression test passed in the second test run.

The optional-observer boundary around after() is valuable. Keep observation failures separate from native exceptions so the recorder does not label its own failure as a native hook failure.

### P1, full frames fixed and verified: Encoded transport credentials

Raw remote stdin contains base64 environment assignments and command text. Raw output frames contain base64 native streams. Plaintext redaction is insufficient. The added protocol-aware sanitization and known canary test cover complete frames. Incomplete frames remain the separate finding above.

Do not assume arbitrary base64 in free text is now secret-free. Protocol sanitization fixes known transport representations. General credential detection still has a stated limit.

### P2: Registered Hermes event identity can be lost

observed() returns a function unchanged when it already carries _development_observed. Bridge methods are observed before register(ctx) registers them. Registration observation therefore cannot replace a bridge method name with the actual Hermes event name.

Examples include pre_llm_call versus pre_prompt_admission, session_end versus on_session_finalize, and turn_end versus on_turn_result. Keep both a bridge_method property and the actual registered hermes_event. Recorders and reports should not present bridge method names as host event names.

### P2: Discord ingress capture misses early admission rejection

At review time patch_module only wraps _handle_message and send. The inspected upstream adapter can reject a message in _discord_message_admission before _handle_message runs. Such a message produces no ingress event in this design.

Observe the actual admission call and result where the deployed adapter exposes it. Never invoke admission again for inspection because its claim argument changes deduplication state. Preserve ignored messages as ingress outcomes, not hook failures.

### P2, implementation updated: Detached remote terminal events

Initially, the subprocess observer only recognized JSON native input. Remote input is framed text, so successful detached remote hooks had no hook.completed event and appeared incomplete forever. The primary agent updated remote_hook observation to emit detached start and terminal outcomes.

The local fallback runner test passes. A real SSH or Docker detached completion was not verified by this reviewer. Include both a successful remote result and a transport failure. Escaping exceptions also need hook.failed under the same invocation ID, rather than only remote_hook.failed.

### P2: Remote scope identity is incomplete

Registration inventory removes _remote_project and records target_kind as remote, without distinguishing SSH and Docker. Its settings origin can be unknown. Identical remote settings can have identical inventory IDs across workspaces. A raw transport artifact helps recover backend type, but the metadata is weaker for pattern queries.

Add backend kind, stable backend identity, and project root to the remote registration identity or its indexed scope. Preserve the explicit origin_observed flag when source settings cannot be identified. Do not infer an observed origin.

## Startup and loader assessment

The interpreter .pth approach fits the account's detached base sys.executable. INSTALLED guards against duplicate activation through additional site directories. The primary agent added an explicit fingerprint check for the __main__ hook_runner entry point, which normal import loader instrumentation would miss.

SourceFileLoader applies in-memory AST changes only to pinned bridge.py and remote_hooks.py. The changes observe actual jobs and backend calls. Unknown source revisions fall back to original loading with a capture gap. This is preferable to applying a stale transformation.

There is no fundamental loader blocker in the inspected implementation. Keep the activation scoped to the test account and verify the .pth file is removed during rollback. The bootstrap currently initializes capture for other interpreter invocations too, even if those processes never load Hermes. Their process.initialized events are overhead and extra data; role filtering would reduce noise.

Subprocess.run and OpenerDirector.open patches affect the process globally. Current invocation-context and native-input checks substantially limit capture. Test recursive Python child processes and unrelated subprocess work while a hook context exists. The test suite does not establish behavior for every host extension.

## Evidence and analysis quality

Positive points:

- Full command streams exceeding 1 MB are captured.
- Artifacts are redacted before hashing and use immutable atomic publication.
- JSONL shards avoid inter-process append races and carry local sequence and monotonic time.
- A real disk failure does not change the native denial.
- The HTTP read cap stays unchanged and capture labels its completeness limit.
- SQLite is derived offline from raw evidence.
- Partial JSONL tails and missing terminal events are explicit report states.
- Expected exit-code-2 interventions are distinct from execution failures.

Remaining test gaps:

1. Actual systemd-run launch, rather than only Popen fallback.
2. Live SSH and Docker detached completion and transport failure.
3. Host-enforced denial, approval resolution, and actual context application on the deployed .212 revision.
4. Multiple-process and concurrent-thread writes, with correct invocation correlation.
5. Configuration reload identity and never-exercised registrations.
6. Instrumented versus uninstrumented latency and final-answer behavior under real Hermes callback budgets.
7. Package inspection confirming development instrumentation is excluded from the public distribution.

The current trace records observed boundaries, not semantic parity. Generic hook completion cannot prove a memory write, file update, notification, or model-context effect occurred.

## Files changed by this reviewer

Only review reports and raw evidence under docs/agents/2026-09-30-capture-design-review/. No implementation files, server settings, or memory records changed. The primary agent changed implementation concurrently and received each finding directly.
