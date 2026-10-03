# Development hook capture review

Date: 2026-09-30
Agent role: Independent capture design reviewer
Question: What should development tracing capture, and how should evidence be organized for later agent analysis?
Model: GPT-6.1-Sol, high reasoning effort

## Recommendation

Use an external, development-only Python overlay. Store append-only event records in per-process JSON Lines files and full redacted payloads in immutable artifacts. Build SQLite indexes and reports from those files after capture. Keep SQLite out of the live recording path.

The evidence store must stay outside the public repository, preferably under the lifeos-hermes account's private state directory. The recorder can have its own local development checkout. Package and deployment checks must establish that neither code nor raw data enters the distributable plugin.

Capture the production call boundaries rather than implementing another hook dispatcher. Preserve all original decisions, order, timeout limits, and return values. Use fingerprints of the inspected source functions so that changed functions produce an explicit instrumentation compatibility error instead of plausible but incorrect records.

## Source observations

Exact symbol ranges are in symbol-lines.json. Selected loss points and dispatch branches are in capture-boundaries.txt.

1. lifeos_hook_bridge/__init__.py:register, lines 17-63, registers bridge callbacks. The Stop callback is a closure that can add an on_limit policy after bridge.stop returns. Recording bridge.stop alone misses this final policy.
2. bridge.py:HookBridge._run, lines 1172-1282, selects registrations, applies matcher aliases, skips unsupported types and checkpoint hooks, prepares jobs, launches asynchronous jobs, and executes synchronous jobs through ThreadPoolExecutor. Future exceptions become log messages and absent outcomes.
3. bridge.py:HookBridge._run_command, lines 1284-1299, captures synchronous command streams in memory. OSError and TimeoutExpired become None. A completed callback wrapper cannot distinguish those failures without capture before that conversion.
4. bridge.py:HookBridge._run_http, lines 1302-1315, reads at most 65,536 bytes. It rejects non-loopback destinations and converts transport errors to None.
5. bridge.py:HookBridge._run_async and _run_remote_async, lines 1317-1381, write a private request spool and launch a detached interpreter. The spool includes environment values and must be redacted before copying.
6. bridge.py:HookBridge._start_async_runner, lines 1385-1406, first uses systemd-run. This branch does not pass the supplied environment to the runner. The fallback Popen branch does pass it. PYTHONPATH alone is insufficient to instrument both branches.
7. bin/hook_runner.py:main, lines 14-37, deletes the request spool before execution, directs local stderr to DEVNULL, and reads only 65,537 characters of stdout for context processing. The command itself can produce larger stdout. A wrapper around main cannot recover discarded stderr.
8. bin/hook_runner.py:_run_remote, lines 40-73, runs SSH or Docker transports in a separate interpreter. bin/hook_runner.py:_save_context persists only selected context fields. The bridge later claims and deletes those result files in _drain_async_context.
9. remote_hooks.py:run_project_hook, lines 111-175, transports command, environment assignments, and full payload over stdin. It frames the exit status and streams inside merged backend output, then decodes them. A transport failure and a hook exit failure are distinct events.
10. bridge.py:pre_tool_call, pre_llm_call, augment_tool_result, and stop interpret native output and return host directives. They do not prove the host enforced those directives.
11. tests/test_bridge.py has actual detached-process coverage, including one-megabyte input, result handoff, parent exit, environment restoration, and workdir restoration. These scenarios are suitable for capture regression tests.
12. The upstream host source inspected exposes invoke_hook, ainvoke_hook, _dispatch_pre_tool_call_hooks, and final host directive resolution. The deployed .212 host must be inspected separately because its patch set has additional lifecycle entry points.

## Storage layout

Use a single capture root with explicit run manifests:

```text
capture-root/
  runs/<run-uuid>/manifest.json
  runs/<run-uuid>/events/<utc-date>/<process-uuid>.jsonl
  runs/<run-uuid>/inventory/<inventory-hash>.json
  artifacts/sha256/<first-two-digits>/<remaining-digits>.json.gz
  artifacts/sha256/<first-two-digits>/<remaining-digits>.bin.gz
  analysis/<run-uuid>/index.sqlite
  analysis/<run-uuid>/summary.json
  analysis/<run-uuid>/summary.md
```

Use UUID process identities, not only process IDs. A PID can be reused. Include startup time, PID, parent process identity, role, source revisions, interpreter version, instrumentation version, and source fingerprints in the manifest.

Artifacts are redacted before hashing. The hash identifies uncompressed artifact bytes. Compression changes must not change identity. Store raw bytes when decoding would lose information. Add a separate text or JSON interpretation as a linked artifact.

Write artifacts atomically with exclusive creation and rename or link semantics. Do not overwrite existing content. Write the artifact first, then append its referring event. Orphaned artifacts are harmless. References to missing artifacts are evidence corruption.

One JSONL file per process removes inter-process append races. Protect its writes with one process-local thread lock. Include a monotonically increasing local sequence and monotonic time. UTC wall time enables cross-process alignment, but ordering must not depend only on wall time. A parser must detect a partial final line and retain the preceding records.

Do not add hard-link-based deduplication or elaborate retention logic until real capture size warrants it. SHA-256 addressing and ordinary gzip are sufficient initially.

## Event record

Keep frequently queried properties at the top level. Do not require an agent to read megabyte payloads to identify failures.

```json
{
  "schema_version": 1,
  "event_id": "uuid",
  "run_id": "uuid",
  "process_id": "uuid",
  "sequence": 81,
  "time_utc": "2026-09-30T16:21:32.123456Z",
  "monotonic_ns": 39147829620,
  "pid": 1234,
  "thread_id": 5678,
  "stage": "hook.completed",
  "session_id": "session",
  "turn_id": "turn-or-null",
  "tool_call_id": "tool-call-or-null",
  "callback_id": "uuid",
  "dispatch_id": "uuid",
  "invocation_id": "uuid",
  "parent_invocation_id": null,
  "registration_id": "inventory-hash:source:group-index:hook-index",
  "native_event": "PreToolUse",
  "hermes_event": "pre_tool_call",
  "target_kind": "local",
  "hook_kind": "command",
  "asynchronous": false,
  "status": "completed",
  "decision": "deny",
  "exit_code": 2,
  "duration_ns": 8151200,
  "input_ref": "sha256:hash",
  "stdout_ref": "sha256:hash",
  "stderr_ref": "sha256:hash",
  "evidence_level": "hook-result",
  "exception_type": null,
  "capture_complete": true
}
```

Absent turn identifiers should be null, not invented. A capture-generated callback ID is not a host turn ID. Emit correlation quality when a relation is inferred rather than observed.

Use a registration identity containing source settings path, scope, group position, hook position, and inventory hash. Hashing only the command collapses intentional duplicate registrations. An additional semantic command hash helps compare a handler across updates without replacing the registration identity.

Inventory records include event, matcher, command or redacted URL, timeout, asynchronous flag, scope, settings origin, and hook source hash when available. Configuration reloads create a fresh immutable inventory and emit an inventory.changed event.

## Capture stages

Use explicit stages such as callback.entered, translation.created, registration.evaluated, hook.started, hook.completed, hook.failed, response.parsed, callback.returned, host.policy_resolved, host.tool_started, host.tool_completed, host.context_applied, async.handoff, async.result_saved, and async.result_consumed.

Capture raw callback arguments before the callback mutates them. Capture effective arguments after return where mutation is possible. Preserve a safe serializer for dictionaries, sequences, dataclasses, bytes, Paths, primitives, and known CompletedProcess values. Do not call arbitrary object repr or iterate arbitrary objects while serializing. Record unsupported types explicitly.

Every evaluated registration receives its own record. Distinguish matcher rejection, checkpoint exclusion, unsupported type, invalid command, invalid HTTP destination, untrusted workspace, and missing host capability. Hooks for an entirely different native event are inventory entries that were not exercised, not skipped invocations.

Record native stdout, parsed JSON, event-specific accepted fields, and final callback return separately. A return code of 2 can be an expected denial. A malformed response is not identical to a successful no-op.

Record attempted backend execution and raw framed output separately from decoded hook exit status and streams. This permits diagnosis of missing frames, decoding errors, backend timeouts, and hook failures.

Host enforcement needs observations outside the bridge. Record resolved host directives, actual dispatch entry, actual dispatched arguments, tool result, context assembly, and final response outcome where stable host interfaces expose them. A returned denial alone has evidence_level hook-result. A denial with an observed blocked dispatch can have evidence_level host-observed. File side effects require explicit controlled probes or selected before/after snapshots. Generic tool success is not proof that every intended side effect occurred.

## Instrumentation boundaries and risks

A development import hook can instrument bridge methods and host functions after module loading. Registration wrappers can observe the final plugin callback, including the Stop closure. Preserve functools metadata and signatures because the host filters callback arguments and manages timeout behavior.

Propagate recording context explicitly across ThreadPoolExecutor.submit and detached spools. ContextVar state does not automatically cross those threads or interpreters. Instrument only bridge-owned submission paths, not every executor in the account.

Use a role-filtered bootstrap accessible to the account interpreter so systemd-launched detached runners load it. A temporary .pth startup hook is one option if it is limited to the development account and checks the exact executable, script path, configuration file, and capture enable flag. Test its behavior with both systemd-run and fallback Popen. Remove it on rollback.

Module-level subprocess.run is the shared subprocess module object. Replacing bridge.subprocess.run therefore patches the whole process. Avoid treating it as a bridge-local namespace. A proxy around the module or a strict call-context filter can confine the capture, with behavior-equivalence tests. Never capture unrelated shell commands merely because a development account has instrumentation enabled.

Local asynchronous stderr needs redirection into a recorder-owned temporary file instead of DEVNULL. Preserve the caller-visible CompletedProcess shape and result handling. Read stdout from the existing temporary output file after subprocess completion, restore the file position, and store all bytes. Capture partial streams on timeout before the production runner converts the error to exit 1. This changes a subprocess output sink, so verify no hook depends on DEVNULL behavior.

HTTP has a harder limit. Consuming the body beyond the production 65,536-byte read can extend the call or alter failure behavior. Initially capture exact observed bytes and mark the runtime cap. Do not claim complete HTTP bodies. Any later full-body tee needs tests against slow and unbounded responses and must preserve the production read contract.

Exact registration evaluation inside _run is not exposed as a public callback. Re-running _hook_groups is unsafe because it can touch remote files and mutate settings state. Re-creating dispatcher logic risks a misleading parallel implementation. For a zero-source-edit overlay, use a narrowly scoped, source-fingerprinted instrumentation point that observes the actual loop locals and branches. Python tracing can do this, but measure its overhead. If that becomes fragile, a temporary development-only instrumented checkout is more honest than inferred skip records presented as exact evidence. Do not ship that checkout.

A parent crash can leave no completion. Represent pending and incomplete states explicitly and reconcile against known detached runner state later. A reaper exit is not the native hook completion unless it carries the actual hook status.

## Credentials and private data

Preserve substantive prompts, tool arguments, paths, native results, and conversation context. Redact authentication tokens, private keys, passwords, authorization headers, and known secret environment values before any artifact reaches disk. Do not copy complete environment dictionaries without redaction. SSH private-key paths are useful configuration metadata; private-key contents are not.

Default root and artifact permissions should be 0700 and 0600. Keep data outside Git. Never hash an unredacted credential and write that digest as an artifact identity. Do not call the durable memory tools with captured conversations or private raw evidence.

A generic filter cannot prove absence of every secret embedded in arbitrary prose. State this limit and use clean test credentials where practical. Test that known secrets never appear in filenames, events, artifact content, SQLite, reports, error messages, or manifests.

## Agent analysis

The JSONL and artifact manifests are the source of truth. A deterministic offline importer builds SQLite tables for events, registrations, artifacts, and correlation edges. Index native_event, registration_id, status, decision, session_id, tool_call_id, target_kind, and time_utc. Add optional full-text indexing of redacted text artifacts only when needed.

Provide report commands that return bounded JSON results with artifact references. Useful queries include failure counts by registration and version, p50/p95/max duration, skipped reasons, missing completions, repeated semantic decisions, low-confidence correlations, and registrations never exercised. Generate a per-session timeline for reproduction.

Keep outcome categories separate: expected intervention, successful no-op, execution failure, transport failure, parsing failure, incomplete, unobserved host outcome, and not exercised. Do not report parity or correctness percentages from exit codes alone.

## Tests required before .212 everyday capture

1. Local command prints more than 1 MB to stdout and stderr. Recorder preserves complete streams, production return stays unchanged.
2. Exit 2 and structured denial retain expected intervention status. Actual tool dispatch remains blocked.
3. Matcher alias and checkpoint exclusion produce exact registration records without calling remote discovery twice.
4. Two identical command registrations and concurrently executing hooks have distinct identities and correct correlations.
5. Exceptions and timeouts preserve partial output and traceback evidence without changing production error handling.
6. Detached local and remote hooks survive parent exit, using both launcher branches, and preserve context handoff behavior.
7. SSH and Docker frames preserve separate transport and native outcomes. Missing or invalid frames remain errors, not successful empty output.
8. HTTP capture marks the production body cap. A slow extra body does not delay the production callback.
9. Known credentials do not appear anywhere in capture output.
10. Recorder disk failures and partial JSONL tails produce explicit evidence gaps and do not change policy decisions.
11. Instrumented and uninstrumented scenario outcomes match. Record overhead for sequential and concurrent hook workloads.
12. Public package inspection establishes absence of instrumentation imports, development dependencies, raw logs, and deployment bootstrap.

## Discord observations

The local upstream adapter exposes _discord_message_admission at line 1482, _dispatch_discord_message at line 1563, and send at line 3049. Exact symbol ranges are in discord-symbol-lines.json. Admission returns a boolean before plugin hooks run. Capture the incoming message identifier, author identifier, channel/thread relation, bot-account mentions, role mentions, actual admission result, and observed adapter delivery result. A failed admission is an ingress observation, not a skipped LifeOS hook. Do not call admission twice to inspect it because its claim flag mutates deduplication state. The deployed .212 revision can differ and must determine the actual capture points.

## Unresolved limits

The recorder cannot infer correctness from native completion. Paired Claude probes and state checks remain necessary. Hook-internal subprocesses, file writes, and network effects are not automatically observed by Python-boundary capture of a Bun process. Exact host enforcement boundaries must be verified on the deployed .212 revision. Full raw HTTP output above the production cap cannot be promised without a separate experiment. A generic secret filter cannot guarantee every secret in free text is detected.

No implementation code, server settings, or memory records were changed for this review. The review used local source inspection only. It did not run runtime tests.
